"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { analyzeText, analyzeFile, analyzeRehearsal, analyzeApplication } from "@/lib/api";
import type { DocType, AudienceType, GoalType, VenueType } from "@/lib/types";
import { GraduationCap, Mic, Upload, FileText, Loader2 } from "lucide-react";

const VENUE_TYPES: { value: VenueType; label: string; description: string }[] = [
  { value: "neurips", label: "NeurIPS / ICML / CVPR", description: "ML conference talk (12 min)" },
  { value: "nsf", label: "NSF Grant Proposal", description: "CAREER or standard grant" },
  { value: "nih_r01", label: "NIH R01", description: "Research project grant" },
  { value: "job_talk", label: "Faculty Job Talk", description: "R1 hiring committee (50 min)" },
  { value: "graduate_sop", label: "Graduate SOP", description: "General application fit" },
  { value: "phd_application", label: "PhD Application", description: "Research-fit statement" },
  { value: "masters_application", label: "Master's Application", description: "Program-fit essay" },
  { value: "nsf_grfp", label: "NSF GRFP", description: "Fellowship application" },
  { value: "faculty_outreach", label: "Faculty Outreach", description: "Prospective advisor email" },
  { value: "icml", label: "ICML", description: "ML conference talk (12 min)" },
  { value: "cvpr", label: "CVPR", description: "Vision conference talk (12 min)" },
  { value: "generic_academic", label: "Generic Academic", description: "No specific venue norms" },
];

const DOC_TYPES: { value: DocType; label: string }[] = [
  { value: "talk_outline", label: "Talk Outline" },
  { value: "slide_text", label: "Slide Text" },
  { value: "abstract", label: "Abstract" },
  { value: "introduction", label: "Introduction" },
  { value: "paper_section", label: "Paper Section" },
  { value: "grant_aims", label: "Grant Specific Aims" },
  { value: "statement_of_purpose", label: "Statement of Purpose" },
  { value: "personal_statement", label: "Personal Statement" },
  { value: "research_statement", label: "Research Statement" },
  { value: "diversity_statement", label: "Diversity Statement" },
  { value: "faculty_email", label: "Faculty Outreach Email" },
  { value: "fellowship_essay", label: "Fellowship Essay" },
];

const AUDIENCE_TYPES: { value: AudienceType; label: string }[] = [
  { value: "undergraduates", label: "Undergraduates" },
  { value: "grad_students_in_field", label: "Grad Students (In Field)" },
  { value: "grad_students_outside_field", label: "Grad Students (Outside Field)" },
  { value: "experts", label: "Domain Experts" },
  { value: "interdisciplinary", label: "Interdisciplinary Audience" },
  { value: "hiring_committee", label: "Hiring Committee" },
];

const GOAL_TYPES: { value: GoalType; label: string }[] = [
  { value: "explain_clearly", label: "Explain Clearly" },
  { value: "persuade", label: "Persuade" },
  { value: "present_research", label: "Present Research" },
  { value: "teach", label: "Teach" },
];

const AGENT_STEPS = [
  "Content Analyst",
  "Program Research Agent",
  "Faculty Verifier",
  "Paper Fit Agent",
  "Persona: Smart Novice",
  "Persona: Grad Student",
  "Persona: Skeptical Expert",
  "Persona: Impatient Listener",
  "Narrative Coach",
  "Clarity Coach",
  "Q&A Predictor",
  "Delivery Coach",
  "SOP Fit Coach",
  "Authenticity Coach",
  "Revision Planner",
  "Synthesizer",
];

