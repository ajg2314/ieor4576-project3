from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import (
    RevisionPlan, InputDocument, UserContext, ContentAnalysis,
    NarrativeFeedback, ClarityFeedback, PersonaFeedback,
    QAPrediction, VenueContext, DeliveryFeedback,
    DeliveryMetrics, TranscriptSegment, ApplicationFitReport,
)

SYSTEM_PROMPT = """You are a revision planner for technical communication.
Your job is to convert all critique into a concrete, prioritized action plan.
You have received feedback from a narrative coach, clarity coach, audience personas, and a Q&A predictor.

Rules:
- top_priorities must be the 3 most impactful changes — be specific about what to do
- cuts, moves, and emphasis_changes must reference specific content from the document
- revised_outline must be a complete reordered structure (numbered list of sections)
- revised_opening must be a rewritten opening paragraph
- Return only valid JSON matching the schema below

Output schema:
{
  "top_priorities": ["top 3 highest-impact changes, each referencing specific content"],
  "cuts": ["specific passages or sections to remove and why"],
  "moves": ["specific content that should appear earlier or later, with target position"],
  "emphasis_changes": ["content that needs more or less emphasis"],
  "revised_outline": ["1. Section title", "2. Section title", ...],
  "revised_opening": "a rewritten opening paragraph that states motivation and contribution clearly"
}"""


async def run_revision_planner(
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    narrative: NarrativeFeedback,
    clarity: ClarityFeedback,
    personas: list[PersonaFeedback],
    qa_prediction: QAPrediction | None = None,
    venue_context: VenueContext | None = None,
    delivery_feedback: DeliveryFeedback | None = None,
    delivery_metrics: DeliveryMetrics | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    application_fit: ApplicationFitReport | None = None,
) -> RevisionPlan:
    persona_summary = "\n".join(
        f"- {p.persona_name}: {p.overall_reaction[:200]}..."
        for p in personas
    )
    common_confusions = [point for p in personas for point in p.confusion_points]
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    qa_block = ""
    if qa_prediction and qa_prediction.questions:
        weak_qs = [
            f"  - {q.question} (not handled: {q.suggested_response_stub})"
            for q in qa_prediction.questions
            if q.draft_handles in ("partial", "no")
        ]
        if weak_qs:
            qa_block = "WEAK Q&A PREPAREDNESS (questions the draft doesn't answer well):\n" + "\n".join(weak_qs)

    delivery_block = ""
    if delivery_feedback:
        delivery_block = f"""DELIVERY FEEDBACK:
Pacing issues: {delivery_feedback.pacing_issues[:5]}
Filler hotspots: {delivery_feedback.filler_hotspots[:5]}
Slide mismatch flags: {delivery_feedback.slide_mismatch_flags[:5]}
Opening: {delivery_feedback.weak_opening_notes}
Closing: {delivery_feedback.weak_closing_notes}
Delivery fixes: {delivery_feedback.ranked_delivery_fixes[:5]}"""

    application_block = ""
    if application_fit:
        application_block = f"""APPLICATION FIT FEEDBACK:
Program fit verdict: {application_fit.program_fit_verdict}
Faculty matches: {[m.faculty_name + ': ' + m.why_match[:160] for m in application_fit.verified_faculty_matches[:5]]}
Fit gaps: {application_fit.fit_gaps[:5]}
Unsupported claims: {application_fit.unsupported_claims[:5]}
Authenticity risks: {application_fit.authenticity_risks[:5]}
Program-specific rewrite points: {application_fit.program_specific_rewrite_points[:5]}"""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
CONTENT ANALYSIS:
- Main claim: {content_analysis.main_claim}
- Motivation quality: {content_analysis.motivation_quality}
- Technical density: {content_analysis.technical_density}

NARRATIVE ISSUES:
Weaknesses: {narrative.weaknesses}
Ordering issues: {narrative.ordering_issues}

CLARITY ISSUES:
Jargon: {clarity.jargon_issues[:3]}
Dense sections: {clarity.dense_sections[:3]}

AUDIENCE REACTIONS:
{persona_summary}

COMMON CONFUSION POINTS ACROSS PERSONAS:
{common_confusions[:5]}

{qa_block}

{delivery_block}

{application_block}

--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

Produce a concrete revision plan and return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.5-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return RevisionPlan(**parse_llm_json(raw))
