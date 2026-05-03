import json
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from enum import Enum


def _coerce_str_list(v: list) -> list[str]:
    """Coerce list items to strings — handles cases where LLM returns nested objects."""
    result = []
    for item in v:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            str_vals = [str(val) for val in item.values() if val]
            result.append(" — ".join(str_vals) if str_vals else json.dumps(item))
        else:
            result.append(str(item))
    return result


class DocType(str, Enum):
    talk_outline = "talk_outline"
    slide_text = "slide_text"
    abstract = "abstract"
    introduction = "introduction"
    paper_section = "paper_section"
    grant_aims = "grant_aims"
    statement_of_purpose = "statement_of_purpose"
    personal_statement = "personal_statement"
    research_statement = "research_statement"
    diversity_statement = "diversity_statement"
    faculty_email = "faculty_email"
    fellowship_essay = "fellowship_essay"


class AudienceType(str, Enum):
    undergraduates = "undergraduates"
    grad_students_in_field = "grad_students_in_field"
    grad_students_outside_field = "grad_students_outside_field"
    experts = "experts"
    interdisciplinary = "interdisciplinary"
    hiring_committee = "hiring_committee"


class GoalType(str, Enum):
    explain_clearly = "explain_clearly"
    persuade = "persuade"
    present_research = "present_research"
    teach = "teach"


class VenueType(str, Enum):
    neurips = "neurips"
    icml = "icml"
    cvpr = "cvpr"
    nsf = "nsf"
    nih_r01 = "nih_r01"
    job_talk = "job_talk"
    generic_academic = "generic_academic"
    graduate_sop = "graduate_sop"
    phd_application = "phd_application"
    masters_application = "masters_application"
    nsf_grfp = "nsf_grfp"
    faculty_outreach = "faculty_outreach"
    custom = "custom"


class VenueContext(BaseModel):
    venue: str
    name: str = ""
    expected_length_minutes: int = 0
    scoring_criteria: list[str] = []
    common_rejection_reasons: list[str] = []
    expected_pacing_notes: str = ""
    reference_accepted_examples: list[str] = []
    reference_rejected_examples: list[str] = []

    def to_prompt_block(self) -> str:
        lines = [f"VENUE: {self.name or self.venue}"]
        if self.expected_length_minutes:
            lines.append(f"Expected length: {self.expected_length_minutes} minutes")
        if self.scoring_criteria:
            lines.append("Scoring criteria:\n" + "\n".join(f"  - {c}" for c in self.scoring_criteria))
        if self.common_rejection_reasons:
            lines.append("Common rejection reasons:\n" + "\n".join(f"  - {r}" for r in self.common_rejection_reasons))
        if self.expected_pacing_notes:
            lines.append(f"Expected pacing: {self.expected_pacing_notes}")
        return "\n".join(lines)


class InputDocument(BaseModel):
    id: str = ""
    title: str = ""
    raw_text: str
    sections: list[str] = []
    doc_type: DocType
    source_type: str = "paste"


class UserContext(BaseModel):
    venue: VenueType = VenueType.generic_academic
    audience_type: AudienceType
    goal_type: GoalType
    domain: str = ""
    user_notes: str = ""
    application_target: Optional["ApplicationTarget"] = None


class ContentAnalysis(BaseModel):
    main_claim: str
    contributions: list[str]
    structure_map: list[str]
    technical_density: str  # low / medium / high
    motivation_quality: str  # strong / weak / missing


