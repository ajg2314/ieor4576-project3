from backend.models.schemas import DeliveryFeedback, DeliveryMetrics, TranscriptSegment, UserContext, VenueContext
from backend.utils.audio import delivery_metrics_block
from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry

SYSTEM_PROMPT = """You are a delivery coach for academic talks.
You critique the speaker's actual rehearsal delivery using timestamped transcript segments and computed delivery metrics.

Rules:
- Every pacing, filler, and mismatch issue must include a timestamp
- Tie advice to the stated venue when venue context is available
- Focus on delivery and content-as-delivered, not prose polishing
- Return only valid JSON matching the schema below

Output schema:
{
  "pacing_issues": ["timestamped pacing issue and why it matters"],
  "filler_hotspots": ["timestamped filler-word hotspot"],
  "slide_mismatch_flags": ["timestamped slide-speech mismatch"],
  "weak_opening_notes": "specific note on first 30 seconds",
  "weak_closing_notes": "specific note on final 30 seconds",
  "ranked_delivery_fixes": ["highest-impact delivery fix first"]
}"""


async def run_delivery_coach(
    segments: list[TranscriptSegment],
    metrics: DeliveryMetrics,
    context: UserContext,
    venue_context: VenueContext | None = None,
) -> DeliveryFeedback:
    venue_block = venue_context.to_prompt_block() if venue_context else ""
    segment_block = "\n".join(
        f"- {segment.start_seconds:.1f}-{segment.end_seconds:.1f}s"
        f"{f' ({segment.aligned_slide})' if segment.aligned_slide else ''}: "
        f"{segment.wpm:.0f} WPM, {segment.filler_word_count} fillers — {segment.text[:350]}"
        for segment in segments[:60]
    )

    user_message = f"""Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
DELIVERY METRICS:
{delivery_metrics_block(metrics, segments)}

TRANSCRIPT SEGMENTS:
{segment_block}

Return delivery feedback JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return DeliveryFeedback(**parse_llm_json(raw))
