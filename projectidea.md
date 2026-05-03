# StoryCoach

StoryCoach is an agent-based communication coach for **academic researchers preparing high-stakes talks, grant proposals, and academic applications**. It diagnoses story, structure, clarity, and audience fit in two current modes: critique a written draft, and **critique a recorded rehearsal of the actual talk**. As an MVP+ extension, it adds an **Academic Application Mode** for statements of purpose, research statements, fellowship essays, and faculty outreach emails.

The wedge is vertical, not horizontal. We don't compete with ChatGPT for "any kind of writing feedback." We compete for one specific job: **getting a researcher's NeurIPS/ICML/CVPR talk, R01/NSF grant, or job-talk over the bar**, where audience-aware critique against domain norms is the difference between accept and reject.

StoryCoach answers higher-level questions a generic LLM doesn't:

- What is my main message? Is it where the audience expects it for *this* venue?
- Where in my talk will a NeurIPS reviewer / NSF panelist / hiring committee disengage?
- Where will a non-expert audience member get lost?
- What questions am I going to get in Q&A, and which ones do I have a weak answer to?
- For my recorded rehearsal: where did pacing collapse? Where did filler words dominate? Where did the slide and the spoken word diverge?
- For a graduate application: which professors at this school actually match my research direction, and can the system verify that from official sources?
- Does my SOP demonstrate real program fit, or does it sound generic enough to send anywhere?
- What are the top 3 fixes that move this draft over the bar?

---

## 1. Project Goal

The goal of this project is to build a deployed agent application that gives **venue-specific, audience-aware** feedback on academic communication, in both **written** and **recorded-rehearsal** modes, with an MVP+ path into source-grounded graduate application advising.

The product should help researchers improve:

- conference talks (NeurIPS, ICML, CVPR, KDD, ACL, etc.)
- grant proposals (NSF, NIH R01, NSF CAREER, ERC)
- job talks (faculty, industry research)
- paper abstracts and introductions
- defense talks (PhD proposal, thesis defense)
- statements of purpose, research statements, personal statements, fellowship essays, and faculty outreach emails

Two product verticals:
1. **Research dissemination mode** — talks, grants, papers, defenses, and rehearsals
2. **Academic application mode (MVP+)** — SOPs, research statements, personal statements, fellowship essays, and faculty outreach emails

The core value is not sentence polishing. The core value is **diagnosing whether the communication works as a story for a specific venue's audience and norms**, plus **critiquing the actual delivery** when the user records a rehearsal — something a generic LLM textbox cannot do.

Two delivery modes:
1. **Draft mode** — user pastes text or uploads slides; agents simulate audience reactions and propose fixes
2. **Rehearsal mode** — user records themselves giving the talk (5–20 min audio); we transcribe, align to slides if provided, and critique both *content as delivered* and *delivery itself* (pacing, filler words, mismatch with slides)

Academic Application Mode adds a third workflow rather than replacing the first two: the user provides a draft SOP/research statement and a target program, then StoryCoach researches the program, verifies faculty fit from public sources, and critiques whether the applicant's story is specific, credible, and aligned.

---

## 2. Problem Statement

For academic researchers, communication is high-stakes and venue-specific. A NeurIPS reviewer, an NSF panelist, and a faculty hiring committee read a piece of writing very differently. The same talk that excites a domain expert can lose a hiring committee in 90 seconds.

Common failure modes:

- motivation appears too late for the venue's expected pacing
- the contribution is buried under method detail
- notation or jargon appears before the audience is ready
- the abstract doesn't answer the questions a reviewer scores on
- the talk's spoken delivery doesn't match the slides
- pacing collapses in the middle, killing engagement
- the speaker hasn't anticipated the obvious Q&A questions

Today, researchers rely on:

