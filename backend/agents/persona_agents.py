from backend.utils.json_parse import parse_llm_json
from backend.utils.throttle import acompletion_with_retry
from backend.models.schemas import PersonaFeedback, InputDocument, UserContext, ContentAnalysis, VenueContext

PERSONAS = {
    "smart_novice": {
        "name": "Smart Novice",
        "description": "Curious and intelligent but has no domain expertise. Gets confused by jargon and needs motivation stated early.",
        "system": """You are a smart, curious person with no domain expertise reading this document.
You get confused by jargon and unexplained notation. You need the motivation to be clear in the first paragraph.
If you don't understand why this matters in the first 20%, you disengage.""",
    },
    "grad_student_in_field": {
        "name": "Grad Student in Field",
        "description": "Knows the domain well. Will spot missing rigor, unsupported claims, and gaps in related work.",
        "system": """You are a graduate student who knows this field well.
You will spot vague contributions, missing citations, and unsupported claims.
You expect technical precision and will notice if the contribution is undersold or oversold.""",
    },
    "skeptical_expert": {
        "name": "Skeptical Expert",
        "description": "Hard to impress. Pushes back on vague contributions, weak comparisons, and overclaiming.",
        "system": """You are a senior expert who is hard to impress.
You push back on vague contributions, weak comparisons to prior work, and anything that overclaims.
You want to know exactly what is new and why it matters.""",
    },
    "impatient_listener": {
        "name": "Impatient Listener",
        "description": "Has 5 minutes. If the main point isn't clear in the first 20%, mentally checks out.",
        "system": """You are a busy person who has 5 minutes to give this document.
If the main point is not clear in the opening, you mentally check out.
You want to know: what is this, why should I care, and what do I take away — all within the first section.""",
    },
}

APPLICATION_PERSONAS = {
    "committee_reader": {
        "name": "Admissions Committee Reader",
        "description": "Evaluates whether the applicant shows preparation, fit, maturity, and a credible trajectory.",
        "system": """You are a graduate admissions committee reader.
You look for evidence of preparation, research maturity, fit with the program, and a coherent intellectual trajectory.
You are skeptical of generic fit paragraphs and claims not backed by concrete experience.""",
    },
    "target_pi": {
        "name": "Potential Faculty Advisor",
        "description": "Checks whether the applicant understands the research area and can plausibly contribute to a lab.",
        "system": """You are a potential faculty advisor reading this application.
You care whether the applicant understands your area, has relevant preparation, and asks research questions that could plausibly fit a lab.
You notice if faculty fit is name-dropping rather than substantive.""",
    },
    "skeptical_fit_reviewer": {
        "name": "Skeptical Fit Reviewer",
        "description": "Pushes back on vague motivation, prestige-chasing, and unsupported faculty/program claims.",
        "system": """You are a skeptical reviewer focused on program fit.
You push back on vague motivation, prestige-chasing, unsupported faculty claims, and anything that sounds reusable across schools.""",
    },
    "authenticity_reader": {
        "name": "Authenticity Reader",
        "description": "Looks for specific, grounded self-presentation rather than inflated or template-like writing.",
        "system": """You are an authenticity-focused admissions reader.
You look for concrete evidence, reflection, and specificity. You flag inflated claims, generic passion statements, and CV-list paragraphs.""",
    },
}

APPLICATION_VENUES = {
    "graduate_sop",
    "phd_application",
    "masters_application",
    "nsf_grfp",
    "faculty_outreach",
}


def _venue_value(context: UserContext) -> str:
    return context.venue.value if hasattr(context.venue, "value") else str(context.venue)

OUTPUT_SCHEMA = """Output schema:
{
  "persona_name": "name of this persona",
  "persona_description": "one-line description of this persona",
  "overall_reaction": "one paragraph describing this persona's overall reaction",
  "confusion_points": ["specific passages or moments where this persona gets confused"],
  "interest_points": ["specific passages or moments that engage this persona"],
  "questions_remaining": ["questions this persona still has after reading"]
}"""


async def run_persona_agent(
    persona_key: str,
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    venue_context: VenueContext | None = None,
) -> PersonaFeedback:
    personas = APPLICATION_PERSONAS if _venue_value(context) in APPLICATION_VENUES else PERSONAS
    persona = personas[persona_key]
    venue_block = venue_context.to_prompt_block() if venue_context else ""

    system = f"""{persona["system"]}

Rules:
- Quote specific passages from the document when identifying confusion or interest points
- Return only valid JSON matching the schema below
- Every observation must reference specific content, not generic advice

{OUTPUT_SCHEMA}"""

    user_message = f"""Document type: {document.doc_type}
Target audience: {context.audience_type}
Goal: {context.goal_type}
{f"VENUE CONTEXT:{chr(10)}{venue_block}{chr(10)}" if venue_block else ""}
Content analyst summary:
- Main claim: {content_analysis.main_claim}
- Technical density: {content_analysis.technical_density}
- Motivation quality: {content_analysis.motivation_quality}

--- DOCUMENT ---
{document.raw_text}
--- END DOCUMENT ---

React to this document as {persona["name"]} and return JSON."""

    response = await acompletion_with_retry(
        model="vertex_ai/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = parse_llm_json(raw)
    data["persona_name"] = persona["name"]
    data["persona_description"] = persona["description"]
    return PersonaFeedback(**data)


async def run_all_personas(
    document: InputDocument,
    context: UserContext,
    content_analysis: ContentAnalysis,
    venue_context: VenueContext | None = None,
) -> list[PersonaFeedback]:
    import asyncio
    personas = APPLICATION_PERSONAS if _venue_value(context) in APPLICATION_VENUES else PERSONAS
    tasks = [
        run_persona_agent(key, document, context, content_analysis, venue_context)
        for key in personas
    ]
    return list(await asyncio.gather(*tasks))
