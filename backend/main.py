import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import (
    AnalyzeRequest, AnalyzeResponse, FinalReport,
    InputDocument, UserContext, DocType, AudienceType, GoalType, VenueType,
    ReviseRequest, CompareRequest, AnalyzeApplicationRequest, ApplicationTarget,
)
from backend.graph.pipeline import run_pipeline, run_rehearsal_pipeline, run_application_pipeline
from backend.storage.db import init_db, save_session, get_session, get_session_record
from backend.utils.parsing import (
    extract_text_from_pdf, extract_text_from_docx,
    extract_text_from_pptx, clean_text,
)
from backend.utils.audio import (
    align_segments_to_slides, compute_delivery_metrics,
    transcript_text, transcribe_audio,
)
from backend.utils.throttle import apply_litellm_throttle
from backend.utils.venue_loader import load_venues, get_venue_context
from backend.utils.throttle import acompletion_with_retry

app = FastAPI(title="StoryCoach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

_SUPPORTED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "video/mp4",
}


@app.on_event("startup")
def startup():
    init_db()
    apply_litellm_throttle()
    load_venues()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    report = await run_pipeline(request.document, request.context)
    save_session(
        report,
        doc_type=request.document.doc_type,
        audience_type=request.context.audience_type,
        goal_type=request.context.goal_type,
        raw_text=request.document.raw_text,
        venue=request.context.venue,
    )
    return AnalyzeResponse(session_id=report.session_id, report=report)


@app.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    doc_type: DocType = Form(...),
    audience_type: AudienceType = Form(...),
    goal_type: GoalType = Form(...),
    venue: VenueType = Form(VenueType.generic_academic),
    domain: str = Form(""),
    user_notes: str = Form(""),
    title: str = Form(""),
):
    if file.content_type not in _SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Supported: PDF, TXT, DOCX, PPTX.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")

    if file.content_type == "application/pdf":
        raw_text = extract_text_from_pdf(content)
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raw_text = extract_text_from_docx(content)
    elif file.content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        raw_text = extract_text_from_pptx(content)
    else:
        raw_text = content.decode("utf-8")

    raw_text = clean_text(raw_text)

    document = InputDocument(
        title=title or file.filename or "",
        raw_text=raw_text,
        doc_type=doc_type,
    )
    context = UserContext(
        venue=venue,
        audience_type=audience_type,
        goal_type=goal_type,
        domain=domain,
        user_notes=user_notes,
    )

    report = await run_pipeline(document, context)
    save_session(
        report,
        doc_type=doc_type,
        audience_type=audience_type,
        goal_type=goal_type,
        raw_text=raw_text,
        venue=venue,
    )
    return AnalyzeResponse(session_id=report.session_id, report=report)


@app.post("/analyze-application", response_model=AnalyzeResponse)
async def analyze_application(request: AnalyzeApplicationRequest):
    context = request.context.model_copy(update={"application_target": request.target})
    report = await run_application_pipeline(request.document, context, request.target)
    save_session(
        report,
        doc_type=request.document.doc_type,
        audience_type=context.audience_type,
        goal_type=context.goal_type,
        raw_text=request.document.raw_text,
        venue=context.venue,
    )
    return AnalyzeResponse(session_id=report.session_id, report=report)


@app.get("/session/{session_id}", response_model=FinalReport)
def get_session_endpoint(session_id: str):
    report = get_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found.")
    return report


@app.post("/revise", response_model=AnalyzeResponse)
async def revise(request: ReviseRequest):
    prior = get_session_record(request.session_id)
    if not prior:
        raise HTTPException(status_code=404, detail="Prior session not found.")

    document = InputDocument(
        raw_text=clean_text(request.new_text),
        doc_type=prior.doc_type,
    )
    context = UserContext(
        venue=prior.venue or VenueType.generic_academic,
        audience_type=prior.audience_type,
        goal_type=prior.goal_type,
    )

    report = await run_pipeline(document, context)
    save_session(
        report,
        doc_type=prior.doc_type,
        audience_type=prior.audience_type,
        goal_type=prior.goal_type,
        raw_text=request.new_text,
        venue=prior.venue or "generic_academic",
        prior_session_id=request.session_id,
    )
    return AnalyzeResponse(session_id=report.session_id, report=report)


