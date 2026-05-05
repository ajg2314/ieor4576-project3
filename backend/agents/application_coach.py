from datetime import datetime, timezone

from backend.models.schemas import (
    ApplicationFitReport, ApplicationTarget, FacultyDossier, FacultyFitMatch,
    FacultyRecord, InputDocument, UserContext, VenueContext,
)
from backend.utils.json_parse import parse_llm_json
from backend.utils.program_research import ResearchSource, sources_prompt_block
from backend.utils.throttle import acompletion_with_retry


def _format_dossiers_block(dossiers: list[FacultyDossier]) -> str:
    if not dossiers:
        return ""
    cards: list[str] = []
    for i, d in enumerate(dossiers, 1):
        lines = [f"[Faculty {i}] {d.name}"]
        if d.profile_url:
            lines.append(f"  Profile: {d.profile_url}")
        if d.evidence_snippets:
            lines.append(f"  Areas/blurb: {d.evidence_snippets[0][:300]}")
        if d.recent_publications:
            lines.append("  Recent papers:")
            for pub in d.recent_publications[:3]:
                year = f" ({pub.year})" if pub.year else ""
                lines.append(f"    - {pub.title}{year} {pub.url}".rstrip())
        if d.active_grants:
            lines.append("  Active/recent grants:")
            for grant in d.active_grants[:3]:
                span = f" {grant.start_year}-{grant.end_year}" if grant.start_year else ""
                lines.append(f"    - [{grant.agency} {grant.award_id}]{span} {grant.title}".rstrip())
        cards.append("\n".join(lines))
    return "\n\n".join(cards)

SYSTEM_PROMPT = """You are an academic application fit coach and source-grounded program researcher.
You evaluate statements of purpose, research statements, fellowship essays, and faculty outreach emails.

Hard rules:
- Do not promise or estimate admissions probability.
- Do not invent professors, papers, labs, rankings, courses, or program facts.
- Faculty recommendations must come from supplied sources only.
- If supplied sources are weak or empty, say the fit cannot be verified and use low confidence.
- Flag generic fit claims, prestige-chasing, unsupported claims, and template-like language.
- Return only valid JSON matching the schema below.

Output schema:
{
  "program_fit_verdict": "strong_fit|plausible_fit|weak_fit",
  "faculty_records": [
    {
      "name": "professor name",
      "title": "title if available",
      "profile_url": "official source URL",
      "lab_url": "lab URL if available",
      "research_areas": ["areas grounded in the source"],
      "evidence_snippets": ["short source-backed evidence"],
      "retrieved_at": "ISO timestamp",
      "verification_status": "verified|partial|unverified"
    }
  ],
  "verified_faculty_matches": [
    {
      "faculty_name": "name",
      "fit_score": 0-100,
      "confidence": "high|medium|low",
      "why_match": "specific link between applicant and faculty/program",
      "source_urls": ["URLs supporting this match"],
      "relevant_papers_or_projects": ["paper/project/lab signals from source, if available"]
    }
  ],
  "fit_gaps": ["missing or weak fit evidence"],
  "unsupported_claims": ["claims in the application not supported by draft or sources"],
  "authenticity_risks": ["generic, inflated, template-like, or prestige-chasing wording"],
  "program_specific_rewrite_points": ["concrete rewrite actions tied to source-grounded program fit"]
}"""


def _fallback_report(target: ApplicationTarget) -> ApplicationFitReport:
    label = target.program_url or "an official target program URL"
    return ApplicationFitReport(
        program_fit_verdict="weak_fit",
        fit_gaps=[
            f"Program fit cannot be verified yet because StoryCoach could not retrieve source pages for {label}.",
            "Add an official department, program, faculty, or lab URL so faculty recommendations can be source-grounded.",
        ],
        unsupported_claims=[
            "Any faculty or program-specific claims should be treated as unverified until official sources are retrieved."
        ],
        authenticity_risks=[
            "Without verified program evidence, the application risks sounding generic or interchangeable."
        ],
        program_specific_rewrite_points=[
            "Add one or two verified faculty/lab connections after supplying an official source URL.",
            "Tie each named faculty member to a specific research question, method, or project from an official page.",
        ],
    )


def _clean_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _clean_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (_clean_str(item).strip() for item in value) if item]


def _clean_faculty_record(item: object, retrieved_at: str) -> FacultyRecord:
    if not isinstance(item, dict):
        return FacultyRecord(retrieved_at=retrieved_at)
    return FacultyRecord(
        name=_clean_str(item.get("name")),
        title=_clean_str(item.get("title")),
        profile_url=_clean_str(item.get("profile_url")),
        lab_url=_clean_str(item.get("lab_url")),
        research_areas=_clean_str_list(item.get("research_areas")),
        evidence_snippets=_clean_str_list(item.get("evidence_snippets")),
        retrieved_at=_clean_str(item.get("retrieved_at")) or retrieved_at,
        verification_status=_clean_str(item.get("verification_status")) or "unverified",
    )


def _clean_faculty_match(item: object) -> FacultyFitMatch:
    if not isinstance(item, dict):
        return FacultyFitMatch()
    return FacultyFitMatch(
        faculty_name=_clean_str(item.get("faculty_name")),
        fit_score=float(item.get("fit_score") or 0.0),
        confidence=_clean_str(item.get("confidence")) or "low",
        why_match=_clean_str(item.get("why_match")),
        source_urls=_clean_str_list(item.get("source_urls")),
        relevant_papers_or_projects=_clean_str_list(item.get("relevant_papers_or_projects")),
    )


async def run_application_coach(
    document: InputDocument,
    context: UserContext,
    target: ApplicationTarget,
    sources: list[ResearchSource],
    venue_context: VenueContext | None = None,
    dossiers: list[FacultyDossier] | None = None,
) -> ApplicationFitReport:
    if not sources:
        return _fallback_report(target)

    venue_block = venue_context.to_prompt_block() if venue_context else ""
    retrieved_at = datetime.now(timezone.utc).isoformat()
    interests = ", ".join(target.research_interests) if target.research_interests else "not specified"
    dossier_block = _format_dossiers_block(dossiers) if dossiers else ""

    user_message = f"""Document type: {document.doc_type}
Application target:
- School: {target.school_name or "unknown"}
- Program: {target.program_name or "unknown"}
- Program URL: {target.program_url or "not supplied"}
- Applicant research interests: {interests}
Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
Retrieved at: {retrieved_at}

SOURCE-GROUNDED PROGRAM EVIDENCE:
{sources_prompt_block(sources)}
{f"{chr(10)}FACULTY DOSSIERS (recent papers + active grants):{chr(10)}{dossier_block}{chr(10)}" if dossier_block else ""}
--- APPLICATION DRAFT ---
{document.raw_text}
--- END APPLICATION DRAFT ---

Evaluate program fit, extract verified faculty records, and return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.5-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    data = parse_llm_json(response.choices[0].message.content)
    records = [_clean_faculty_record(item, retrieved_at) for item in data.get("faculty_records", [])]
    matches = [_clean_faculty_match(item) for item in data.get("verified_faculty_matches", [])]
    return ApplicationFitReport(
        program_fit_verdict=data.get("program_fit_verdict", "weak_fit"),
        faculty_records=records,
        verified_faculty_matches=matches,
        fit_gaps=data.get("fit_gaps", []),
        unsupported_claims=data.get("unsupported_claims", []),
        authenticity_risks=data.get("authenticity_risks", []),
        program_specific_rewrite_points=data.get("program_specific_rewrite_points", []),
    )
