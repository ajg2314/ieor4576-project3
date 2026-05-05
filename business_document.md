# StoryCoach Business Document

GitHub: `git@github.com:AndyJayGu/ieor4576-project3.git`
Live URL: https://ieor4576-project3-558700534812.us-central1.run.app/

## The Pitch

StoryCoach is the first-pass academic communication coach a graduate student can run before sending work to an advisor, committee member, paid writing tutor, or admissions consultant. It is the cheap, fast first check before the expensive human review — not a replacement for the advisor or the $300/hour consultant. A user runs it at midnight, gets feedback from multiple simulated academic readers, fixes the obvious weak spots, and saves scarce human time for the deeper questions.

It differs from a generic ChatGPT prompt in three specific ways: a multi-agent reader panel (persona, narrative, clarity, Q&A, delivery, synthesis) instead of one voice; source-grounded application research that recommends faculty only from cited `.edu` URLs; and rehearsal feedback from audio — pacing, filler words, slide-speech alignment — which text-only chatbots cannot do. The product also ships a single-Gemini baseline mode so a user can see, on their own draft, what the agent pipeline adds.

## The User

The first wedge is third- to fifth-year CS / ML / OR / CompBio PhD students with a NeurIPS, ICML, ACL, NSF GRFP, or faculty-interview deadline in the next 1–4 weeks. They have draft material, know it is not yet ready for an advisor, and want obvious problems fixed before that meeting. The second wedge is research-track graduate applicants — especially international and first-generation students — writing SOPs against a December–January cycle who need to name real faculty and defend fit on specific terms, and who cannot afford a $2,000 consultant package. Department-level licensing through writing centers, graduate schools, and research departments is the long-term expansion path.

## The Problem

Today's options each miss something. Advisors are scarce near deadlines. Peers share blind spots about venue norms. Generic chatbots routinely hallucinate faculty lists or place professors at the wrong universities. Grammar tools improve sentences but not argument or audience fit. Application consultants charge $500–$5,000+ with inconsistent quality and no way to evaluate them before paying. StoryCoach answers a specific question — "Will this exact draft work for this exact venue and audience?" — by running multiple agents that simulate different readers, grounding feedback in venue and program norms, predicting Q&A, comparing against a single-prompt baseline, and (in rehearsal mode) critiquing spoken delivery from audio.

## Competitive Landscape & Moat

**Generic LLMs (ChatGPT, Claude, Gemini chat)** offer broad writing advice but no venue norms, no multi-reader review, no source-grounded faculty research, no audio analysis. **General writing tools (Grammarly, ProWritingAid, $10–$15/mo)** optimize sentences, not argument. **Specialized academic AI (PaperPal-class)** is good on style and grammar, not multi-reader review or source-grounded fit. **Human consultants** can be excellent but cost $500–$5,000+ per package; StoryCoach sits below that layer as the affordable first check.

Defensibility, in increasing strength: (a) the multi-agent + venue YAML pattern is replicable but each new venue needs real review-pattern knowledge to author well; (b) the source-grounding pipeline that refuses to recommend faculty without an `.edu` URL is an architectural commitment, not a single API call; (c) accumulated revision and agent-disagreement data from paid runs compounds over time. None is unbreakable; together they are a head start.

## The Product

Three modes: **Draft critique** (paste or upload talk outline, abstract, paper intro, grant section, job talk, or application essay); **Rehearsal critique** (upload audio + optional slides; the system transcribes, measures pacing/fillers, aligns speech to slide order, and critiques delivery alongside the written content); **Application mode** (enter school/program/department; Vertex Gemini with Google Search grounding plus official-site crawling verifies faculty before grading SOP fit).

Output is a single ranked report: venue-fit verdict, top issues by cross-agent agreement, audience reactions, narrative critique, clarity issues, Q&A predictions, revision plan, and — for applications — verified faculty matches with source URLs and confidence.

## Economics

