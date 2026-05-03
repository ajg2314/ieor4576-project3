from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import ContentAnalysis, InputDocument, UserContext, VenueContext

SYSTEM_PROMPT = """You are a content analyst specializing in technical communication.
Your job is to extract the structure and main argument from a document.

Rules:
- Always quote specific passages when identifying issues (use exact text from the document)
- Return only valid JSON matching the schema below
- Never give generic advice — every observation must reference specific content
- If you cannot find a clear main claim, say so explicitly
- technical_density must be one of: low, medium, high
- motivation_quality must be one of: strong, weak, missing

Output schema:
{
  "main_claim": "one sentence stating the main claim or contribution",
  "contributions": ["list of specific contributions identified"],
  "structure_map": ["ordered list of sections/parts as they appear"],
  "technical_density": "low|medium|high",
  "motivation_quality": "strong|weak|missing"
}"""


async def run_content_analyst(
    document: InputDocument,
    context: UserContext,
    venue_context: VenueContext | None = None,
) -> ContentAnalysis:
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
Domain: {context.domain or "not specified"}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

Analyze this document and return JSON matching the schema."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return ContentAnalysis(**parse_llm_json(raw))
