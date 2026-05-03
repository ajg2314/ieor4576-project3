"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { compareDraft, getSession, getBaseline } from "@/lib/api";
import type { CompareResponse, FinalReport, QAPredictionItem, TranscriptSegment } from "@/lib/types";
import { Loader2, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

const PRIORITY_COLOR: Record<string, string> = {
  critical: "bg-red-900 text-white border-red-900",
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-green-100 text-green-700 border-green-200",
};

const VERDICT_CONFIG = {
  above_bar: { bg: "bg-green-600", text: "✓ Above Bar", sub: "This document would likely clear the bar at this venue." },
  at_bar: { bg: "bg-amber-500", text: "≈ At Bar", sub: "This document is borderline — improvements could push it over." },
  below_bar: { bg: "bg-red-600", text: "✗ Below Bar", sub: "Significant revisions needed before this document meets venue standards." },
};

const QA_HANDLE_COLOR: Record<string, string> = {
  yes: "bg-green-100 text-green-700",
  partial: "bg-yellow-100 text-yellow-700",
  no: "bg-red-100 text-red-700",
};

const LIKELIHOOD_COLOR: Record<string, string> = {
  high: "bg-slate-700 text-white",
  medium: "bg-slate-200 text-slate-700",
  low: "bg-slate-100 text-slate-500",
};

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white border border-slate-100 rounded-xl shadow-sm mb-4">
      <button
        className="w-full flex justify-between items-center px-6 py-4 text-left font-semibold text-slate-800"
        onClick={() => setOpen(!open)}
      >
        {title}
        {open ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
      </button>
      {open && <div className="px-6 pb-6">{children}</div>}
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items?.length) return <p className="text-slate-400 text-sm italic">None flagged.</p>;
  return (
    <ul className="list-disc list-inside space-y-1 text-sm text-slate-700">
      {items.map((item, i) => <li key={i}>{item}</li>)}
    </ul>
  );
}