Pricing is freemium plus a $25/month "deadline crunch" plan. Free shows the venue-fit verdict and one example issue per run, gated by a use limit. Paid unlocks the full ranked report, faculty-fit evidence, revision plan, Q&A predictions, baseline comparison, saved sessions, draft comparison, and rehearsal critique, with fair-use caps of 50 draft/application and 5 rehearsal runs per month.

Why $25 — above generic AI writing tools at $10–$20 and the same magnitude as ChatGPT Plus at $20 — is the application user. A single application fee is ~$100, applicants commonly apply to 8–15 schools, and consultants run $500–$5,000+ per package. Against that backdrop, $25 for source-grounded SOP review is a rational experiment for price-sensitive applicants. A planned tier split, once usage data exists, is $14 "researcher" + $39 "application season" (3-month commit).

Token economics use Google Cloud current pricing: Gemini 2.0 Flash $0.15/$0.60 per 1M in/out; Gemini 2.5 Pro $1.25/$10; Search grounding free for 1,500 grounded prompts/day on Flash then $35/1k; Speech-to-Text v2 $0.016/min.

| User-month | Realistic | Heavy deadline |
|---|---:|---:|
| Draft runs | 8 × $0.05 = $0.40 | 25 × $0.05 = $1.25 |
| Application runs | 2 × $0.15 = $0.30 | 5 × $0.15 = $0.75 |
| Rehearsal runs | 1 × $0.21 = $0.21 | 5 × $0.21 = $1.05 |
| Infra allocation | $0.50 | $1.00 |
| **Total cost** | **~$1.41** | **~$4.05** |
| **Margin at $25** | **~94%** | **~84%** |

The model breaks if rehearsals get long, application research scales past the free grounding tier, or Pro output grows. Controls: fair-use caps, audio-length limits, token budgets, cached venue context, Flash routing. These exclude CAC. Department licensing: ~$100–$200/student/year for 30–200-student departments, landing $5K (small grad program) to $25K (large writing center). Distribution channels to test: PhD subreddits, NeurIPS/ICML/NSF Slack and Discord communities, writing-center partnerships, advisor word of mouth.

## Why These Technical Choices

- **Multi-agent LangGraph pipeline** — structured committee-style review is what justifies pricing above generic AI tools.
- **Editable venue YAML corpus** — new venues take hours, not weeks, and ship without a retrain. Expansion into adjacent venues without an ML team.
- **Hybrid Flash/Pro routing** — Flash for high-throughput structured agents, Pro for reasoning-heavy work. Holds margin above 80% even on heavy months.
- **Vertex Google Search grounding + `.edu` crawling** — application coach recommends only faculty backed by retrieved sources with URL attached. Enables an application-tier price without hallucination liability; a single public failure here would do more brand damage than a year of marketing could repair.
- **Google Speech-to-Text v2 for rehearsal** — pacing, fillers, and slide-speech mismatch require audio analysis text-only competitors cannot offer. Makes "ChatGPT can already do this" a weaker objection.
- **FastAPI + LangGraph + Pydantic + SQLite + Next.js + Cloud Run** — simple to deploy, easy to inspect, structured enough to keep multi-agent output reliable. Cloud Run's per-request billing matches bursty deadline-driven usage.

## Risks & Validation

Three things most likely to kill this: (1) a major LLM provider ships "academic mode" — defended by workflow specialization, the curated venue corpus, and PhD-community brand recognition; (2) free-to-paid conversion is too low to support CAC — measured in the first weeks of operation, not assumed; (3) a public hallucinated-faculty incident — architectural mitigations are in place but not infallible.

90-day proof-points: blind 3-PhD-reviewer eval comparing the multi-agent pipeline against the built-in single-prompt baseline on 30–50 real SOPs; 50 paid users from organic PhD-community channels with tracked free-to-paid conversion; one paid pilot with a university writing center.

Sources: Google Cloud Vertex AI pricing, https://cloud.google.com/vertex-ai/generative-ai/pricing; Google Cloud Speech-to-Text pricing, https://cloud.google.com/speech-to-text/pricing.
