# StoryCoach — Development Log

**Project:** StoryCoach — agent-based communication coach for talks, papers, presentations, and academic applications  
**Course:** IEOR 4576, Project 3  
**Team:** Andy Gu  
**Deadline:** TBD  
**Live URL:** TBD  

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI |
| Package manager | uv |
| Agent orchestration | LangGraph |
| LLM client | LiteLLM for the agent pipeline; Google Gen AI SDK for Vertex/Gemini Google Search grounding |
| Models | Gemini 2.0 Flash (simple agents), Gemini 2.5 Pro (Narrative Coach, Revision Planner, Synthesizer, application coach), Gemini 2.5 Flash for search grounding |
| Storage | SQLite + SQLAlchemy |
| Frontend | Next.js |
| Deployment | Google Cloud Run |

---

## Repo Structure

```
storycoach/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── agents/
│   │   ├── content_analyst.py   # extracts main claim, structure, density
│   │   ├── persona_agents.py    # 4 audience personas (separate LLM calls)
│   │   ├── narrative_coach.py   # story arc, motivation, ordering (2.5 Pro)
│   │   ├── clarity_coach.py     # jargon, undefined terms, dense sections
│   │   ├── qa_predictor.py      # likely audience / committee questions
│   │   ├── delivery_coach.py    # rehearsal pacing, filler, slide mismatch feedback
│   │   ├── application_coach.py # source-grounded SOP/program-fit report
│   │   ├── revision_planner.py  # top fixes, cuts, moves, revised outline (2.5 Pro)
│   │   └── synthesizer.py       # dedup + rank + final report (2.5 Pro)
│   ├── graph/
│   │   └── pipeline.py          # LangGraph DAG definition
│   ├── models/
│   │   └── schemas.py           # all Pydantic models
│   ├── storage/
│   │   └── db.py                # SQLAlchemy session storage
│   ├── venues/                  # venue/application YAML context blocks
│   └── utils/
│       ├── parsing.py           # text/PDF/docx/pptx ingestion
│       ├── audio.py             # Google Speech-to-Text + slide alignment helpers
│       ├── program_research.py  # Vertex search grounding + official-site crawl
│       └── venue_loader.py      # loads venue YAML into agent prompts
├── frontend/                    # Next.js app
├── pyproject.toml               # uv-managed dependencies
├── .env.example
├── Dockerfile
├── README.md
├── business_onepager.md
├── developmentlog.md
└── projectidea.md
```

### LangGraph Execution DAG

```
Input + UserContext
        ↓
[content_analyst_node]              ← Gemini 2.0 Flash, runs first
        ↓
[persona_1] [persona_2] [persona_3] [persona_4]
[narrative_coach] [clarity_coach] [qa_predictor]
        ↓
[delivery_coach]                    ← rehearsal mode only
        ↓
[application_coach]                 ← application mode, after program research
        ↓
[revision_planner_node]             ← Gemini 2.5 Pro
        ↓
[synthesizer_node]                  ← Gemini 2.5 Pro, produces FinalReport
```

---

## Phase 0: Setup ✅

- [x] Init repo with uv (`uv init`)
- [x] Add dependencies: `fastapi uvicorn langgraph litellm sqlalchemy pydantic python-dotenv pymupdf python-multipart`
- [x] Create `.env.example` with Google / Vertex AI env vars
- [x] Verify LiteLLM can call Gemini through Vertex AI
- [x] FastAPI skeleton: `GET /health` returns 200

---

## Phase 1: Schemas + Content Analyst

- [x] Define all Pydantic models in `backend/models/schemas.py`
  - InputDocument, UserContext, ContentAnalysis
  - PersonaFeedback, NarrativeFeedback, ClarityFeedback
  - RevisionPlan, FinalReport, PriorityIssue
- [x] Implement Content Analyst agent with structured JSON output
- [x] Smoke test: paste a weak talk outline → verify `ContentAnalysis` schema returned ✅
- [x] Validate Gemini 2.0 Flash quality for extraction tasks ✅

---

## Phase 2: Full Agent Pipeline (LangGraph)

