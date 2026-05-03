from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import NarrativeFeedback, InputDocument, UserContext, ContentAnalysis, VenueContext

SYSTEM_PROMPT = """You are a narrative coach specializing in technical communication.
Treat the document as a story with setup (motivation), conflict (problem/challenge), and resolution (contribution/result).
Identify which elements are missing or weak.

Rules:
- Quote specific passages when identifying issues
- Return only valid JSON matching the schema below
- Every observation must reference specific content
- Be direct — name the structural problem precisely

Output schema:
{
  "arc_summary": "one paragraph describing the narrative arc as written",
  "strengths": ["specific narrative strengths with quoted evidence"],
  "weaknesses": ["specific narrative weaknesses with quoted evidence"],
  "ordering_issues": ["specific ordering problems — what appears too early or too late"],
  "revision_suggestions": ["concrete suggestions for improving the narrative flow"]
}"""


async def run_narrative_coach(
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    venue_context: VenueContext | None = None,
) -> NarrativeFeedback:
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
Domain: {context.domain or "not specified"}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
Content analyst summary:
- Main claim: {content_analysis.main_claim}
- Structure map: {", ".join(content_analysis.structure_map)}
- Motivation quality: {content_analysis.motivation_quality}
- Contributions: {", ".join(content_analysis.contributions)}

--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

Evaluate the narrative structure and return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.5-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return NarrativeFeedback(**parse_llm_json(raw))
