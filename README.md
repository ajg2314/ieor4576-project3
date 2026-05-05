# StoryCoach

StoryCoach is an agent-based academic communication coach for research talks, papers, grant drafts, recorded rehearsals, and academic application materials. It is designed for high-stakes academic communication where the question is not just "is this well written?" but "will this work for this exact audience and venue?"

The app combines a FastAPI backend, a LangGraph multi-agent pipeline, Gemini/Vertex AI model routing, venue-specific YAML context, SQLite persistence, and a Next.js frontend.

## Submission Links

- GitHub: `git@github.com:AndyJayGu/ieor4576-project3.git`
- Live URL: `https://ieor4576-project3-558700534812.us-central1.run.app/`
- Business one-pager: [business_document.md](business_document.md)

## Current Status

- Frontend and backend are deployed.
- Google Cloud / Vertex AI configuration is working.
- The live URL has been verified end-to-end.
- Draft critique, file upload, venue grounding, Q&A prediction, baseline comparison, and application mode are working.
- Rehearsal mode is implemented, but real-file Google Speech-to-Text timestamp validation is still an acceptable unfinished item.
- Google Scholar/DBLP/arXiv supplemental lookup is intentionally deferred because official-source crawling is safer for the current deadline.

The business one-pager is maintained in [business_document.md](business_document.md). The build log and remaining work are tracked in [developmentlog.md](developmentlog.md).

## Core Features

- Draft critique for pasted text, PDF, TXT, DOCX, and PPTX uploads.
- Venue-aware feedback for academic contexts such as NeurIPS, NSF, job talks, and generic academic communication.
- Multi-agent review with content analysis, audience personas, narrative critique, clarity critique, Q&A prediction, revision planning, and synthesis.
- Ranked priority issues based on cross-agent agreement.
- Baseline comparison against a single Gemini prompt.
- Revision comparison across drafts.
- Rehearsal upload flow with transcription, pacing metrics, filler detection, slide alignment, and delivery critique.
- Academic application mode with target school/program research, source-linked faculty fit, unsupported-claim warnings, authenticity risks, and program-specific rewrite priorities.

## Architecture

```text
frontend/                 Next.js UI
backend/main.py           FastAPI routes
backend/graph/pipeline.py LangGraph orchestration
backend/agents/           Specialized critique agents
backend/models/schemas.py Pydantic request/report schemas
backend/storage/db.py     SQLite session persistence
backend/utils/            Parsing, audio, venue, research, JSON helpers
backend/venues/           YAML venue/application context
```

The main draft pipeline is:

```text
Content Analyst
  -> Persona Agents + Narrative Coach + Clarity Coach + Q&A Predictor
  -> Revision Planner
  -> Synthesizer
  -> FinalReport
```

Rehearsal mode adds transcription, delivery metrics, and Delivery Coach. Application mode adds program research and Application Coach before synthesis.

## Class Concepts Used

StoryCoach uses several agent and AI engineering concepts from class:

- **Agent framework / graph orchestration:** LangGraph defines the multi-step agent pipeline in [backend/graph/pipeline.py](backend/graph/pipeline.py). The graph runs content analysis first, fans out to multiple reviewers, then routes into revision planning and synthesis.
- **Multi-agent decomposition:** Specialized agents live in [backend/agents/](backend/agents/), including audience personas, narrative coach, clarity coach, Q&A predictor, delivery coach, application coach, revision planner, and synthesizer. This matches the business need to simulate several academic readers instead of one generic response.
- **Parallel agent execution:** Persona, narrative, clarity, Q&A, and delivery/application feedback are run in the parallel stage of the graph in [backend/graph/pipeline.py](backend/graph/pipeline.py), reducing latency while preserving independent reviewer perspectives.
- **Structured outputs:** Pydantic schemas in [backend/models/schemas.py](backend/models/schemas.py) define `ContentAnalysis`, `PersonaFeedback`, `RevisionPlan`, `ApplicationFitReport`, and `FinalReport`, making the agent output reliable enough for the frontend to render.
- **Retrieval / grounding:** Venue YAML files in [backend/venues/](backend/venues/) ground feedback in academic norms, while [backend/utils/program_research.py](backend/utils/program_research.py) uses Vertex/Gemini Google Search grounding and official-site crawling for application-mode faculty fit.
- **Tool use and external APIs:** [backend/utils/audio.py](backend/utils/audio.py) integrates Google Speech-to-Text for rehearsal critique, and [backend/utils/program_research.py](backend/utils/program_research.py) uses search/crawling tools for source-linked application advice.
- **Memory / persistence:** [backend/storage/db.py](backend/storage/db.py) stores sessions and revision chains in SQLite, enabling session retrieval, draft revision, and comparison.
- **Evaluation baseline:** [backend/main.py](backend/main.py) exposes `POST /baseline/{session_id}`, which runs a single-prompt Gemini baseline so users can compare generic LLM feedback against the StoryCoach agent pipeline.
- **Model routing for cost/quality tradeoffs:** The agents use faster Gemini Flash models for structured/simple tasks and Gemini Pro for reasoning-heavy narrative, revision, synthesis, and application-fit work; see [backend/agents/](backend/agents/) and the decisions in [developmentlog.md](developmentlog.md).

## API Routes

- `GET /health`
- `POST /analyze`
- `POST /analyze/upload`
- `POST /analyze-rehearsal`
- `POST /analyze-application`
- `GET /session/{session_id}`
- `POST /revise`
- `POST /compare`
- `POST /baseline/{session_id}`

## Environment

Create a `.env` file using [.env.example](.env.example):

```bash
GOOGLE_API_KEY=your_google_ai_api_key_here
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=true
STORYCOACH_SEARCH_MODEL=gemini-2.5-flash
STORYCOACH_AUDIO_BUCKET=your-gcs-bucket-for-rehearsal-audio
GOOGLE_SEARCH_API_KEY=optional_google_custom_search_api_key_fallback
GOOGLE_SEARCH_CX=optional_google_programmable_search_engine_id_fallback
DATABASE_URL=sqlite:///./storycoach.db
```

## Local Development

Install backend dependencies:

```bash
uv sync
```

Run the backend:

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the frontend:

```bash
npm run dev
```

The frontend proxies API calls through `frontend/app/api/[...path]/route.ts`. For local development, it defaults to `http://localhost:8000`.

## Combined Docker Build

`Dockerfile.combined` builds the Next.js frontend and runs it together with the FastAPI backend. The startup script is [scripts/start-combined.sh](scripts/start-combined.sh).

```bash
docker build -f Dockerfile.combined -t storycoach .
docker run --env-file .env -p 8080:8080 storycoach
```

## Project Notes

Important documentation:

- [projectidea.md](projectidea.md): full project specification and product rationale.
- [business_document.md](business_document.md): business one-pager, target users, economics, and technical choices.
- [developmentlog.md](developmentlog.md): build phases, completed work, deferred work, and validation checklist.