- [x] Define `AgentState` in `backend/graph/pipeline.py`
- [x] Implement 4 Persona agents (parallel via asyncio.gather inside parallel_agents_node)
- [x] Implement Narrative Coach (Gemini 2.5 Pro)
- [x] Implement Clarity Coach (Gemini 2.0 Flash)
- [x] Implement Revision Planner (Gemini 2.5 Pro)
- [x] Implement Synthesizer with priority ranking (3+ agents = High, 2 = Medium, 1 = Low)
- [x] Wire full DAG: content_analyst → parallel_agents → revision_planner → synthesizer
- [x] End-to-end test: one document in → `FinalReport` out ✅
- [ ] **Validate actual token counts vs. ~22k input / ~5.5k output estimate from projectidea.md §21**

---

## Phase 3: API Endpoints ✅

- [x] `POST /analyze` — runs full pipeline, saves session, returns FinalReport
- [x] `GET /session/{id}` — retrieves stored session
- [x] `POST /revise` — re-runs pipeline using `session_id` reference
- [x] `POST /compare` — re-runs + diffs against prior session issues
- [x] Request validation: file size limit, doc_type enum, audience_type enum

---

## Phase 4: Session Persistence ✅

- [x] SQLAlchemy models for sessions + reports in `backend/storage/db.py`
- [x] SQLite DB init on app startup
- [x] Save FinalReport to DB on each `/analyze` call
- [x] Retrieve session by ID
- [x] Store revision chain (session → prior_session_id)

---

## Phase 5: Frontend (Next.js) ✅

- [x] Page 1: Landing page (`app/page.tsx`) — hero + 4 feature cards
- [x] Page 2: Input form (`app/analyze/page.tsx`) — text paste + file upload tabs, doc type / audience / goal selectors, domain + notes fields
- [x] Page 3: Analysis progress view — animated agent step list shown while pipeline runs (~60–90s)
- [x] Page 4: Results dashboard (`app/results/[sessionId]/page.tsx`)
  - executive summary banner
  - priority issues with High/Medium/Low color badges and quoted passages
  - 4 persona reaction cards (confusion, interest, questions)
  - narrative critique section (arc summary, strengths, weaknesses, ordering, suggestions)
  - clarity critique section (jargon, undefined terms, dense sections)
  - revision plan (top priorities, revised outline, cuts, moves, emphasis changes, revised opening)
- [x] Page 5 (stretch): Compare drafts view
- [x] Connect to FastAPI backend via `lib/api.ts` (300s timeout, proper error handling)
- [x] Shared types in `lib/types.ts` mirroring backend Pydantic schemas
- [x] Local frontend dev server verified on `http://127.0.0.1:3000`

---

## Phase 6: File Upload ✅

- [x] PDF parsing in `backend/utils/parsing.py` (pymupdf)
- [x] Accept `multipart/form-data` on `POST /analyze/upload`
- [x] Validate file type (PDF, TXT only for MVP)

---

## Phase 7: Deployment

