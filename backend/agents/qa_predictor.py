from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import (
    QAPrediction, QAPredictionItem, InputDocument, UserContext,
    ContentAnalysis, VenueContext,
)

SYSTEM_PROMPT = """You are a Q&A predictor for academic talks and grant proposals.
Your job is to predict the 5 most likely questions an audience will ask at this specific venue, then evaluate how well the document pre-emptively answers each.

Rules:
- Questions must be specific to this venue's norms and audience — not generic
- likelihood must be one of: high, medium, low
- draft_handles must be one of: yes, partial, no
- suggested_response_stub: provide a 1-2 sentence response stub ONLY if draft_handles is "partial" or "no"; otherwise use an empty string
- Return only valid JSON matching the schema below

Output schema:
{
  "questions": [
    {
      "question": "specific question this venue's audience would ask",
      "likelihood": "high|medium|low",
      "draft_handles": "yes|partial|no",
      "suggested_response_stub": "1-2 sentence response if draft is weak, else empty string"
    }
  ]
}"""


async def run_qa_predictor(
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    venue_context: VenueContext | None = None,
) -> QAPrediction:
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
Content summary:
- Main claim: {content_analysis.main_claim}
- Contributions: {", ".join(content_analysis.contributions)}
- Motivation quality: {content_analysis.motivation_quality}

--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

Predict the 5 most likely Q&A questions for this venue and evaluate how well the draft handles each. Return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = parse_llm_json(raw)
    items = [QAPredictionItem(**q) for q in data.get("questions", [])]
    return QAPrediction(questions=items)