- self-editing
- their advisor (who is a senior expert and may have lost the novice's perspective)
- peers in the same lab (overlapping blind spots)
- generic ChatGPT/Claude feedback (no venue norms, no audience model, no rehearsal critique)
- grammar tools (wrong layer)

### Why a generic LLM is not enough

A single ChatGPT prompt asking "critique this talk for a NeurIPS audience" returns vague, even-handed suggestions. It does not:

- model **multiple distinct audience personas in parallel** and surface where they disagree
- ground critique in **venue-specific norms** (e.g., "NeurIPS reviewers expect the contribution stated in the first 90 seconds")
- **rank issues by cross-agent agreement** — an issue flagged by 4 of 6 agents is much more actionable than one flagged by one
- **ingest a rehearsal recording** and critique delivery — generic LLMs are text-only
- generate **predicted Q&A questions** the speaker should prepare for, with answer-quality scoring
- **track issues across drafts** with a memory of what was previously raised
- reliably perform **source-grounded program research** for graduate applications — generic chatbots often hallucinate faculty, list professors who are not at the university, or misclassify a professor's research area

StoryCoach's differentiator isn't the model — it's the **specialized agent pipeline + venue grounding + rehearsal mode + cross-agent ranking**. We commit to proving this in a side-by-side baseline (Section 17) — if the multi-agent system doesn't beat single-prompt empirically, we redesign.

For Academic Application Mode, the differentiator becomes **agentic, source-linked fit research**. StoryCoach uses Vertex/Gemini Google Search grounding for school/program-name lookup, then crawls official program pages, faculty profiles, lab pages, and research pages to build a small per-run fit database. If the user supplies an official URL, StoryCoach can skip search and crawl that source directly. Custom Search keys are only a fallback path. Every faculty/program fit claim should carry source links and confidence instead of invented facts.

---

## 3. Target Users

### 3.1 Primary wedge: PhD students and postdocs preparing a high-stakes academic talk or grant proposal

Concrete user profile:
- PhD year 3–5 in CS / EE / ML / stats / quantitative bio / OR
- has 1–4 weeks until a hard deadline (conference talk, grant submission, job talk, qualifying exam)
- already has a draft or slides
- gets feedback from advisor, but wants more iterations than the advisor's calendar allows
- already pays for ChatGPT Plus and Grammarly — sees the gap in *venue-specific* feedback

Example users:
- ML PhD students preparing 12-minute NeurIPS / ICML talks (high deadline pressure, ~12,000 papers/year, very specific reviewer norms)
- early-career faculty submitting NSF CAREER or R01 proposals
- PhD candidates preparing 60-minute job talks

### 3.2 Secondary buyer: department-level licensing

After the wedge:
- university communication / writing centers
- department-level faculty development offices
- pitch coaching firms (YC's pre-Demo Day equivalents for academia: Insight Fellows, Rhodes, etc.)

This is the path to enterprise contracts ($10–50k/yr per institution) once the wedge is proven.

### 3.3 Why this wedge

- **Real WTP.** A failed grant is a year lost. A bad job talk is a job lost. The deadline-driven academic willingly pays $20–50/month during the deadline crunch.
- **Defensible vertical.** Venue norms (NeurIPS reviewer guidelines, NSF merit/broader-impact criteria, hiring committee scoring rubrics) are public but require curation. ChatGPT can answer "what does NeurIPS look for?" generically; it can't run that as part of a specialized agent pipeline that grounds every critique in those norms.
- **Reproducible test set.** Public accepted vs. rejected NeurIPS abstracts and NIH-funded vs. not-funded specific aims pages exist. We can build evals.

### 3.4 Example user questions

- "Will a NeurIPS reviewer score this abstract above the bar?"
- "Where in my 12-minute talk will an audience member check out?"
- "What 5 questions am I most likely to get in Q&A, and which ones is my answer weakest on?"
- "I just rehearsed my job talk on video — where did the delivery break?"
- "Compared with last week's draft, what improved and what's still broken?"
- "Which professors at this school actually match my research direction?"
- "Does my SOP demonstrate fit with this program, or does it sound generic?"
- "Which faculty or papers should I reference, and are they real/current?"
- "Where does my application overclaim, underspecify, or fail to connect my past work to future research?"

---

## 4. Core Product Idea

StoryCoach takes either a written draft *or* a recorded rehearsal, plus venue context (NeurIPS / NSF / job talk / etc.), then runs multiple specialized agents to produce a structured, ranked report.

The report includes:
- venue-specific main diagnosis ("would this clear the bar at this venue?")
- multiple audience persona reactions, surfaced separately
- story / structure critique with concrete passage citations
- clarity critique with concrete jargon flags
- **predicted Q&A questions and your weakest answers** (talks)
- delivery critique (rehearsal mode only): pacing, filler words, slide-speech mismatch
- top 3 priority fixes
- revised outline or opening
- cross-draft improvement memory ("last time you had X — it's resolved / it's worse")

The system is meant to behave like **a focus group of 4 distinct audience members + a venue-savvy reviewer + a delivery coach + a critique synthesizer**, all running in parallel and ranked by agreement.

In Academic Application Mode, StoryCoach behaves like **a program researcher + faculty-fit verifier + admissions committee reader + SOP coach**. It does not estimate admissions probability. It diagnoses whether the writing makes a source-grounded case for fit, maturity, specificity, and research direction.

---

## 5. MVP Scope

### In Scope
- text paste input
- file upload (PDF, .docx, .pptx text extraction)
- **venue selection** — NeurIPS / ICML / NSF / NIH-R01 / job-talk / generic
- audience selection (within venue, e.g., "domain expert reviewer" vs. "general program committee")
- goal selection
- multi-agent analysis (Content Analyst + 4 Persona Agents + Narrative + Clarity + Q&A Predictor + Synthesizer)
- venue-grounded critique (each agent prompt includes the venue's known scoring criteria / reviewer norms)
- **rehearsal mode (audio in)** — accept a 5–20 min recording, transcribe, align to slide outline if uploaded, run all agents on transcript + add Delivery Coach
- prioritized revision suggestions
- predicted Q&A list with answer-weakness flags
- final structured feedback report
- **draft comparison** — re-run on new draft, surface resolved vs. worsened vs. new issues
- **baseline comparison surfaced in the UI** (StoryCoach output vs. single-prompt LLM output, so the user can see the difference)

### MVP+ / Phase 10 Scope: Academic Application Mode
- SOP / research-statement / personal-statement / fellowship-essay input
- target school/program field, accepting either a school/program name or official URL
- optional applicant research interests
- agentic program research over public pages: Vertex/Gemini Google Search grounding for name-only targets, direct crawl for supplied official URLs, and official department/faculty/lab/research pages as primary sources
- verified faculty-fit table with source URLs, evidence snippets, confidence, and retrieval timestamp
- program-fit verdict (`strong_fit|plausible_fit|weak_fit`)
- fit gaps, unsupported claims, authenticity risks, and program-specific rewrite priorities

### Out of Scope
- real-time live audience monitoring during a delivered talk
- slide generation / direct PowerPoint editing
- grammar-only writing assistant
- collaborative editing
- full design/layout critique
- citation management
- admissions probability prediction or guarantees
- fabricating faculty, publications, rankings, or program facts without sources
- scraping non-public/private application systems

---

## 6. User Workflow

### 6.1 Draft mode
1. User pastes text or uploads file (PDF / docx / pptx)
2. User selects **venue** (NeurIPS, ICML, CVPR, NSF, NIH-R01, job-talk, generic-academic, custom)
3. User selects document type (talk outline, slide deck, abstract, intro, full paper section, grant specific aims, …)
4. User selects audience emphasis within venue (e.g., "skeptical reviewer" vs. "broad program committee")
5. User adds optional notes ("I'm worried section 2 is too dense")
6. StoryCoach runs multi-agent analysis (parallel fan-out)
7. User receives structured feedback report with:
   - venue-fit verdict
   - top 3 priority fixes
   - persona reactions
   - predicted Q&A + weakest answers
   - revised outline / opening (optional)
8. User revises and resubmits → comparison report shows resolved/worsened/new

### 6.2 Rehearsal mode (NEW)
1. User uploads a 5–20 minute recording of themselves rehearsing the talk (mp4 / m4a / wav)
2. Optional: user uploads slide deck so transcript can be aligned to slides
3. System transcribes with Google Cloud Speech-to-Text timestamps
4. Standard agents run on transcript content
5. **Delivery Coach** additionally critiques:
   - pacing (speaking rate variance, dead time, rushed sections)
   - filler words ("um," "like," "basically") frequency and density per slide
   - slide-speech mismatch (does the spoken content map to what's on the slide?)
   - opening hook and closing landing (the two highest-impact moments)
6. Report includes timestamped delivery flags ("0:42–1:10 — pacing dropped, motivation got lost")

### 6.3 Academic application mode (MVP+)
1. User pastes or uploads an SOP, research statement, personal statement, fellowship essay, or faculty outreach email
2. User enters a target school/program name or official program URL, plus optional research interests
3. `ProgramResearchAgent` uses Vertex/Gemini Google Search grounding to find official department/program pages when no URL is supplied, or crawls the supplied official URL directly
4. `FacultyVerifierAgent` verifies current faculty, titles, official URLs, and research areas
5. `PaperFitAgent` reads selected faculty pages, lab pages, research pages, and paper/project signals when available to build a small source-grounded fit database
6. SOP/application agents critique narrative, fit, specificity, authenticity, committee risk, and unsupported claims
7. Final report recommends strongest-fit faculty, weak-fit or unverified claims, missing evidence, and program-specific rewrite priorities

---

## 7. Key Features

### 7.1 Content Upload / Input
Users can:
- paste text directly
- upload text-based documents
- choose content type

### 7.2 Audience Selection
Users specify who the content is for, so feedback can be tailored.

### 7.3 Story Diagnosis
The system identifies:
- main message
- central contribution
- narrative arc
- missing motivation
- buried payoff
- weak transitions
- poor ordering

### 7.4 Audience Simulation
Multiple audience personas react to the content, for example:
- smart novice
- target-domain grad student
- skeptical expert
- impatient listener

### 7.5 Clarity Feedback
The system flags:
- jargon overload
- undefined terms
- abrupt notation
- confusing paragraphs
- overly dense sections

### 7.6 Revision Planner
The system provides:
- top 3 priority fixes
- what to cut
- what to move earlier/later
- what to emphasize more
- revised outline or opening paragraph

### 7.7 Iterative Revision Loop
Users can compare drafts and see whether major issues improved.

### 7.8 Q&A Prediction (NEW)
A dedicated Q&A Predictor agent generates the 5 most likely audience questions for the venue, then evaluates the user's draft for whether it pre-emptively answers each. The user gets:
- ranked list of likely questions
- for each: "your draft addresses this / partially / not at all"
- suggested 1–2 sentence response if weak

### 7.9 Rehearsal Delivery Critique (NEW)
For audio uploads, the Delivery Coach agent flags:
- pacing variance (words per minute over time)
- filler-word hotspots
- timing vs. the venue's expected length (e.g., NeurIPS 12 minutes)
- mismatch between what the slide says and what the speaker says
- weak opening (first 30 seconds) and weak closing (last 30 seconds)

### 7.10 Venue-Specific Grounding (NEW)
Every agent receives a venue context block with:
- the venue's expected pacing and structure
- known reviewer / committee scoring criteria
- common rejection reasons for that venue
- examples of accepted vs. rejected openings

This is the core differentiator from generic LLM critique.

### 7.11 Source-Grounded Program Fit Research (MVP+)
For graduate applications, StoryCoach researches the target program before giving fit advice. It should:
- prefer official university department pages, faculty profiles, and lab pages
- use paper/project metadata and abstracts only as supplemental evidence when they are visible from official or source-linked pages
- extract professor name, title, lab/profile URL, research areas, and evidence snippets
- rank faculty by overlap with the applicant's interests and SOP content
- mark every faculty/program claim with source URL, confidence, and retrieval timestamp
- label unsupported or unverified claims instead of presenting them as facts

---

## 8. System Architecture

The app consists of the following major parts:

### Frontend
Responsible for:
- user input
- audience/goal selection
- report display
- revision loop UX

### Backend API
Responsible for:
- request handling
- file ingestion
- orchestration of agent pipeline
- returning structured report data

### Parsing / Preprocessing Layer
Responsible for:
- normalizing raw text
- extracting text from PDF / docx / pptx
- chunking long content
- extracting sections
- preparing content for analysis

### Audio Pipeline Layer (NEW — for rehearsal mode)
Responsible for:
- transcribing audio with Google Cloud Speech-to-Text (word-level timestamps)
- aligning transcript to uploaded slide outline if present
- computing pacing and filler-word metrics
- emitting a transcript + delivery-metrics object that downstream agents consume

### Venue Knowledge Base (NEW)
Responsible for:
- storing per-venue context blocks (NeurIPS, ICML, NSF, NIH, job-talk, etc.)
- each block: expected pacing, scoring criteria, common rejection reasons, accepted/rejected reference examples
- injected into every agent's system prompt for that venue

### Program Research Layer (MVP+ — for academic applications)
Responsible for:
- resolving a target school/program name or URL into official public pages
- crawling a small bounded set of department, faculty, and lab pages
- extracting faculty records and research themes with source evidence
- reading selected papers/pages for fit signals
- caching a per-run, timestamped faculty-fit database that downstream SOP agents consume

### Agent Orchestration Layer (LangGraph)
Responsible for:
- running specialized agents in a defined graph
- merging outputs into shared state
- controlling flow and dependencies
- short-circuiting when a venue-fail-fast condition is detected (e.g., abstract has no clear contribution → skip Q&A predictor, surface only that)

Execution DAG (draft mode):
```
Input + UserContext + VenueContext
        ↓
[content_analyst_node]          ← must run first; outputs ContentAnalysis
        ↓
[persona_1] [persona_2] [persona_3] [persona_4]
[narrative_coach] [clarity_coach] [qa_predictor]   ← parallel fan-out via LangGraph Send API
        ↓
[revision_planner_node]         ← depends on all 7 outputs above
        ↓
[synthesizer_node]              ← ranks by cross-agent agreement, produces final structured report
```

Execution DAG (rehearsal mode):
```
Audio + (optional) Slides + UserContext + VenueContext
        ↓
[speech_to_text_transcribe + slide_align]    ← outputs Transcript + DeliveryMetrics
        ↓
[content_analyst_node]                ← runs on transcript text
        ↓
[persona_1..4] [narrative] [clarity] [qa_predictor] [delivery_coach]   ← 8 agents parallel
        ↓
[revision_planner_node]
        ↓
[synthesizer_node]
```

Running 7–8 agents in parallel instead of sequentially is the difference between a 90-second result and a 12-second result. UX matters here — users iterate.

Execution DAG (academic application mode, MVP+):
```
SOP + Target Program + Applicant Interests
        ↓
[program_research_agent] → [faculty_verifier_agent] → [paper_fit_agent]
        ↓
[content_analyst_node]
        ↓
[admissions_personas] [narrative] [clarity] [sop_fit_coach] [authenticity_coach]
        ↓
[revision_planner_node]
        ↓
[application_synthesizer_node]  ← source-grounded fit report
```

### Report Synthesis Layer
Responsible for:
- deduplicating feedback
- prioritizing issues
- generating final structured output

### Session Storage
Responsible for:
- saving user runs
- revision history
- draft comparison

---

## 9. Agent Design

StoryCoach uses multiple agents with distinct responsibilities.

### 9.1 Content Analyst Agent
Purpose:
- understand what the content is trying to say

Functions:
- extract main claim
- identify contributions
- detect structure
- estimate technical density
- infer assumptions about audience knowledge

Output:
- content summary
- structure map
- main message
- candidate narrative arc

---

### 9.2 Audience Persona Agents
Purpose:
- simulate likely audience reactions

Possible personas:
- smart novice
- target-domain grad student
- skeptical expert
- impatient audience member

Functions:
- identify confusion points
- identify interest drop points
- identify missing explanation
- respond from persona perspective

Output:
- persona reaction summaries
- questions each persona still has
- likely confusion areas

---

### 9.3 Narrative Coach Agent
Purpose:
- evaluate story and structure

Functions:
- judge whether the motivation is strong enough
- detect buried contributions
- detect weak transitions
- detect poor ordering
- detect over-detailed early sections
- suggest a better flow

Output:
- narrative strengths
- narrative weaknesses
- ordering suggestions
- better framing ideas

---

### 9.4 Clarity Coach Agent
Purpose:
- evaluate how understandable the content is

Functions:
- detect jargon overload
- detect undefined terminology
- detect confusing steps
- flag dense sections
- suggest simpler framing

Output:
- top clarity issues
- flagged confusing sections
- suggested simplifications

---

### 9.5 Revision Planner Agent
Purpose:
- convert critique into action

Functions:
- prioritize issues
- produce top 3 fixes
- suggest what to cut
- suggest what to move
- generate revised outline
- generate revised opening

Output:
- prioritized action plan
- revised structure
- optional rewrite suggestions

---

### 9.6 Q&A Predictor Agent (NEW)
Purpose:
- predict the top 5 likely Q&A questions for the venue, score the draft's preparedness for each

Functions:
- generate venue-aware Q&A questions (NeurIPS reviewers ask about ablations and baselines; NSF panelists ask about broader impacts and feasibility)
- score, for each question, whether the draft addresses it (yes / partial / no)
- suggest a 1–2 sentence response stub for weak ones

Output:
- ranked Q&A list with answer-quality flag per question
- response stubs for weak answers

---

### 9.7 Delivery Coach Agent (NEW — rehearsal mode only)
Purpose:
- critique how the talk was actually delivered

Inputs:
- transcript with word-level timestamps
- delivery metrics (WPM-over-time, filler-word counts)
- optional slide alignment

Functions:
- flag pacing collapses (sustained drop in WPM or sustained rapid catch-up)
- flag filler-word hotspots
- flag slide-speech mismatch (when speaker drifts off the slide topic)
- flag weak openings (first 30s) and weak closings (last 30s)
- suggest specific delivery fixes ("the motivation slide is on screen for 90 seconds but only 20 seconds is spent on it")

Output:
- list of timestamped delivery issues
- ranked delivery fixes

---

### 9.8 Synthesizer Agent
Purpose:
- combine all agent outputs into one clean report

Input:
- ContentAnalysis + all PersonaFeedback + NarrativeFeedback + ClarityFeedback + QAPrediction + (optional DeliveryFeedback) + RevisionPlan + VenueContext

Functions:
- deduplicate overlapping issues across agents (e.g., "jargon in section 2" flagged by both Clarity Coach and Persona 3)
- rank issues by frequency across agents + severity label
- ground top-issue framing in venue norms ("for NeurIPS specifically, this would cost a point on the contribution-clarity score")
- select top 5 highest-impact issues overall
- produce a single-paragraph executive summary
- organize remaining issues into labeled sections
- produce a venue-fit verdict (above bar / at bar / below bar with confidence)

Ranking logic:
- Issues flagged by 4+ agents → Critical priority
- Issues flagged by 3 agents → High priority
- Issues flagged by 2 agents → Medium priority
- Issues flagged by 1 agent → Low priority (still shown, but below the fold)

Output:
- final structured report (see FinalReport model in Section 11)
- venue-fit verdict
- if comparison-mode: resolved/worsened/new diff vs. prior run

---

### 9.9 ProgramResearchAgent (MVP+ — academic applications)
Purpose:
- find official, current public sources for a target graduate program

Functions:
- accept a school/program name or official URL
- identify official department/program/faculty pages
- avoid relying on unsourced generic search snippets
- return candidate pages with source type, URL, and retrieval timestamp

Output:
- bounded source list for the target program
- official program URL candidates
- confidence that the program identity was resolved correctly

---

### 9.10 FacultyVerifierAgent (MVP+ — academic applications)
Purpose:
- verify that faculty mentioned or recommended by the system are real, current, and relevant to the target program

Functions:
- extract professor name, title, lab/profile URL, and research areas
- cross-check official department/faculty pages before marking someone verified
- exclude or mark unverified faculty not found on official sources
- record evidence snippets and retrieval timestamp

Output:
- verified faculty records with source URLs
- unverified or weakly verified candidates with warnings

---

### 9.11 PaperFitAgent (MVP+ — academic applications)
Purpose:
- connect applicant interests and SOP claims to faculty research using source-grounded paper/profile evidence

Functions:
- read selected faculty/lab/research pages and paper/project metadata or abstracts when available
- extract research themes, methods, domains, and recent project signals
- rank overlap with applicant interests and SOP content
- explain why each match is strong, partial, or weak

Output:
- small per-run faculty-fit database
- ranked faculty matches with confidence and evidence

---

### 9.12 SOPFitCoach (MVP+ — academic applications)
Purpose:
- evaluate whether the SOP/research statement makes a credible case for program fit

Functions:
- judge whether past work, future interests, and target faculty connect logically
- flag generic school paragraphs that could be sent anywhere
- flag missing evidence for research maturity or future direction
- suggest program-specific rewrite priorities grounded in verified faculty/program sources

Output:
- `program_fit_verdict`: strong_fit / plausible_fit / weak_fit
- fit gaps
- strongest faculty/program fit claims
- program-specific rewrite suggestions

---

### 9.13 AuthenticityCoach (MVP+ — academic applications)
Purpose:
- flag SOP writing that sounds inflated, template-like, unsupported, or strategically vague

Functions:
- identify claims not backed by concrete experience
- flag prestige-chasing language that does not explain intellectual fit
- identify overclaiming, generic passion statements, and CV-list paragraphs
- suggest more specific, evidence-backed framing

Output:
- authenticity risks
- unsupported claims
- concrete rewrite guidance

---

## 10. Functional Requirements

### Input Layer
- accept raw text input
- accept basic file uploads
- validate file type / size
- identify document type
- extract clean text
- segment text into sections

### User Context Layer
- capture audience type
- capture communication goal
- capture optional user concerns
- attach metadata to analysis request
- for application mode: capture target school/program, optional program URL, and applicant research interests

### Analysis Layer
- extract main argument/story
- critique structure
- critique clarity
- simulate audience response
- prioritize feedback
- for application mode: verify faculty/program fit from public sources before making recommendations

### Output Layer
- generate structured JSON report
- display readable report
- support revision suggestions
- support iterative re-analysis
- for application mode: display faculty-fit evidence, source URLs, confidence, and unverified-claim warnings

### Storage Layer
- save session results
- save previous drafts
- support draft comparison

---

## 11. Data Models

### InputDocument
```json
{
  "id": "",
  "title": "",
  "raw_text": "",
  "sections": [],
  "doc_type": "",
  "source_type": ""
}
```

### UserContext
```json
{
  "venue": "neurips|icml|cvpr|nsf|nih_r01|job_talk|generic_academic|custom",
  "audience_type": "",
  "goal_type": "",
  "domain": "",
  "user_notes": ""
}
```

Academic Application Mode extends venue/document options:
```json
{
  "doc_type": "statement_of_purpose|personal_statement|research_statement|diversity_statement|faculty_email|fellowship_essay",
  "venue": "graduate_sop|phd_application|masters_application|nsf_grfp|faculty_outreach"
}
```

### ApplicationTarget (MVP+)
```json
{
  "school_name": "",
  "program_name": "",
  "program_url": "",
  "research_interests": []
}
```

### FacultyRecord (MVP+)
```json
{
  "name": "",
  "title": "",
  "profile_url": "",
  "lab_url": "",
  "research_areas": [],
  "evidence_snippets": [],
  "retrieved_at": "",
  "verification_status": "verified|partial|unverified"
}
```

### FacultyFitMatch (MVP+)
```json
{
  "faculty_name": "",
  "fit_score": 0,
  "confidence": "high|medium|low",
  "why_match": "",
  "source_urls": [],
  "relevant_papers_or_projects": []
}
```

### ApplicationFitReport (MVP+)
```json
{
  "program_fit_verdict": "strong_fit|plausible_fit|weak_fit",
  "verified_faculty_matches": [],
  "fit_gaps": [],
  "unsupported_claims": [],
  "authenticity_risks": [],
  "program_specific_rewrite_points": []
}
```

### VenueContext (NEW — loaded from knowledge base, not user input)
```json
{
  "venue": "",
  "expected_length_minutes": 0,
  "scoring_criteria": [],
  "common_rejection_reasons": [],
  "expected_pacing_notes": "",
  "reference_accepted_examples": [],
  "reference_rejected_examples": []
}
```

### TranscriptSegment (NEW — rehearsal mode)
```json
{
  "start_seconds": 0.0,
  "end_seconds": 0.0,
  "text": "",
  "wpm": 0.0,
  "filler_word_count": 0,
  "aligned_slide": null
}
```

### DeliveryMetrics (NEW — rehearsal mode)
```json
{
  "total_duration_seconds": 0,
  "average_wpm": 0,
  "wpm_variance": 0,
  "filler_word_total": 0,
  "filler_word_density_per_minute": 0,
  "pacing_dropouts": [],
  "slide_speech_mismatches": []
}
```

### QAPrediction (NEW)
```json
{
  "questions": [
    {
      "question": "",
      "likelihood": "high|medium|low",
      "draft_handles": "yes|partial|no",
      "suggested_response_stub": ""
    }
  ]
}
```

### DeliveryFeedback (NEW)
```json
{
  "pacing_issues": [],
  "filler_hotspots": [],
  "slide_mismatch_flags": [],
  "weak_opening_notes": "",
  "weak_closing_notes": "",
  "ranked_delivery_fixes": []
}
```

### ContentAnalysis
```json
{
  "main_claim": "",
  "contributions": [],
  "structure_map": [],
  "technical_density": "",
  "motivation_quality": ""
}
```

### PersonaFeedback
```json
{
  "persona_name": "",
  "persona_description": "",
  "overall_reaction": "",
  "confusion_points": [],
  "interest_points": [],
  "questions_remaining": []
}
```

### NarrativeFeedback
```json
{
  "arc_summary": "",
  "strengths": [],
  "weaknesses": [],
  "ordering_issues": [],
  "revision_suggestions": []
}
```

### ClarityFeedback
```json
{
  "jargon_issues": [],
  "undefined_terms": [],
  "dense_sections": [],
  "clarification_suggestions": []
}
```

### RevisionPlan
```json
{
  "top_priorities": [],
  "cuts": [],
  "moves": [],
  "emphasis_changes": [],
  "revised_outline": [],
  "revised_opening": ""
}
```

### FinalReport
```json
{
  "session_id": "",
  "venue": "",
  "venue_fit_verdict": "above_bar|at_bar|below_bar",
  "venue_fit_confidence": "high|medium|low",
  "executive_summary": "",
  "top_issues": [
    {
      "issue": "",
      "priority": "critical|high|medium|low",
      "agents_flagging": [],
      "quoted_passage": "",
      "venue_grounding": "",
      "suggested_fix": ""
    }
  ],
  "audience_reactions": [],
  "narrative_section": {},
  "clarity_section": {},
  "qa_predictions": {},
  "delivery_section": null,
  "revision_plan": {},
  "comparison_to_previous": null
}
```

---

## 12. Frontend Plan

### Page 1: Landing Page
Purpose:
- introduce product
- explain use cases
- guide user into analysis flow

### Page 2: Upload / Input Page
Features:
- paste text
- upload file (PDF, .docx, .pptx)
- **upload audio rehearsal** (mp4, m4a, wav) — switches to rehearsal mode
- choose content type
- **choose venue** (NeurIPS, ICML, CVPR, NSF, NIH-R01, job-talk, generic) — drives venue grounding
- choose audience emphasis
- choose goal
- optional notes

### Page 3: Analysis View
Features:
- loading/progress state
- show which stages are running
  - parsing
  - content analysis
  - audience simulation
  - synthesis

### Page 4: Results Dashboard
Sections:
- **venue-fit verdict** at the top (above bar / at bar / below bar)
- top 3 priority fixes
- audience persona reactions (4 cards, distinct viewpoints)
- story critique
- clarity critique
- **predicted Q&A list** with answer-quality flags
- **delivery section** (rehearsal mode only): timeline of timestamped issues, pacing chart, filler-word heatmap
- suggested revised opening / outline
- **side-by-side baseline comparison** (collapsed by default, one click to expand) — same input through a single Gemini prompt vs. StoryCoach's pipeline, so the user can see the difference

### Page 5: Compare Drafts (Optional / MVP+)
Features:
- compare previous and current version
- what improved
- what still needs work

---

## 13. API Plan

### `POST /analyze`
Input:
- document text / uploaded file reference
- venue
- audience
- goal
- doc type
- optional notes

Output:
- full analysis report

### `POST /analyze-rehearsal` (NEW)
Input:
- audio file (mp4 / m4a / wav)
- optional slide deck reference
- venue
- audience
- goal
- optional notes

Output:
- transcript with word-level timestamps
- delivery metrics
- full analysis report including DeliveryFeedback section

### `POST /revise`
Input:
- session_id (references prior report from storage)
- current draft text
- optional focus area

Output:
- updated feedback + revised suggestions
- list of issues from previous run that were resolved

### `GET /session/{id}`
Output:
- stored session results

### `POST /compare`
Input:
- session_id (references old run)
- new draft text

Behavior:
- Re-runs full agent pipeline on new draft
- Synthesizer receives both old FinalReport and new agent outputs
- Synthesizer explicitly flags which prior issues are resolved, worsened, or unchanged

Output:
- new full report
- improvement summary (resolved / unchanged / new issues)

---

## 14. Implementation Milestones

### Milestone 1: Core Input + Analysis Backend
Deliverables:
- text input endpoint
- user context schema
- content analyzer
- structured JSON output

### Milestone 2: Multi-Agent Pipeline
Deliverables:
- audience persona agents
- narrative coach
- clarity coach
- synthesis layer

### Milestone 3: Revision Planning
Deliverables:
- prioritization logic
- top fixes
- revised outline
- revised opening

### Milestone 4: Frontend
Deliverables:
- input form
- results dashboard
- persona cards
- structured report rendering

### Milestone 5: Persistence + Compare Drafts
Deliverables:
- save sessions
- compare runs
- show improvement summary

### Milestone 6: Polish + Deployment
Deliverables:
- prompt tuning
- error handling
- sample demo examples
- public deployment
- final README
- one-pager

---

## 15. Suggested Build Order

### Phase 1
- define schemas
- build text input flow
- implement content analyzer
- implement one narrative analysis function

### Phase 2
- add audience persona feedback
- add clarity coach
- add report synthesis

### Phase 3
- add revision planner
- add revised outline generation
- add revised opening generation

### Phase 4
- build frontend dashboard
- format results cleanly
- add save/load session support

### Phase 5
- compare draft feature
- polish prompts
- polish demo flow
- deploy

---

## 16. Prompt Engineering

Each agent prompt must enforce three things:
1. **Cite the text** — feedback must quote specific passages, not describe them abstractly
2. **Return structured JSON** — no prose paragraphs; use the defined output schema
3. **Be audience-aware** — every observation must be relative to the specified audience

### Prompt Structure (all agents)
```
System: You are a [role]. You are analyzing a [doc_type] for an audience of [audience_type] 
        whose goal is to [goal_type]. The author's domain is [domain].
        
        Rules:
        - Always quote specific passages when identifying issues (use exact text from the document)
        - Return only valid JSON matching the schema below
        - Never give generic advice — every observation must reference specific content
        - If you cannot find a specific example, say so; do not fabricate

User: [document text]
      [output schema]
```

### Agent-specific system prompt notes

**Content Analyst:** "Extract the main claim in one sentence. If you cannot find a clear main claim, say so explicitly."

**Persona Agents:** Each persona gets a distinct system prompt personality:
- *Smart novice:* "You are curious but have no domain expertise. You get confused by jargon and need motivation to be stated early."
- *Target-domain grad student:* "You know the field but will spot missing rigor or unsupported claims."
- *Skeptical expert:* "You are hard to impress. You push back on vague contributions and weak comparisons."
- *Impatient listener:* "You have 5 minutes. If the main point isn't clear in the first 20%, you mentally check out."

**Narrative Coach:** "Treat the document as a story with setup, conflict, and resolution. Identify which of these is missing or weak."

**Synthesizer:** "You will receive feedback from multiple reviewers. Your job is to deduplicate and rank. An issue flagged by multiple reviewers is more important than one flagged by one. Always surface the top 5 issues first."

---

## 17. Evaluation Plan

**The baseline comparison is the load-bearing experiment for this project.** If multi-agent does not measurably beat single-prompt on our test set, the architecture has no defense. We run this in week 1, not at the end.

### 17.1 Baseline Comparison (PRIORITY 1 — run in week 1)

Test set: 8 academic documents
- 2 NeurIPS abstracts: 1 known-accepted, 1 known-rejected (use OpenReview public data)
- 2 NSF / NIH specific aims: 1 funded, 1 not-funded (use public-record samples)
- 2 talk outlines: 1 polished, 1 messy
- 2 paper introductions: 1 strong narrative, 1 weak

For each document, run:
- **Baseline A:** single Gemini 2.5 Pro prompt — "Give detailed feedback on this [doc_type] for a [venue] audience. Identify problems and suggest fixes."
- **Baseline B:** single Gemini 2.5 Pro prompt with venue context block injected (same context StoryCoach uses)
- **StoryCoach:** full multi-agent pipeline with venue grounding

Score each output on 5 axes (1–5 each), blind to source, by 2 independent graders:
1. **Specificity** — does it quote actual passages and reference them concretely?
2. **Actionability** — can the user execute the suggestions in 30 minutes?
3. **Audience sensitivity** — does feedback change meaningfully when venue changes?
4. **Non-redundancy** — does it surface distinct issues without repeating?
5. **Venue accuracy** — does it correctly identify whether the document is above/below the venue bar?

**Pass criterion:** StoryCoach beats Baseline A by ≥1.0 average on (3) and (5), and ties or beats on the rest. Beats Baseline B by ≥0.5 average on (4) — this is the cross-agent ranking value.

If we fail criterion: redesign before continuing — most likely fix is sharper venue grounding or stronger Q&A predictor differentiation.

This experiment goes on the demo slide. "Don't take our word, here's the head-to-head."

### 17.2 Functional Evaluation
Test:
- upload success (text, PDF, docx, pptx)
- audio upload + transcription success (mp4, m4a, wav)
- JSON schema validity
- report generation success
- frontend rendering success
- comparison-mode resolves/unresolves correctly

### 17.3 Quality Evaluation
Test with the 8-document test set above plus:
- strong vs. weak intros
- 3 rehearsal recordings of varying delivery quality (one polished, one rushed, one full-of-fillers)

Measure:
- agent agreement (do agents flag overlapping issues? — too much agreement = redundancy; too little = inconsistency)
- venue verdict accuracy (against known accept/reject data)
- delivery flag precision/recall (against human-annotated delivery issues)

### 17.4 Human Evaluation
Recruit 5 PhD students, each with a real upcoming talk or grant. Have them use StoryCoach for one revision cycle. Survey:
- Did the system identify real story problems?
- Did persona reactions feel distinct, or interchangeable?
- Did predicted Q&A feel like real questions they would get?
- Did delivery feedback (rehearsal mode) match what their advisor said?
- Would you pay $20/month during a deadline crunch?

---

## 18. Risks and Mitigations

### Risk: Feedback is too generic
Mitigation:
- use structured outputs
- require audience-specific comments
- enforce concrete examples in prompts

### Risk: Too much duplicate feedback
Mitigation:
- synthesize and deduplicate before final report

### Risk: Parsing files is messy
Mitigation:
- make pasted text the primary workflow first
- add file upload support after backend is stable

### Risk: Project scope becomes too large
Mitigation:
- prioritize story/structure critique only
- avoid slide generation, grammar, and voice analysis for MVP

### Risk: Feels like “just ChatGPT”
Mitigation:
- venue-specific grounding is the single biggest differentiator — no generic LLM has it pre-loaded
- rehearsal mode is text-LLM-impossible: ChatGPT cannot ingest audio + slide alignment
- side-by-side baseline comparison surfaced in the UI — let the user *see* the difference
- predicted Q&A with answer-quality scoring is a distinct user job ChatGPT doesn't do
- cross-agent ranking (issues flagged by 4+ agents → critical) gives a prioritization signal a single prompt cannot

### Risk: Baseline beats us empirically
Mitigation:
- run the baseline experiment in week 1, before building the rest
- if baseline ties or wins, redesign immediately — sharper venue grounding, stronger persona differentiation, or pivot harder into rehearsal-only mode (which generic LLMs cannot do at all)

### Risk: Audio pipeline is fragile
Mitigation:
- only support common formats (mp4, m4a, wav)
- cap input length at 20 minutes for MVP
- show the user the transcript before running agents, so they can fix obvious errors

---

## 19. Tech Stack

- **Backend:** FastAPI
- **Frontend:** Next.js (React)
- **LLM Client:** LiteLLM for the main agent pipeline, plus Google Gen AI SDK for Vertex/Gemini Google Search grounding
- **LLM Models:** Hybrid routing by agent complexity:
  - Gemini 2.0 Flash — Content Analyst, Persona Agents, Clarity Coach, Q&A Predictor, Delivery Coach (structured/templated tasks)
  - Gemini 2.5 Pro — Narrative Coach, Revision Planner, Synthesizer (reasoning-heavy tasks)
  - Gemini 2.5 Flash — program-search query grounding (`STORYCOACH_SEARCH_MODEL`, configurable)
- **Agent Orchestration:** LangGraph (graph-based pipeline, parallel fan-out via `Send` API)
- **Audio (rehearsal mode):**
  - **Transcription:** Google Cloud Speech-to-Text v2 for word-level timestamps
  - **Slide alignment:** simple keyword-overlap heuristic between transcript chunks and slide text (sufficient for MVP; embedding-based matching as upgrade path)
- **Parsing:**
  - text / PDF: pymupdf
  - docx: python-docx
  - pptx: python-pptx
- **Venue Knowledge Base:** YAML files per venue, loaded at startup; injected into agent prompts
- **Package Manager:** uv
- **Storage:** SQLite + SQLAlchemy for sessions; object store (Cloud Storage) for uploaded audio
- **Deployment:** Google Cloud Run (backend) + Vercel (frontend)
- **Structured outputs:** Pydantic models + LiteLLM JSON mode

---

## 20. Class Concepts to Highlight

This project demonstrates:
- **Multi-agent orchestration with parallel fan-out** — 7 (draft) or 8 (rehearsal) agents via LangGraph `Send` API; ~6× wall-time speedup vs. sequential
- **Hybrid model routing** — Flash for structured/templated tasks, Pro for reasoning; ties tech choice directly to per-run cost
- **Cross-agent ranking and synthesis** — issues weighted by how many agents independently flagged them; this is the formal mechanism for "why multi-agent beats single prompt"
- **Tool integration** — Google Cloud Speech-to-Text for transcription, file parsers for PDF/docx/pptx, slide alignment heuristic
- **Agentic web research** — Vertex/Gemini Google Search grounding plus bounded official-site crawl for application-mode faculty/program verification
- **Structured outputs** — Pydantic schemas enforced at every agent boundary
- **Retrieval-style grounding** — venue knowledge base injected into every prompt for that venue
- **Memory across sessions** — comparison mode tracks issues across drafts, surfaces resolved/worsened/new
- **Evaluation methodology** — formal baseline comparison (single-prompt vs. multi-agent) with blinded scoring
- **Deployment**

---

## 21. Token Economics

### Per-run cost — draft mode

| Agent | Model | Input tokens | Output tokens |
|-------|-------|-------------|---------------|
| Content Analyst | Flash | ~2,000 | ~500 |
| Persona Agent × 4 | Flash | ~8,000 | ~2,000 |
| Clarity Coach | Flash | ~2,000 | ~600 |
| Q&A Predictor | Flash | ~2,500 | ~800 |
| Narrative Coach | 2.5 Pro | ~2,000 | ~600 |
| Revision Planner | 2.5 Pro | ~3,000 | ~800 |
| Synthesizer | 2.5 Pro | ~5,500 | ~1,200 |
| **Total** | | **~25,000** | **~6,500** |

Cost: Flash ~$0.003 + Pro ~$0.027 = **~$0.03 per draft run**

### Per-run cost — rehearsal mode (10-min audio)

Add to draft costs:
- Speech-to-Text transcription: Google Cloud Speech-to-Text v2 billed against GCP credits
- Delivery Coach (Flash): ~3,000 in / ~800 out = ~$0.001
- Synthesizer input grows by ~1,500 tokens (DeliveryFeedback): adds ~$0.003

**Total per rehearsal run: ~$0.10**

### Unit economics — Pro tier ($25/month, deadline-crunch positioning)

We deliberately price higher than ChatGPT Plus ($20) and Grammarly Premium ($12). The pitch isn't "cheaper feedback"; it's "venue-specific feedback you can't get anywhere else, during the weeks that decide your career."

Realistic usage from PhD-student interviews (replacing the original optimistic 50/month):

| User type | Runs/month | Mix (draft/rehearsal) |
|---|---|---|
| Active deadline crunch (4 weeks/yr × 2 deadlines) | 30 | 70% / 30% |
| Steady user | 8 | 90% / 10% |
| Light user | 2 | 100% / 0% |

Mid-case (steady user, 8 runs/mo, 90/10 split):

| Metric | Value |
|--------|-------|
| Price | $25/user/month |
| Token cost | ~$0.30 |
| Speech-to-Text cost | covered by GCP credit during course demo |
| Infrastructure | ~$0.50 |
| Total cost to serve | ~$0.85/user/month |
| Gross margin | ~97% |

Heavy-deadline-crunch month (30 runs):

| Metric | Value |
|--------|-------|
| Token cost | ~$1.20 |
| Speech-to-Text cost | covered by GCP credit during course demo |
| Infrastructure | ~$0.50 |
| Total | ~$2.20 |
| Margin at $25 | ~91% |

### Economics break only if:
- a single user exceeds ~250 runs/month (caps via fair-use prevent this)
- rehearsal share goes to >70% of runs and recordings average 20+ min — even then, 70% margin

### Department / institutional license

- $5,000–$25,000/yr per institution for unlimited use across faculty/grad students
- ~5–10 institutional pilots = $50–250k ARR — the goal of the wedge

These are pre-build estimates; we lock numbers after the week-1 baseline experiment confirms quality.

---

## 22. MVP Definition

The MVP must do the following well:

- accept a talk outline, abstract, intro, or paper section
- accept a 5–20 minute rehearsal recording (mp4 / m4a / wav)
- let the user specify **venue** (NeurIPS, ICML, NSF, NIH-R01, job-talk, generic) plus audience and goal
- run multiple critique agents in parallel via LangGraph
- ground every agent's critique in the venue's known scoring criteria
- generate 4 distinct audience persona reactions
- generate predicted Q&A list with answer-quality flags
- (rehearsal) generate Delivery Coach feedback with timestamped pacing/filler/mismatch flags
- output a venue-fit verdict (above/at/below bar) with confidence
- output top 3 priority fixes ranked by cross-agent agreement
- suggest a revised outline or improved opening
- support draft comparison (resolved/worsened/new)
- **expose side-by-side baseline output (single-prompt vs. StoryCoach) in the UI** — the experiment that proves the architecture

The class demo: one PhD-student volunteer, real talk abstract, 90-second result, then live audio rehearsal upload, 30-second delivery critique with timestamps. End on the side-by-side panel.

---

## 23. Product Positioning

StoryCoach is **not**:
- a grammar checker (Grammarly does that)
- a generic AI writing assistant (ChatGPT does that, with no venue specificity)
- a slide generator
- a speaking-speed tracker

StoryCoach **is**:
- a **venue-specific** communication coach for academic researchers
- the only tool that critiques both the **written draft and the recorded rehearsal** in one workflow
- a multi-agent pipeline whose advantage over single-prompt LLMs is empirically demonstrated, not asserted

One-line product definition:

> StoryCoach is a venue-aware multi-agent coach that helps researchers get their NeurIPS talks, NSF proposals, and job talks over the bar — by critiquing both the draft and the recorded rehearsal against the venue's scoring criteria, simulating audience reactions, predicting Q&A, and ranking fixes by cross-agent agreement.

---

## 24. Business Case Summary (one-pager source)

### The user
Concrete: a 4th-year ML PhD student with 3 weeks until their NeurIPS oral. They've already drafted slides, gotten one round of advisor feedback, and want 5 more iterations than the advisor will give them. They pay for ChatGPT Plus already and find it directionally useful but venue-blind.

Or: an early-career PI two weeks from an NSF CAREER deadline, with one shot per year.

### The problem
- Generic LLMs give venue-blind feedback that misses the specific bar these venues set
- Advisors are bandwidth-limited; peer feedback has overlapping blind spots
- No tool today critiques a recorded rehearsal — but the rehearsal is where the talk actually breaks
- Q&A surprises kill talks; nobody systematically generates the questions in advance

### Why now
- Cloud Speech-to-Text transcription is accurate enough for rehearsal critique and keeps the stack on Google Cloud
- Public OpenReview / OpenAlex data lets us build a real eval set of accepted vs. rejected examples
- LangGraph parallel fan-out makes 7-agent pipelines respond in 12s — fast enough for tight iteration loops

### The product
A multi-agent coach with venue grounding, draft + rehearsal modes, predicted Q&A, and cross-draft memory. The architecture's value is demonstrated in-product via a side-by-side baseline panel.

### How we make money
- **B2C Pro tier:** $25/user/month (positioned for deadline crunches, not casual use)
- **Department licensing:** $5–25k/yr per institution for unlimited use
- **Cost to serve:** ~$0.85/user/month at typical usage; ~$2.20 at heavy use → ~91–97% gross margin
- **Path to revenue:** ML PhD students at top-25 CS departments → ~6,000 target users for the wedge venue (NeurIPS); 1% conversion at $25/mo = ~$18k MRR from one venue alone

### Why these technical choices
- **Multi-agent + cross-agent ranking:** the synthesizer ranks issues by how many agents independently flagged them. This is the formal mechanism that beats a single prompt — a single prompt cannot vote with itself.
- **Venue knowledge base injected per agent:** every critique is grounded in the specific venue's norms — generic LLMs cannot do this without per-venue prompt engineering, which is exactly what we encapsulate.
- **Speech-to-Text + Delivery Coach:** rehearsal critique is text-LLM-impossible. This is our hardest-to-copy feature and the wow moment for the demo.
- **Hybrid Flash + Pro routing:** Flash handles structured high-throughput agents (4 personas + clarity + Q&A); Pro handles the synthesizer where reasoning quality is decisive. This is what makes ~95% margin defensible at $25/month.
- **Baseline panel in-UI:** users can see the difference between StoryCoach and a generic LLM call. The architecture is empirically defended every time the user opens the report.

### What's defensible
- Curated venue knowledge base (NeurIPS reviewer guidelines, NSF merit criteria, common rejection patterns) — the asset compounds as we add venues
- Rehearsal mode — a multi-modal feature that text-only LLMs cannot replicate
- Eval methodology + test set built from accepted/rejected public examples — this is a moat against "ChatGPT will add this"
