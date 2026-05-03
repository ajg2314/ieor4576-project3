from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import ClarityFeedback, InputDocument, UserContext, ContentAnalysis, VenueContext

SYSTEM_PROMPT = """You are a clarity coach specializing in technical communication.
Your job is to identify where the document loses the reader due to jargon, undefined terms, or dense writing.

Rules:
- Quote specific passages that are problematic
- Return only valid JSON matching the schema below
- Every item must reference a specific passage, term, or section — no generic advice

Output schema:
{
  "jargon_issues": ["quoted jargon terms or passages that are unexplained"],
  "undefined_terms": ["terms used before being defined, with the passage where they first appear"],
  "dense_sections": ["sections or passages that are overly compressed or hard to parse"],
  "clarification_suggestions": ["specific rewrite suggestions for the worst offenders"]
}"""


async def run_clarity_coach(
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    venue_context: VenueContext | None = None,
) -> ClarityFeedback:
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
Technical density assessed: {content_analysis.technical_density}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

Identify clarity issues and return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return ClarityFeedback(**parse_llm_json(raw))