@app.post("/baseline/{session_id}")
async def baseline(session_id: str):
    record = get_session_record(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found.")

    venue_ctx = get_venue_context(record.venue or "generic_academic")
    venue_block = venue_ctx.to_prompt_block() if venue_ctx else ""

    prompt = f"""You are an expert academic communication coach.
Give detailed, actionable feedback on the following {record.doc_type} for a {record.audience_type} audience.
Identify the main problems, suggest specific fixes, and state whether this document would succeed at its goal.
{f"Venue context:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
--- DOCUMENT ---
{record.raw_text}
--- END ---

Provide your full feedback."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.5-pro",
        messages=[{"role": "user", "content": prompt}],
    )
    return {"baseline_feedback": response.choices[0].message.content}


@app.post("/analyze-rehearsal", response_model=AnalyzeResponse)
async def analyze_rehearsal(
    audio_file: UploadFile = File(...),
    slide_file: UploadFile | None = File(None),
    doc_type: DocType = Form(DocType.talk_outline),
    audience_type: AudienceType = Form(...),
    goal_type: GoalType = Form(...),
    venue: VenueType = Form(VenueType.generic_academic),
    domain: str = Form(""),
    user_notes: str = Form(""),
    title: str = Form(""),
):
    if audio_file.content_type not in _SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio type. Supported: MP3, MP4/M4A, WAV.",
        )

    audio_content = await audio_file.read()
    if len(audio_content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB).")

    slide_text = ""
    if slide_file:
        if slide_file.content_type != "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            raise HTTPException(status_code=400, detail="Slide alignment currently supports PPTX only.")
        slide_content = await slide_file.read()
        if len(slide_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Slide file too large (max 10MB).")
        slide_text = extract_text_from_pptx(slide_content)

    try:
        segments = await transcribe_audio(
            audio_content,
            audio_file.filename or "rehearsal_audio",
            audio_file.content_type or "application/octet-stream",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if slide_text:
        segments = align_segments_to_slides(segments, slide_text)
    metrics = compute_delivery_metrics(segments)
    raw_text = clean_text(transcript_text(segments))

    document = InputDocument(
        title=title or audio_file.filename or "Rehearsal transcript",
        raw_text=raw_text,
        doc_type=doc_type,
        source_type="rehearsal",
    )
    context = UserContext(
        venue=venue,
        audience_type=audience_type,
        goal_type=goal_type,
        domain=domain,
        user_notes=user_notes,
    )

    report = await run_rehearsal_pipeline(document, context, segments, metrics)
    save_session(
        report,
        doc_type=doc_type,
        audience_type=audience_type,
        goal_type=goal_type,
        raw_text=raw_text,
        venue=venue,
    )
    return AnalyzeResponse(session_id=report.session_id, report=report)


@app.post("/compare")
async def compare(request: CompareRequest):
    prior_report = get_session(request.session_id)
    prior_record = get_session_record(request.session_id)
    if not prior_report or not prior_record:
        raise HTTPException(status_code=404, detail="Prior session not found.")

    document = InputDocument(
        raw_text=clean_text(request.new_text),
        doc_type=prior_record.doc_type,
    )
    context = UserContext(
        venue=prior_record.venue or VenueType.generic_academic,
        audience_type=prior_record.audience_type,
        goal_type=prior_record.goal_type,
    )

    new_report = await run_pipeline(document, context)
    save_session(
        new_report,
        doc_type=prior_record.doc_type,
        audience_type=prior_record.audience_type,
        goal_type=prior_record.goal_type,
        raw_text=request.new_text,
        venue=prior_record.venue or "generic_academic",
        prior_session_id=request.session_id,
    )

    old_issues = {issue.issue for issue in prior_report.top_issues}
    new_issues = {issue.issue for issue in new_report.top_issues}

    return {
        "new_session_id": new_report.session_id,
        "new_report": new_report,
        "improvement_summary": {
            "resolved_count": len(old_issues - new_issues),
            "new_count": len(new_issues - old_issues),
            "persisted_count": len(old_issues & new_issues),
        },
    }