export default function AnalyzePage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [tab, setTab] = useState<"paste" | "upload" | "rehearsal" | "application">("paste");
  const [rawText, setRawText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [slideFile, setSlideFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [venue, setVenue] = useState<VenueType>("generic_academic");
  const [docType, setDocType] = useState<DocType>("talk_outline");
  const [audienceType, setAudienceType] = useState<AudienceType>("grad_students_in_field");
  const [goalType, setGoalType] = useState<GoalType>("present_research");
  const [domain, setDomain] = useState("");
  const [userNotes, setUserNotes] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [programName, setProgramName] = useState("");
  const [programUrl, setProgramUrl] = useState("");
  const [researchInterests, setResearchInterests] = useState("");

  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState("");

  function switchTab(nextTab: "paste" | "upload" | "rehearsal" | "application") {
    setTab(nextTab);
    if (nextTab === "application") {
      setVenue((current) => current === "generic_academic" ? "graduate_sop" : current);
      setDocType((current) => current === "talk_outline" ? "statement_of_purpose" : current);
      setAudienceType("hiring_committee");
      setGoalType("persuade");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    setCurrentStep(0);

    const stepInterval = setInterval(() => {
      setCurrentStep((s) => Math.min(s + 1, AGENT_STEPS.length - 1));
    }, 8000);

    try {
      const common = { docType, audienceType, goalType, venue, domain, userNotes, title };
      let result;
      if (tab === "application") {
        result = await analyzeApplication({
          rawText,
          ...common,
          target: {
            school_name: schoolName,
            program_name: programName,
            program_url: programUrl,
            research_interests: researchInterests
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          },
        });
      } else if (tab === "rehearsal" && audioFile) {
        result = await analyzeRehearsal({ audioFile, slideFile, ...common });
      } else if (tab === "upload" && file) {
        result = await analyzeFile({ file, ...common });
      } else {
        result = await analyzeText({ rawText, ...common });
      }
      clearInterval(stepInterval);
      router.push(`/results/${result.session_id}`);
    } catch (err: unknown) {
      clearInterval(stepInterval);
      setError(err instanceof Error ? err.message : "Unknown error");
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-10 max-w-md w-full text-center">
          <Loader2 className="animate-spin mx-auto mb-4 text-brand-600" size={40} />
          <h2 className="text-xl font-semibold text-slate-800 mb-6">
            {tab === "rehearsal" ? "Analyzing your rehearsal…" : "Analyzing your document…"}
          </h2>
          <ul className="text-left space-y-2">
            {AGENT_STEPS.map((step, i) => (
              <li key={step} className={`flex items-center gap-2 text-sm transition-colors ${
                i < currentStep ? "text-green-600" : i === currentStep ? "text-brand-600 font-medium" : "text-slate-300"
              }`}>
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  i < currentStep ? "bg-green-500" : i === currentStep ? "bg-brand-500 animate-pulse" : "bg-slate-200"
                }`} />
                {step}
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-400 mt-6">This takes ~60–90 seconds</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 py-12 px-6">
      <div className="max-w-2xl mx-auto">
        <a href="/" className="text-brand-600 text-sm mb-6 inline-block">← Back</a>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Analyze Document</h1>
        <p className="text-slate-500 mb-8">Paste text, upload a file, or critique a recorded rehearsal against venue norms.</p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-6 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Venue selector — prominent, first choice */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Venue <span className="text-brand-600 font-normal">(drives all grounded feedback)</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {VENUE_TYPES.map((v) => (
                <button
                  key={v.value}
                  type="button"
                  onClick={() => setVenue(v.value)}
                  className={`text-left border rounded-lg px-3 py-2.5 transition-colors ${
                    venue === v.value
                      ? "border-brand-500 bg-brand-50 text-brand-800"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  <p className="text-xs font-semibold leading-tight">{v.label}</p>
                  <p className="text-xs text-slate-400 leading-tight mt-0.5">{v.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Tab switcher */}
          <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
            {(["paste", "upload", "rehearsal", "application"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  tab === t ? "bg-white shadow text-slate-900" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {t === "paste" && <><FileText className="inline w-4 h-4 mr-1" />Paste Text</>}
                {t === "upload" && <><Upload className="inline w-4 h-4 mr-1" />Upload File</>}
                {t === "rehearsal" && <><Mic className="inline w-4 h-4 mr-1" />Rehearsal</>}
                {t === "application" && <><GraduationCap className="inline w-4 h-4 mr-1" />Application</>}
              </button>
            ))}
          </div>

          {/* Input */}
          {tab === "paste" || tab === "application" ? (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {tab === "application" ? "Application Draft" : "Document Text"}
              </label>
              <textarea
                required
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={10}
                placeholder={tab === "application"
                  ? "Paste your SOP, research statement, personal statement, fellowship essay, or faculty email here..."
                  : "Paste your talk outline, abstract, grant aims, or paper section here…"}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
              />
              {tab === "application" && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Target School</label>
                    <input
                      type="text"
                      value={schoolName}
                      onChange={(e) => setSchoolName(e.target.value)}
                      placeholder="e.g. Columbia University"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Program / Department</label>
                    <input
                      type="text"
                      value={programName}
                      onChange={(e) => setProgramName(e.target.value)}
                      placeholder="e.g. Computer Science PhD"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-1">Official Program URL</label>
                    <input
                      type="url"
                      value={programUrl}
                      onChange={(e) => setProgramUrl(e.target.value)}
                      placeholder="Best: official department/faculty page URL"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      If omitted, search requires backend Google Custom Search config.
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-1">Research Interests</label>
                    <input
                      type="text"
                      value={researchInterests}
                      onChange={(e) => setResearchInterests(e.target.value)}
                      placeholder="Comma-separated, e.g. online optimization, ML for routing"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                </div>
              )}
            </div>
          ) : tab === "upload" ? (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Upload file (PDF, TXT, DOCX, PPTX — max 10 MB)
              </label>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.txt,.docx,.pptx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                required={tab === "upload"}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full text-sm text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-100 file:text-brand-700 hover:file:bg-brand-200"
              />
              {file && <p className="text-xs text-slate-500 mt-1">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Rehearsal audio or video (MP3, M4A, WAV, MP4 — max 25 MB)
                </label>
                <input
                  type="file"
                  accept=".mp3,.m4a,.wav,.mp4,audio/*,video/mp4"
                  required={tab === "rehearsal"}
                  onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-100 file:text-brand-700 hover:file:bg-brand-200"
                />
                {audioFile && <p className="text-xs text-slate-500 mt-1">{audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Optional slide deck for alignment (PPTX — max 10 MB)
                </label>
                <input
                  type="file"
                  accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                  onChange={(e) => setSlideFile(e.target.files?.[0] ?? null)}
                  className="w-full text-sm text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
                />
                {slideFile && <p className="text-xs text-slate-500 mt-1">{slideFile.name} ({(slideFile.size / 1024).toFixed(1)} KB)</p>}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Title (optional)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. NeurIPS 2025 Talk Outline"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Selects */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Document Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value as DocType)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {DOC_TYPES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Audience</label>
              <select
                value={audienceType}
                onChange={(e) => setAudienceType(e.target.value as AudienceType)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {AUDIENCE_TYPES.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Goal</label>
              <select
                value={goalType}
                onChange={(e) => setGoalType(e.target.value as GoalType)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {GOAL_TYPES.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Domain (optional)</label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. Machine Learning, Operations Research"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes for the coach (optional)</label>
            <textarea
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              rows={2}
              placeholder="e.g. First draft, 15-minute talk slot, worried about section 2 being too dense"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3 rounded-lg transition-colors"
          >
            {tab === "rehearsal" && "Analyze Rehearsal →"}
            {tab === "application" && "Analyze Application →"}
            {(tab === "paste" || tab === "upload") && "Analyze Document →"}
          </button>
        </form>
      </div>
    </main>
  );
}