class PersonaFeedback(BaseModel):
    persona_name: str = ""
    persona_description: str = ""
    overall_reaction: str = ""
    confusion_points: list[str] = []
    interest_points: list[str] = []
    questions_remaining: list[str] = []

    @field_validator("confusion_points", "interest_points", "questions_remaining", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class NarrativeFeedback(BaseModel):
    arc_summary: str = ""
    strengths: list[str] = []
    weaknesses: list[str] = []
    ordering_issues: list[str] = []
    revision_suggestions: list[str] = []

    @field_validator("strengths", "weaknesses", "ordering_issues", "revision_suggestions", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class ClarityFeedback(BaseModel):
    jargon_issues: list[str] = []
    undefined_terms: list[str] = []
    dense_sections: list[str] = []
    clarification_suggestions: list[str] = []

    @field_validator("jargon_issues", "undefined_terms", "dense_sections", "clarification_suggestions", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class QAPredictionItem(BaseModel):
    question: str
    likelihood: str = "medium"  # high | medium | low
    draft_handles: str = "partial"  # yes | partial | no
    suggested_response_stub: str = ""


class QAPrediction(BaseModel):
    questions: list[QAPredictionItem] = []


class TranscriptSegment(BaseModel):
    start_seconds: float
    end_seconds: float
    text: str
    wpm: float = 0.0
    filler_word_count: int = 0
    aligned_slide: Optional[str] = None


class DeliveryMetrics(BaseModel):
    total_duration_seconds: float = 0.0
    average_wpm: float = 0.0
    wpm_variance: float = 0.0
    filler_word_total: int = 0
    filler_word_density_per_minute: float = 0.0
    pacing_dropouts: list[str] = []
    slide_speech_mismatches: list[str] = []


class DeliveryFeedback(BaseModel):
    pacing_issues: list[str] = []
    filler_hotspots: list[str] = []
    slide_mismatch_flags: list[str] = []
    weak_opening_notes: str = ""
    weak_closing_notes: str = ""
    ranked_delivery_fixes: list[str] = []

    @field_validator(
        "pacing_issues", "filler_hotspots", "slide_mismatch_flags", "ranked_delivery_fixes",
        mode="before",
    )
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class ApplicationTarget(BaseModel):
    school_name: str = ""
    program_name: str = ""
    program_url: str = ""
    research_interests: list[str] = []

    @field_validator("research_interests", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class FacultyRecord(BaseModel):
    name: str = ""
    title: str = ""
    profile_url: str = ""
    lab_url: str = ""
    research_areas: list[str] = []
    evidence_snippets: list[str] = []
    retrieved_at: str = ""
    verification_status: str = "unverified"  # verified | partial | unverified

    @field_validator("research_areas", "evidence_snippets", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class FacultyFitMatch(BaseModel):
    faculty_name: str = ""
    fit_score: float = 0.0
    confidence: str = "low"  # high | medium | low
    why_match: str = ""
    source_urls: list[str] = []
    relevant_papers_or_projects: list[str] = []

    @field_validator("source_urls", "relevant_papers_or_projects", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class ApplicationFitReport(BaseModel):
    program_fit_verdict: str = ""  # strong_fit | plausible_fit | weak_fit
    verified_faculty_matches: list[FacultyFitMatch] = []
    faculty_records: list[FacultyRecord] = []
    fit_gaps: list[str] = []
    unsupported_claims: list[str] = []
    authenticity_risks: list[str] = []
    program_specific_rewrite_points: list[str] = []

    @field_validator(
        "fit_gaps", "unsupported_claims", "authenticity_risks",
        "program_specific_rewrite_points",
        mode="before",
    )
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class RevisionPlan(BaseModel):
    top_priorities: list[str] = []
    cuts: list[str] = []
    moves: list[str] = []
    emphasis_changes: list[str] = []
    revised_outline: list[str] = []
    revised_opening: str = ""

    @field_validator("top_priorities", "cuts", "moves", "emphasis_changes", "revised_outline", mode="before")
    @classmethod
    def coerce_str_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v) if isinstance(v, list) else v


class PriorityIssue(BaseModel):
    issue: str
    priority: str  # critical | high | medium | low
    agents_flagging: list[str]
    quoted_passage: str = ""
    venue_grounding: str = ""
    suggested_fix: str


class FinalReport(BaseModel):
    session_id: str
    venue: str = "generic_academic"
    venue_fit_verdict: str = ""   # above_bar | at_bar | below_bar
    venue_fit_confidence: str = ""  # high | medium | low
    executive_summary: str
    top_issues: list[PriorityIssue]
    audience_reactions: list[PersonaFeedback]
    narrative_section: NarrativeFeedback
    clarity_section: ClarityFeedback
    qa_predictions: Optional[QAPrediction] = None
    delivery_section: Optional[DeliveryFeedback] = None
    delivery_metrics: Optional[DeliveryMetrics] = None
    transcript_segments: list[TranscriptSegment] = []
    application_fit: Optional[ApplicationFitReport] = None
    revision_plan: RevisionPlan


# --- Request / Response models ---

class AnalyzeRequest(BaseModel):
    document: InputDocument
    context: UserContext


class AnalyzeResponse(BaseModel):
    session_id: str
    report: FinalReport


class AnalyzeApplicationRequest(BaseModel):
    document: InputDocument
    context: UserContext
    target: ApplicationTarget


class ReviseRequest(BaseModel):
    session_id: str
    new_text: str
    focus_area: Optional[str] = None


class CompareRequest(BaseModel):
    session_id: str
    new_text: str
