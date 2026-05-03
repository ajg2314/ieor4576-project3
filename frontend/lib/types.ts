export type DocType =
  | "talk_outline"
  | "slide_text"
  | "abstract"
  | "introduction"
  | "paper_section"
  | "grant_aims"
  | "statement_of_purpose"
  | "personal_statement"
  | "research_statement"
  | "diversity_statement"
  | "faculty_email"
  | "fellowship_essay";

export type AudienceType =
  | "undergraduates"
  | "grad_students_in_field"
  | "grad_students_outside_field"
  | "experts"
  | "interdisciplinary"
  | "hiring_committee";

export type GoalType =
  | "explain_clearly"
  | "persuade"
  | "present_research"
  | "teach";

export type VenueType =
  | "neurips"
  | "icml"
  | "cvpr"
  | "nsf"
  | "nih_r01"
  | "job_talk"
  | "generic_academic"
  | "graduate_sop"
  | "phd_application"
  | "masters_application"
  | "nsf_grfp"
  | "faculty_outreach"
  | "custom";

export type VenueFitVerdict = "above_bar" | "at_bar" | "below_bar" | "";
export type VenueFitConfidence = "high" | "medium" | "low" | "";

export interface PriorityIssue {
  issue: string;
  priority: "critical" | "high" | "medium" | "low";
  agents_flagging: string[];
  quoted_passage: string;
  venue_grounding: string;
  suggested_fix: string;
}

export interface PersonaFeedback {
  persona_name: string;
  persona_description: string;
  overall_reaction: string;
  confusion_points: string[];
  interest_points: string[];
  questions_remaining: string[];
}

export interface NarrativeFeedback {
  arc_summary: string;
  strengths: string[];
  weaknesses: string[];
  ordering_issues: string[];
  revision_suggestions: string[];
}

export interface ClarityFeedback {
  jargon_issues: string[];
  undefined_terms: string[];
  dense_sections: string[];
  clarification_suggestions: string[];
}

export interface QAPredictionItem {
  question: string;
  likelihood: "high" | "medium" | "low";
  draft_handles: "yes" | "partial" | "no";
  suggested_response_stub: string;
}

export interface QAPrediction {
  questions: QAPredictionItem[];
}

export interface DeliveryFeedback {
  pacing_issues: string[];
  filler_hotspots: string[];
  slide_mismatch_flags: string[];
  weak_opening_notes: string;
  weak_closing_notes: string;
  ranked_delivery_fixes: string[];
}

export interface DeliveryMetrics {
  total_duration_seconds: number;
  average_wpm: number;
  wpm_variance: number;
  filler_word_total: number;
  filler_word_density_per_minute: number;
  pacing_dropouts: string[];
  slide_speech_mismatches: string[];
}

export interface TranscriptSegment {
  start_seconds: number;
  end_seconds: number;
  text: string;
  wpm: number;
  filler_word_count: number;
  aligned_slide: string | null;
}

export interface ApplicationTarget {
  school_name: string;
  program_name: string;
  program_url: string;
  research_interests: string[];
}

export interface FacultyRecord {
  name: string;
  title: string;
  profile_url: string;
  lab_url: string;
  research_areas: string[];
  evidence_snippets: string[];
  retrieved_at: string;
  verification_status: "verified" | "partial" | "unverified" | string;
}

export interface FacultyFitMatch {
  faculty_name: string;
  fit_score: number;
  confidence: "high" | "medium" | "low" | string;
  why_match: string;
  source_urls: string[];
  relevant_papers_or_projects: string[];
}

export interface ApplicationFitReport {
  program_fit_verdict: "strong_fit" | "plausible_fit" | "weak_fit" | "";
  verified_faculty_matches: FacultyFitMatch[];
  faculty_records: FacultyRecord[];
  fit_gaps: string[];
  unsupported_claims: string[];
  authenticity_risks: string[];
  program_specific_rewrite_points: string[];
}

export interface RevisionPlan {
  top_priorities: string[];
  cuts: string[];
  moves: string[];
  emphasis_changes: string[];
  revised_outline: string[];
  revised_opening: string;
}

export interface FinalReport {
  session_id: string;
  venue: VenueType;
  venue_fit_verdict: VenueFitVerdict;
  venue_fit_confidence: VenueFitConfidence;
  executive_summary: string;
  top_issues: PriorityIssue[];
  audience_reactions: PersonaFeedback[];
  narrative_section: NarrativeFeedback;
  clarity_section: ClarityFeedback;
  qa_predictions: QAPrediction | null;
  delivery_section: DeliveryFeedback | null;
  delivery_metrics: DeliveryMetrics | null;
  transcript_segments: TranscriptSegment[];
  application_fit: ApplicationFitReport | null;
  revision_plan: RevisionPlan;
}

export interface AnalyzeResponse {
  session_id: string;
  report: FinalReport;
}

export interface CompareResponse {
  new_session_id: string;
  new_report: FinalReport;
  improvement_summary: {
    resolved_count: number;
    new_count: number;
    persisted_count: number;
  };
}
