import type { AnalyzeResponse, ApplicationTarget, CompareResponse, DocType, AudienceType, GoalType, VenueType } from "./types";

const BASE = "/api";

export async function analyzeText(params: {
  rawText: string;
  docType: DocType;
  audienceType: AudienceType;
  goalType: GoalType;
  venue: VenueType;
  domain: string;
  userNotes: string;
  title: string;
}): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document: {
        raw_text: params.rawText,
        doc_type: params.docType,
        title: params.title,
      },
      context: {
        venue: params.venue,
        audience_type: params.audienceType,
        goal_type: params.goalType,
        domain: params.domain,
        user_notes: params.userNotes,
      },
    }),
    signal: AbortSignal.timeout(300_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function analyzeFile(params: {
  file: File;
  docType: DocType;
  audienceType: AudienceType;
  goalType: GoalType;
  venue: VenueType;
  domain: string;
  userNotes: string;
  title: string;
}): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("doc_type", params.docType);
  form.append("audience_type", params.audienceType);
  form.append("goal_type", params.goalType);
  form.append("venue", params.venue);
  form.append("domain", params.domain);
  form.append("user_notes", params.userNotes);
  form.append("title", params.title || params.file.name);

  const res = await fetch(`${BASE}/analyze/upload`, {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(300_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function analyzeRehearsal(params: {
  audioFile: File;
  slideFile?: File | null;
  docType: DocType;
  audienceType: AudienceType;
  goalType: GoalType;
  venue: VenueType;
  domain: string;
  userNotes: string;
  title: string;
}): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("audio_file", params.audioFile);
  if (params.slideFile) form.append("slide_file", params.slideFile);
  form.append("doc_type", params.docType);
  form.append("audience_type", params.audienceType);
  form.append("goal_type", params.goalType);
  form.append("venue", params.venue);
  form.append("domain", params.domain);
  form.append("user_notes", params.userNotes);
  form.append("title", params.title || params.audioFile.name);

  const res = await fetch(`${BASE}/analyze-rehearsal`, {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(420_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function analyzeApplication(params: {
  rawText: string;
  docType: DocType;
  audienceType: AudienceType;
  goalType: GoalType;
  venue: VenueType;
  domain: string;
  userNotes: string;
  title: string;
  target: ApplicationTarget;
}): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze-application`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document: {
        raw_text: params.rawText,
        doc_type: params.docType,
        title: params.title,
        source_type: "application",
      },
      context: {
        venue: params.venue,
        audience_type: params.audienceType,
        goal_type: params.goalType,
        domain: params.domain,
        user_notes: params.userNotes,
        application_target: params.target,
      },
      target: params.target,
    }),
    signal: AbortSignal.timeout(420_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Application analysis error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function getSession(sessionId: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/session/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${sessionId}`);
  const report = await res.json();
  return { session_id: sessionId, report };
}

export async function getBaseline(
  sessionId: string
): Promise<{ baseline_feedback: string }> {
  const res = await fetch(`${BASE}/baseline/${sessionId}`, {
    method: "POST",
    signal: AbortSignal.timeout(120_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Baseline error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function compareDraft(params: {
  sessionId: string;
  newText: string;
}): Promise<CompareResponse> {
  const res = await fetch(`${BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: params.sessionId,
      new_text: params.newText,
    }),
    signal: AbortSignal.timeout(300_000),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Compare error ${res.status}: ${detail}`);
  }
  return res.json();
}