- [x] Dockerfile for backend — multi-stage uv-based build; excludes .venv/node_modules via .dockerignore ✅ 2026-04-28
- [ ] Deploy frontend (Next.js → Vercel or Cloud Run)
- [ ] Deploy backend to Google Cloud Run
- [ ] Set Vertex AI / Google Cloud env vars as Cloud Run secrets or service env vars (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`, optional `STORYCOACH_AUDIO_BUCKET`)
- [ ] Verify live URL end-to-end

---

## Phase 9A: Venue Grounding ✅ 2026-04-28

- [x] Add `venue` field to `UserContext` schema (`neurips|icml|cvpr|nsf|nih_r01|job_talk|generic_academic|custom`)
- [x] Create `VenueContext` Pydantic model with `to_prompt_block()` method
- [x] Create `backend/venues/` directory with YAML files: `neurips.yaml`, `nsf.yaml`, `job_talk.yaml`, `generic_academic.yaml`
- [x] Create `backend/utils/venue_loader.py` — loads all YAMLs at startup, `get_venue_context(venue)` returns the block
- [x] Load venue YAML files at app startup (`load_venues()` called in FastAPI `startup` event); inject into every agent
- [x] Update `FinalReport` to include `venue`, `venue_fit_verdict` (`above_bar|at_bar|below_bar`), `venue_fit_confidence` (`high|medium|low`)
- [x] Update Synthesizer to produce venue-fit verdict; output schema now includes `venue_grounding` per issue
- [x] Fix priority ranking: `4+ agents = Critical`, `3 = High`, `2 = Medium`, `1 = Low`
- [x] Add `venue_grounding` field to `PriorityIssue` model (spec §11)
- [x] Add `venue` column to `SessionRecord` DB table — **note: delete `storycoach.db` locally to pick up new schema**

---

## Phase 9B: Q&A Predictor Agent ✅ 2026-04-28

- [x] Create `QAPredictionItem` and `QAPrediction` Pydantic models
- [x] Implement `backend/agents/qa_predictor.py` (Gemini 2.0 Flash; venue-aware question generation + answer-quality scoring)
- [x] Add `qa_predictor_node` to LangGraph parallel fan-out alongside personas, narrative, clarity
- [x] Pass `QAPrediction` to Revision Planner (weak-answer block) and Synthesizer (unhandled Q&A risks block)
- [x] Add `qa_predictions` field to `FinalReport`
- [x] Render Q&A section in frontend results dashboard (ranked list, yes/partial/no badges, response stubs)

---

## Phase 9C: Audio Pipeline + Delivery Coach (rehearsal mode)

- [x] Add `TranscriptSegment` Pydantic model (`start_seconds`, `end_seconds`, `text`, `wpm`, `filler_word_count`, `aligned_slide`)
- [x] Add `DeliveryMetrics` Pydantic model (`total_duration_seconds`, `average_wpm`, `wpm_variance`, `filler_word_total`, `pacing_dropouts`, `slide_speech_mismatches`)
- [x] Add `DeliveryFeedback` Pydantic model (`pacing_issues`, `filler_hotspots`, `slide_mismatch_flags`, `weak_opening_notes`, `weak_closing_notes`, `ranked_delivery_fixes`)
- [x] Integrate Google Cloud Speech-to-Text v2 for timestamped transcription
- [x] Implement pacing metrics: WPM per transcript segment, variance computation, dropout detection
- [x] Implement filler-word detection (um, uh, like, basically, sort of, you know)
- [x] Add pptx text extraction (`python-pptx`) for slide alignment
- [x] Implement slide alignment: keyword overlap between transcript chunks and slide text
- [x] Implement `backend/agents/delivery_coach.py` (Gemini 2.0 Flash; ingests `TranscriptSegment` list + `DeliveryMetrics`, flags pacing collapses, filler hotspots, slide-speech mismatch, weak open/close)
- [x] Add `POST /analyze-rehearsal` endpoint (multipart: audio file + optional slide deck, venue/audience/goal params)
- [x] Wire rehearsal-mode LangGraph DAG: transcribe → content_analyst → 8-agent parallel (personas + narrative + clarity + Q&A + delivery) → revision_planner → synthesizer
- [x] Add `delivery_section` field to `FinalReport` (null in draft mode)
- [x] Support Cloud Storage bucket for audio transcription via `STORYCOACH_AUDIO_BUCKET`
- [x] Render delivery section in frontend: timestamped issue list
- [x] Render delivery section in frontend: pacing chart and filler-word heatmap
- [x] Add rehearsal upload flow to the frontend form
- [ ] Validate Google Speech-to-Text timestamp granularity on a real rehearsal file

---

## Phase 9D: File Upload Extensions ✅ 2026-04-28

- [x] Add `.docx` parsing to `backend/utils/parsing.py` (`python-docx`)
- [x] Add `.pptx` text extraction (`python-pptx` — also used for slide alignment in 9C)
- [x] Update `/analyze/upload` endpoint to accept `.docx` and `.pptx`; raised file size limit to 10MB

---

## Phase 9E: Baseline Comparison Panel ✅ 2026-04-28

- [x] Add `POST /baseline/{session_id}` endpoint: runs a single Gemini 2.5 Pro prompt on the same input (Baseline A from spec §17.1) and returns the raw response
- [x] Lazy evaluation: only call `/baseline/{session_id}` when the user clicks "show comparison" in the UI — not on every analyze run
- [x] Render collapsible comparison panel in frontend results page

---

## Phase 10A: Academic Application Mode — Product Spec

- [x] Add SOP/application mode to project concept as MVP+ extension, not replacement for talks/grants/rehearsals
- [x] Add new doc types: `statement_of_purpose`, `personal_statement`, `research_statement`, `diversity_statement`, `faculty_email`, `fellowship_essay`
- [x] Add new venues/application targets: `graduate_sop`, `phd_application`, `masters_application`, `nsf_grfp`, `faculty_outreach`
- [x] Define application-specific report fields: `program_fit_verdict`, faculty matches, program-fit gaps, unsupported claims, authenticity risks
- [x] Add application-specific venue/context YAML blocks for SOPs, PhD applications, masters applications, NSF GRFP, and faculty outreach

---

## Phase 10B: Program Research Agent ✅ 2026-04-28

- [x] Accept school/program URL or school/program name from the user
- [x] Use Vertex/Gemini Google Search grounding for school/program-name lookup; use direct crawl when the user supplies an official URL
- [x] Search official department and faculty pages first; prefer `.edu`/official university domains
- [x] Extract professor name, title, lab/profile URL, research areas, and evidence snippets
- [x] Store source URL, source type, confidence, and retrieval timestamp for every faculty record
- [x] Mark unresolved or ambiguous programs as needing user confirmation instead of guessing

---

## Phase 10C: Faculty/Paper Fit Database ✅ 2026-04-28

- [x] Build a small per-run database from verified faculty pages, lab pages, research pages, and paper/project signals visible in those sources
- [x] Prefer official profiles and lab pages
- [ ] Add explicit Google Scholar/DBLP/arXiv supplemental lookup after official-source MVP is stable
- [x] Rank faculty by overlap with applicant interests and SOP content
- [x] Include confidence, source URLs, and "why this match" evidence for each faculty recommendation
- [x] Label weak/no-match cases honestly rather than inventing faculty fit

---

## Phase 10D: SOP/Application Critique Pipeline ✅ 2026-04-28

- [x] Reuse existing Content, Narrative, Clarity, Persona, Revision, and Synthesizer agents
- [x] Add `SOPFitCoach` for applicant-program fit, generic-fit detection, and future-direction critique
- [x] Add `AuthenticityCoach` for inflated claims, unsupported claims, prestige-chasing, and template-like writing
- [x] Add admissions-committee personas: committee reader, target PI, skeptical fit reviewer
- [x] Generate source-grounded rewrite suggestions tied to verified faculty/program evidence
- [x] Enforce boundary: no admissions probability predictions or guarantees

---

## Phase 10E: Frontend Application Flow ✅ 2026-04-28

- [x] Add "Application" mode to analyze page
- [x] Add target school/program fields, optional official URL, and applicant research interests field
- [x] Render program-fit verdict and faculty-fit table with source links and confidence
- [x] Render fit gaps, unsupported claims, authenticity risks, and SOP rewrite priorities
- [x] Add comparison baseline: single Gemini prompt for faculty suggestions + SOP feedback vs. source-grounded agent output

---

## Phase 10F: Vertex Search + Website Crawl Smoke Test ✅ 2026-05-01

- [x] Verified application mode with an official faculty URL: `https://www.cs.columbia.edu/people/faculty/`
- [x] Verified school/program-name-only flow using Vertex/Gemini Google Search grounding
- [x] Confirmed Custom Search keys are optional fallback, not required for the Google Cloud/Vertex path
- [x] Hardened crawler to try up to 5 official seed URLs so one stale/404 result does not fail the whole research pass
- [x] Normalized optional/null faculty fields from LLM output so missing lab/profile URLs do not crash the backend
- [x] Smoke-test result: name-only Columbia CS PhD target returned source-linked faculty matches and faculty records

---

## Phase 8: Polish

- [ ] Tune prompts on 5 test documents:
  - strong intro (baseline)
  - weak intro with buried contribution
  - jargon-heavy technical outline
  - unclear motivation
  - disorganized structure
- [ ] Run baseline comparison: single Gemini prompt vs. StoryCoach pipeline on same docs
- [ ] Run application-mode baseline: single prompt faculty suggestions vs. source-grounded agent research on real public departments
- [ ] Add 2–3 built-in demo example documents
- [ ] Write `README.md` (run instructions, live URL, class concepts with file references)
- [ ] Write `business_onepager.md`
- [ ] Final demo run

---

## Decisions Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-25 | Use LangGraph for orchestration | Graph-based parallel fan-out, built-in state management, fits multi-agent DAG cleanly |
| 2026-04-25 | Hybrid model routing: Flash for simple agents, 2.5 Pro for reasoning agents | Quality where it counts; keeps per-run cost ~$0.025 vs ~$0.055 for all-Pro |
| 2026-04-25 | Separate LLM call per persona agent | More distinct, more agentic; better demo; parallel calls avoid latency penalty |
| 2026-04-25 | SQLite for session storage | Simplest option for MVP; easy to swap to Postgres post-launch |
| 2026-04-25 | Text paste as primary input, PDF as secondary | PDF parsing is a rabbit hole; validate core pipeline first |
| 2026-04-25 | Use `vertex_ai/gemini-2.5-pro` and `vertex_ai/gemini-2.0-flash` model strings | `gemini-2.5-pro-preview-05-06` not available in project; plain `gemini-2.5-pro` works |
| 2026-04-25 | Use `json-repair` library + `_coerce_str_list` Pydantic validators | Vertex AI doesn't reliably return valid JSON — repair handles malformed output; coerce handles nested objects in list fields |
| 2026-04-25 | Frontend: Next.js 15 App Router + Tailwind, no component library | Keeps dependencies minimal; Tailwind covers all needed UI; avoids shadcn/radix version conflicts with React 19 |
| 2026-04-25 | Animate agent steps client-side during loading (~8s per step) | Pipeline is ~60–90s with no streaming; fake progress prevents blank spinner confusion |
| 2026-04-28 | Venue YAML files as static knowledge base loaded at startup | Keeps venue norms editable without code changes; injected into every agent's user message as a formatted block |
| 2026-04-28 | Q&A predictor runs in parallel fan-out with personas/narrative/clarity (not after) | Adding it to the parallel stage costs zero latency; its output is consumed by revision_planner and synthesizer downstream |
| 2026-04-28 | docx/pptx imports lazy inside functions, not at module level | Avoids import cost on every request; both are only needed in the upload path |
| 2026-04-28 | Dockerfile: uv copied from official image, `uv sync --frozen --no-dev` installs deps | Reproducible installs; image is ~250MB — well within Cloud Run limits |
| 2026-04-28 | Academic Application Mode is MVP+ / Phase 10, not core MVP | Strong adjacent vertical, but current demo remains talks/grants/rehearsals unless time allows |
| 2026-04-28 | Application fit claims must be source-grounded | Generic chatbots hallucinate faculty/program fit; every faculty recommendation needs URL evidence, confidence, and retrieval timestamp |

---

## Validate Early (before going too deep)

- [ ] Gemini 2.5 Pro quality for Narrative Coach — run on a real talk outline in Phase 1
- [ ] Actual token counts vs. estimate (measure with LiteLLM usage callbacks)
- [ ] LangGraph `Send` API parallel behavior with LiteLLM — check for rate-limit issues
- [ ] PDF parsing quality with pymupdf on a real academic paper
- [ ] Google Speech-to-Text word offset format — confirm real-audio timing quality before tuning delivery metrics
- [ ] Slide alignment accuracy on a real pptx with jargon-heavy slides — keyword overlap may need tuning
- [ ] Cloud Run audio upload size limit (default 32 MB request body — 20-min audio can exceed this; set `--max-instances` and adjust `--timeout` and request-size limits)
- [ ] Run baseline experiment (spec §17.1) on at least 3 real documents **before** building Phase 9E frontend — if multi-agent doesn't beat single-prompt, redesign first
- [ ] Application-mode factuality: verify faculty recommendations against official department pages for at least 3 public programs before building the full frontend flow
