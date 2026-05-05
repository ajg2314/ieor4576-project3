from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import (
    FinalReport, PriorityIssue, InputDocument, UserContext, ContentAnalysis,
    NarrativeFeedback, ClarityFeedback, PersonaFeedback, RevisionPlan,
    QAPrediction, VenueContext, DeliveryFeedback,
    DeliveryMetrics, TranscriptSegment, ApplicationFitReport,
)

SYSTEM_PROMPT = """You are a synthesis editor for technical communication feedback.
You receive feedback from multiple specialized reviewers and produce a single, clean, prioritized report.

Ranking logic (count how many distinct reviewers flagged each issue):
- Flagged by 4+ reviewers → "critical" priority
- Flagged by 3 reviewers → "high" priority
- Flagged by 2 reviewers → "medium" priority
- Flagged by 1 reviewer → "low" priority

Rules:
- Deduplicate overlapping issues across reviewers
- executive_summary must be 2–3 sentences: what works, what the top problem is, and the single most important fix
- top_issues must list the 5 most impactful issues, each with priority, agents_flagging, quoted_passage, venue_grounding, and suggested_fix
- venue_grounding must explain why this specific issue matters for the stated venue's norms — be concrete
- venue_fit_verdict: judge whether this document would clear the bar at this venue using the calibrated rubric below
- Do not make the verdict harsher than the audience evidence supports. If all or most audience personas are positive/engaged and the problems are fixable revision issues, the verdict should usually be "at_bar", not "below_bar".
- Use "below_bar" only when there is a fatal or near-fatal venue risk: unclear core contribution, missing motivation, unverified/unsupported central claims, severe audience confusion across multiple personas, or a mismatch with the assignment/venue that would likely cause rejection.
- Use "at_bar" when the document is credible for the venue and audiences respond positively, but it still needs concrete improvements before submission or delivery.
- Use "above_bar" when the document is clearly strong for the venue, has a compelling contribution/story, and remaining issues are minor polish rather than structural risks.
- venue_fit_confidence should be "low" when positive audience reactions and serious issue lists point in different directions.
- Return only valid JSON matching the schema below

Output schema:
{
  "venue_fit_verdict": "above_bar|at_bar|below_bar",
  "venue_fit_confidence": "high|medium|low",
  "executive_summary": "2-3 sentence summary",
  "top_issues": [
    {
      "issue": "clear description of the issue",
      "priority": "critical|high|medium|low",
      "agents_flagging": ["list of reviewer names that flagged this"],
      "quoted_passage": "exact quote from the document illustrating this issue",
      "venue_grounding": "why this issue specifically hurts at this venue",
      "suggested_fix": "concrete actionable fix"
    }
  ]
}"""


async def run_synthesizer(
    session_id: str,
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    personas: list[PersonaFeedback],
    narrative: NarrativeFeedback,
    clarity: ClarityFeedback,
    revision_plan: RevisionPlan,
    qa_prediction: QAPrediction | None = None,
    venue_context: VenueContext | None = None,
    delivery_feedback: DeliveryFeedback | None = None,
    delivery_metrics: DeliveryMetrics | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    application_fit: ApplicationFitReport | None = None,
) -> FinalReport:
    all_issues = (
        [f"[Narrative Coach] {w}" for w in narrative.weaknesses]
        + [f"[Narrative Coach] {o}" for o in narrative.ordering_issues]
        + [f"[Clarity Coach] {j}" for j in clarity.jargon_issues]
        + [f"[Clarity Coach] {d}" for d in clarity.dense_sections]
        + [f"[{p.persona_name}] {c}" for p in personas for c in p.confusion_points]
    )
    if delivery_feedback:
        all_issues.extend(
            [f"[Delivery Coach] {issue}" for issue in delivery_feedback.pacing_issues]
            + [f"[Delivery Coach] {issue}" for issue in delivery_feedback.filler_hotspots]
            + [f"[Delivery Coach] {issue}" for issue in delivery_feedback.slide_mismatch_flags]
        )
    if application_fit:
        all_issues.extend(
            [f"[SOP Fit Coach] {issue}" for issue in application_fit.fit_gaps]
            + [f"[Authenticity Coach] {issue}" for issue in application_fit.authenticity_risks]
            + [f"[Source Verifier] {issue}" for issue in application_fit.unsupported_claims]
        )

    qa_block = ""
    if qa_prediction and qa_prediction.questions:
        unhandled = [
            f"  - {q.question} (draft: {q.draft_handles})"
            for q in qa_prediction.questions
            if q.draft_handles in ("partial", "no")
        ]
        if unhandled:
            qa_block = "\nUNANSWERED Q&A RISKS:\n" + "\n".join(unhandled)

    application_block = ""
    if application_fit:
        application_block = f"""
APPLICATION FIT REPORT:
Program fit verdict: {application_fit.program_fit_verdict}
Verified faculty matches: {[m.faculty_name + ': ' + m.why_match[:160] for m in application_fit.verified_faculty_matches[:5]]}
Fit gaps: {application_fit.fit_gaps[:5]}
Unsupported claims: {application_fit.unsupported_claims[:5]}
Authenticity risks: {application_fit.authenticity_risks[:5]}
Program-specific rewrite points: {application_fit.program_specific_rewrite_points[:5]}
"""

    venue_block = venue_context.to_prompt_block() if venue_context else ""
    audience_balance = "\n".join(
        f"- {p.persona_name}: overall={p.overall_reaction[:360]}; "
        f"interest={p.interest_points[:3]}; confusion={p.confusion_points[:3]}"
        for p in personas
    )

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
CONTENT ANALYSIS:
Main claim: {content_analysis.main_claim}
Motivation quality: {content_analysis.motivation_quality}

DOCUMENT STRENGTHS:
Narrative strengths: {narrative.strengths}
Audience interest points: {[point for p in personas for point in p.interest_points][:8]}

ALL FLAGGED ISSUES (deduplicate and rank these):
{chr(10).join(all_issues[:35])}

AUDIENCE REACTION BALANCE (use this to calibrate the overall verdict):
{audience_balance}

TOP REVISION PRIORITIES (from Revision Planner):
{revision_plan.top_priorities}
{qa_block}
{application_block}

--- DOCUMENT (first 1200 chars for passage quoting) ---
{document.raw_text[:1200]}
--- END ---

Synthesize the top 5 issues and return JSON. Make the venue_fit_verdict reflect the whole evidence record: audience engagement, strengths, severity of issues, and venue expectations."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.5-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = parse_llm_json(raw)

    top_issues = [PriorityIssue(**issue) for issue in data["top_issues"]]

    return FinalReport(
        session_id=session_id,
        venue=context.venue,
        venue_fit_verdict=data.get("venue_fit_verdict", ""),
        venue_fit_confidence=data.get("venue_fit_confidence", ""),
        executive_summary=data["executive_summary"],
        top_issues=top_issues,
        audience_reactions=personas,
        narrative_section=narrative,
        clarity_section=clarity,
        qa_predictions=qa_prediction,
        delivery_section=delivery_feedback,
        delivery_metrics=delivery_metrics,
        transcript_segments=transcript_segments or [],
        application_fit=application_fit,
        revision_plan=revision_plan,
    )