function QAItem({ item }: { item: QAPredictionItem }) {
  return (
    <div className="border border-slate-100 rounded-lg p-4">
      <div className="flex flex-wrap items-start gap-2 mb-2">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${LIKELIHOOD_COLOR[item.likelihood]}`}>
          {item.likelihood} likelihood
        </span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${QA_HANDLE_COLOR[item.draft_handles]}`}>
          Draft: {item.draft_handles}
        </span>
      </div>
      <p className="text-sm font-medium text-slate-800 mb-1">{item.question}</p>
      {item.suggested_response_stub && (
        <p className="text-xs text-slate-500 mt-2 leading-relaxed">
          <span className="font-medium text-slate-600">Suggested response: </span>
          {item.suggested_response_stub}
        </p>
      )}
    </div>
  );
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${minutes}:${secs}`;
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-slate-800">{value}</p>
    </div>
  );
}

function PacingChart({ segments }: { segments: TranscriptSegment[] }) {
  const chartSegments = segments.filter((segment) => segment.end_seconds > segment.start_seconds).slice(0, 24);
  if (!chartSegments.length) return null;
  const maxWpm = Math.max(...chartSegments.map((segment) => segment.wpm), 200);

  return (
    <div>
      <p className="text-xs font-semibold text-slate-600 mb-2">Pacing Chart</p>
      <div className="h-32 flex items-end gap-1 border border-slate-100 rounded-lg bg-slate-50 px-3 py-2">
        {chartSegments.map((segment, i) => {
          const height = Math.max(10, Math.min(100, (segment.wpm / maxWpm) * 100));
          const color = segment.wpm < 90 ? "bg-red-400" : segment.wpm > 190 ? "bg-amber-400" : "bg-brand-500";
          return (
            <div key={`${segment.start_seconds}-${i}`} className="flex-1 min-w-0 flex flex-col items-center justify-end gap-1">
              <div
                className={`w-full max-w-5 rounded-sm ${color}`}
                style={{ height: `${height}%` }}
                title={`${formatTime(segment.start_seconds)}-${formatTime(segment.end_seconds)}: ${segment.wpm.toFixed(0)} WPM`}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>{formatTime(chartSegments[0].start_seconds)}</span>
        <span>{formatTime(chartSegments[chartSegments.length - 1].end_seconds)}</span>
      </div>
    </div>
  );
}

function FillerHeatmap({ segments }: { segments: TranscriptSegment[] }) {
  const heatSegments = segments.filter((segment) => segment.end_seconds > segment.start_seconds).slice(0, 32);
  if (!heatSegments.length) return null;
  const maxFillers = Math.max(...heatSegments.map((segment) => segment.filler_word_count), 1);

  return (
    <div>
      <p className="text-xs font-semibold text-slate-600 mb-2">Filler Heatmap</p>
      <div className="grid grid-cols-8 gap-1">
        {heatSegments.map((segment, i) => {
          const intensity = segment.filler_word_count / maxFillers;
          const color = intensity === 0
            ? "bg-slate-100"
            : intensity < 0.35
              ? "bg-yellow-200"
              : intensity < 0.7
                ? "bg-orange-300"
                : "bg-red-400";
          return (
            <div
              key={`${segment.start_seconds}-${i}`}
              className={`h-7 rounded ${color}`}
              title={`${formatTime(segment.start_seconds)}-${formatTime(segment.end_seconds)}: ${segment.filler_word_count} fillers`}
            />
          );
        })}
      </div>
    </div>
  );
}

const APPLICATION_VERDICT: Record<string, { label: string; color: string }> = {
  strong_fit: { label: "Strong Fit", color: "bg-green-600 text-white" },
  plausible_fit: { label: "Plausible Fit", color: "bg-amber-500 text-white" },
  weak_fit: { label: "Weak / Unverified Fit", color: "bg-red-600 text-white" },
};

export default function ResultsPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [report, setReport] = useState<FinalReport | null>(null);
  const [error, setError] = useState("");

  const [baselineText, setBaselineText] = useState<string | null>(null);
  const [baselineLoading, setBaselineLoading] = useState(false);
  const [baselineError, setBaselineError] = useState("");
  const [baselineOpen, setBaselineOpen] = useState(false);
  const [compareText, setCompareText] = useState("");
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState("");

  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId)
      .then((r) => setReport(r.report))
      .catch((e) => setError(e.message));
  }, [sessionId]);

  async function loadBaseline() {
    if (baselineText) { setBaselineOpen(true); return; }
    setBaselineLoading(true);
    setBaselineError("");
    try {
      const { baseline_feedback } = await getBaseline(sessionId);
      setBaselineText(baseline_feedback);
      setBaselineOpen(true);
    } catch (e: unknown) {
      setBaselineError(e instanceof Error ? e.message : "Failed to load baseline.");
    } finally {
      setBaselineLoading(false);
    }
  }

  async function runCompare() {
    if (!compareText.trim()) return;
    setCompareLoading(true);
    setCompareError("");
    try {
      const result = await compareDraft({ sessionId, newText: compareText });
      setCompareResult(result);
    } catch (e: unknown) {
      setCompareError(e instanceof Error ? e.message : "Failed to compare drafts.");
    } finally {
      setCompareLoading(false);
    }
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 text-red-500" size={36} />
          <p className="text-red-600">{error}</p>
          <a href="/analyze" className="text-brand-600 text-sm mt-4 inline-block">← New analysis</a>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-brand-600" size={36} />
      </div>
    );
  }

  const verdict = report.venue_fit_verdict ? VERDICT_CONFIG[report.venue_fit_verdict] : null;

  return (
    <main className="min-h-screen bg-slate-50 py-12 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <a href="/analyze" className="text-brand-600 text-sm">← New analysis</a>
            <h1 className="text-3xl font-bold text-slate-900 mt-1">Analysis Report</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Session: {report.session_id} · Venue: <span className="font-medium capitalize">{report.venue?.replace("_", " ")}</span>
            </p>
          </div>
        </div>

        {/* Venue-fit verdict */}
        {verdict && (
          <div className={`${verdict.bg} text-white rounded-xl px-6 py-4 mb-4 flex items-center justify-between shadow`}>
            <div>
              <p className="text-lg font-bold">{verdict.text}</p>
              <p className="text-sm opacity-80 mt-0.5">{verdict.sub}</p>
            </div>
            {report.venue_fit_confidence && (
              <span className="text-xs font-semibold bg-white/20 px-3 py-1 rounded-full whitespace-nowrap">
                {report.venue_fit_confidence} confidence
              </span>
            )}
          </div>
        )}

        {/* Executive Summary */}
        <div className="bg-brand-600 text-white rounded-xl p-6 mb-4 shadow">
          <h2 className="font-semibold text-lg mb-2">Executive Summary</h2>
          <p className="text-brand-100 text-sm leading-relaxed">{report.executive_summary}</p>
        </div>

        {/* Application Fit */}
        {report.application_fit ? (
          <Section title="Application Fit Research">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                APPLICATION_VERDICT[report.application_fit.program_fit_verdict]?.color || "bg-slate-200 text-slate-700"
              }`}>
                {APPLICATION_VERDICT[report.application_fit.program_fit_verdict]?.label || "Fit Not Scored"}
              </span>
              <span className="text-xs text-slate-400">
                Source-grounded faculty claims only; unverified claims are flagged.
              </span>
            </div>
            {!!report.application_fit.verified_faculty_matches?.length && (
              <div className="mb-5">
                <p className="text-xs font-semibold text-slate-600 mb-2">Verified Faculty Matches</p>
                <div className="space-y-3">
                  {report.application_fit.verified_faculty_matches.map((match, i) => (
                    <div key={`${match.faculty_name}-${i}`} className="border border-slate-100 rounded-lg p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                        <p className="text-sm font-semibold text-slate-800">{match.faculty_name}</p>
                        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                          {match.confidence} confidence · {Math.round(match.fit_score)} fit
                        </span>
                      </div>
                      <p className="text-sm text-slate-700 leading-relaxed">{match.why_match}</p>
                      {!!match.source_urls?.length && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {match.source_urls.slice(0, 3).map((url) => (
                            <a key={url} href={url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 hover:text-brand-700 break-all">
                              Source
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-red-600 mb-1">Fit Gaps</p>
                <BulletList items={report.application_fit.fit_gaps} />
              </div>
              <div>
                <p className="text-xs font-semibold text-orange-600 mb-1">Unsupported Claims</p>
                <BulletList items={report.application_fit.unsupported_claims} />
              </div>
              <div>
                <p className="text-xs font-semibold text-yellow-700 mb-1">Authenticity Risks</p>
                <BulletList items={report.application_fit.authenticity_risks} />
              </div>
              <div>
                <p className="text-xs font-semibold text-brand-700 mb-1">Program-Specific Rewrites</p>
                <BulletList items={report.application_fit.program_specific_rewrite_points} />
              </div>
            </div>
          </Section>
        ) : null}

        {/* Top Issues */}
        <Section title={`Top Issues (${report.top_issues.length})`}>
          <div className="space-y-4">
            {report.top_issues.map((issue, i) => (
              <div key={i} className={`border rounded-lg p-4 ${PRIORITY_COLOR[issue.priority] || "bg-slate-50 border-slate-200 text-slate-700"}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wide">{issue.priority}</span>
                  <span className="text-xs opacity-60">flagged by: {issue.agents_flagging?.join(", ")}</span>
                </div>
                <p className="font-medium text-sm mb-1">{issue.issue}</p>
                {issue.quoted_passage && (
                  <blockquote className="border-l-2 border-current pl-3 my-2 text-xs opacity-75 italic">
                    {issue.quoted_passage}
                  </blockquote>
                )}
                {issue.venue_grounding && (
                  <p className="text-xs mt-2 opacity-70">
                    <span className="font-semibold">Venue: </span>{issue.venue_grounding}
                  </p>
                )}
                <p className="text-xs mt-2 opacity-80"><strong>Fix:</strong> {issue.suggested_fix}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Q&A Predictions */}
        {report.qa_predictions?.questions?.length ? (
          <Section title={`Predicted Q&A (${report.qa_predictions.questions.length} questions)`}>
            <p className="text-xs text-slate-500 mb-4">
              Questions this venue's audience is likely to ask — and how well your draft handles each.
            </p>
            <div className="space-y-3">
              {report.qa_predictions.questions.map((q, i) => (
                <QAItem key={i} item={q} />
              ))}
            </div>
          </Section>
        ) : null}

        {/* Delivery Coach */}
        {report.delivery_section ? (
          <Section title="Delivery Coach">
            {report.delivery_metrics && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <MetricTile label="Duration" value={`${Math.round(report.delivery_metrics.total_duration_seconds / 60)} min`} />
                <MetricTile label="Average pace" value={`${report.delivery_metrics.average_wpm.toFixed(0)} WPM`} />
                <MetricTile label="Pace variance" value={report.delivery_metrics.wpm_variance.toFixed(0)} />
                <MetricTile label="Fillers" value={`${report.delivery_metrics.filler_word_total}`} />
              </div>
            )}
            {!!report.transcript_segments?.length && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
                <PacingChart segments={report.transcript_segments} />
                <FillerHeatmap segments={report.transcript_segments} />
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs font-semibold text-red-600 mb-1">Pacing Issues</p>
                <BulletList items={report.delivery_section.pacing_issues} />
              </div>
              <div>
                <p className="text-xs font-semibold text-orange-600 mb-1">Filler Hotspots</p>
                <BulletList items={report.delivery_section.filler_hotspots} />
              </div>
            </div>
            {!!report.delivery_section.slide_mismatch_flags?.length && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-blue-600 mb-1">Slide-Speech Mismatch</p>
                <BulletList items={report.delivery_section.slide_mismatch_flags} />
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
                <p className="text-xs font-semibold text-slate-600 mb-1">Opening</p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {report.delivery_section.weak_opening_notes || "No opening-specific note."}
                </p>
              </div>
              <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
                <p className="text-xs font-semibold text-slate-600 mb-1">Closing</p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {report.delivery_section.weak_closing_notes || "No closing-specific note."}
                </p>
              </div>
            </div>
            <p className="text-xs font-semibold text-slate-600 mb-1">Ranked Delivery Fixes</p>
            <BulletList items={report.delivery_section.ranked_delivery_fixes} />
          </Section>
        ) : null}

        {/* Persona Reactions */}
        <Section title="Audience Reactions">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {report.audience_reactions.map((persona, i) => (
              <div key={i} className="border border-slate-100 rounded-lg p-4">
                <h3 className="font-semibold text-slate-800 text-sm mb-0.5">{persona.persona_name}</h3>
                <p className="text-xs text-slate-500 mb-2">{persona.persona_description}</p>
                <p className="text-sm text-slate-700 mb-3 italic">&ldquo;{persona.overall_reaction}&rdquo;</p>
                {!!persona.confusion_points?.length && (
                  <div className="mb-2">
                    <p className="text-xs font-medium text-red-600 mb-1">Confusion points</p>
                    <BulletList items={persona.confusion_points} />
                  </div>
                )}
                {!!persona.interest_points?.length && (
                  <div className="mb-2">
                    <p className="text-xs font-medium text-green-700 mb-1">Interest points</p>
                    <BulletList items={persona.interest_points} />
                  </div>
                )}
                {!!persona.questions_remaining?.length && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">Questions remaining</p>
                    <BulletList items={persona.questions_remaining} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>

        {/* Narrative */}
        <Section title="Narrative Coach">
          <p className="text-sm text-slate-700 mb-4 leading-relaxed">{report.narrative_section.arc_summary}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-green-700 mb-1">Strengths</p>
              <BulletList items={report.narrative_section.strengths} />
            </div>
            <div>
              <p className="text-xs font-semibold text-red-600 mb-1">Weaknesses</p>
              <BulletList items={report.narrative_section.weaknesses} />
            </div>
          </div>
          {!!report.narrative_section.ordering_issues?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-yellow-700 mb-1">Ordering Issues</p>
              <BulletList items={report.narrative_section.ordering_issues} />
            </div>
          )}
          {!!report.narrative_section.revision_suggestions?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-slate-600 mb-1">Suggestions</p>
              <BulletList items={report.narrative_section.revision_suggestions} />
            </div>
          )}
        </Section>

        {/* Clarity */}
        <Section title="Clarity Coach">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-red-600 mb-1">Jargon Issues</p>
              <BulletList items={report.clarity_section.jargon_issues} />
            </div>
            <div>
              <p className="text-xs font-semibold text-yellow-700 mb-1">Undefined Terms</p>
              <BulletList items={report.clarity_section.undefined_terms} />
            </div>
          </div>
          {!!report.clarity_section.dense_sections?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-slate-600 mb-1">Dense Sections</p>
              <BulletList items={report.clarity_section.dense_sections} />
            </div>
          )}
          {!!report.clarity_section.clarification_suggestions?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-slate-600 mb-1">Suggestions</p>
              <BulletList items={report.clarity_section.clarification_suggestions} />
            </div>
          )}
        </Section>

        {/* Revision Plan */}
        <Section title="Revision Plan">
          {report.revision_plan.revised_opening && (
            <div className="mb-5 bg-brand-50 border border-brand-100 rounded-lg p-4">
              <p className="text-xs font-semibold text-brand-700 mb-1">Suggested Revised Opening</p>
              <p className="text-sm text-slate-700 leading-relaxed">{report.revision_plan.revised_opening}</p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-semibold text-red-600 mb-1">Top Priorities</p>
              <BulletList items={report.revision_plan.top_priorities} />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-600 mb-1">Revised Outline</p>
              <ol className="list-decimal list-inside space-y-1 text-sm text-slate-700">
                {report.revision_plan.revised_outline?.map((item, i) => <li key={i}>{item}</li>)}
              </ol>
            </div>
          </div>
          {!!report.revision_plan.cuts?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-orange-600 mb-1">Suggested Cuts</p>
              <BulletList items={report.revision_plan.cuts} />
            </div>
          )}
          {!!report.revision_plan.moves?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-blue-600 mb-1">Suggested Moves</p>
              <BulletList items={report.revision_plan.moves} />
            </div>
          )}
          {!!report.revision_plan.emphasis_changes?.length && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-purple-600 mb-1">Emphasis Changes</p>
              <BulletList items={report.revision_plan.emphasis_changes} />
            </div>
          )}
        </Section>

        {/* Baseline Comparison (Phase 9E) */}
        <div className="bg-white border border-slate-100 rounded-xl shadow-sm mb-4">
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-800">Baseline Comparison</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Single Gemini 2.5 Pro prompt on the same input — see what multi-agent adds.
              </p>
            </div>
            <button
              onClick={() => baselineOpen ? setBaselineOpen(false) : loadBaseline()}
              disabled={baselineLoading}
              className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 disabled:opacity-50 whitespace-nowrap ml-4"
            >
              {baselineLoading ? (
                <><Loader2 className="animate-spin" size={14} /> Loading…</>
              ) : baselineOpen ? (
                <><ChevronUp size={14} /> Hide</>
              ) : (
                <><ChevronDown size={14} /> Show comparison</>
              )}
            </button>
          </div>
          {baselineOpen && (
            <div className="px-6 pb-6 border-t border-slate-100">
              {baselineError ? (
                <p className="text-sm text-red-500 mt-4">{baselineError}</p>
              ) : (
                <div className="mt-4 prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap text-sm leading-relaxed">
                  {baselineText}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Draft Comparison */}
        <Section title="Compare Revised Draft" defaultOpen={false}>
          <textarea
            value={compareText}
            onChange={(e) => setCompareText(e.target.value)}
            rows={7}
            placeholder="Paste a revised version here to see which issues were resolved, persisted, or newly introduced."
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              onClick={runCompare}
              disabled={compareLoading || !compareText.trim()}
              className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold px-4 py-2 rounded-lg transition-colors text-sm"
            >
              {compareLoading ? "Comparing..." : "Compare Draft"}
            </button>
            {compareError && <p className="text-sm text-red-500">{compareError}</p>}
          </div>
          {compareResult && (
            <div className="mt-5 border border-slate-100 rounded-lg p-4 bg-slate-50">
              <div className="grid grid-cols-3 gap-3 mb-4">
                <MetricTile label="Resolved" value={`${compareResult.improvement_summary.resolved_count}`} />
                <MetricTile label="Persisted" value={`${compareResult.improvement_summary.persisted_count}`} />
                <MetricTile label="New" value={`${compareResult.improvement_summary.new_count}`} />
              </div>
              <p className="text-sm text-slate-700 leading-relaxed mb-3">
                {compareResult.new_report.executive_summary}
              </p>
              <a
                href={`/results/${compareResult.new_session_id}`}
                className="text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                Open revised report →
              </a>
            </div>
          )}
        </Section>

        <div className="text-center py-8">
          <a href="/analyze" className="bg-brand-600 hover:bg-brand-700 text-white font-semibold px-6 py-3 rounded-lg transition-colors text-sm">
            Analyze Another Document →
          </a>
        </div>
      </div>
    </main>
  );
}
