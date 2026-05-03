import asyncio
import uuid
from typing import TypedDict

from langgraph.graph import StateGraph, END

from backend.models.schemas import (
    InputDocument, UserContext, ContentAnalysis,
    PersonaFeedback, NarrativeFeedback, ClarityFeedback,
    RevisionPlan, FinalReport, QAPrediction, VenueContext,
    TranscriptSegment, DeliveryMetrics, DeliveryFeedback,
    ApplicationTarget, ApplicationFitReport,
)
from backend.agents.content_analyst import run_content_analyst
from backend.agents.persona_agents import run_all_personas
from backend.agents.narrative_coach import run_narrative_coach
from backend.agents.clarity_coach import run_clarity_coach
from backend.agents.qa_predictor import run_qa_predictor
from backend.agents.delivery_coach import run_delivery_coach
from backend.agents.application_coach import run_application_coach
from backend.agents.revision_planner import run_revision_planner
from backend.agents.synthesizer import run_synthesizer
from backend.utils.program_research import research_program_sources
from backend.utils.venue_loader import get_venue_context


class AgentState(TypedDict):
    session_id: str
    document: InputDocument
    context: UserContext
    venue_context: VenueContext | None
    content_analysis: ContentAnalysis | None
    personas: list[PersonaFeedback]
    narrative: NarrativeFeedback | None
    clarity: ClarityFeedback | None
    qa_prediction: QAPrediction | None
    transcript_segments: list[TranscriptSegment]
    delivery_metrics: DeliveryMetrics | None
    delivery_feedback: DeliveryFeedback | None
    application_target: ApplicationTarget | None
    application_fit: ApplicationFitReport | None
    revision_plan: RevisionPlan | None
    final_report: FinalReport | None


async def content_analyst_node(state: AgentState) -> dict:
    result = await run_content_analyst(
        state["document"], state["context"], state["venue_context"]
    )
    return {"content_analysis": result}


async def parallel_agents_node(state: AgentState) -> dict:
    vc = state["venue_context"]
    personas_task = run_all_personas(
        state["document"], state["context"], state["content_analysis"], vc
    )
    narrative_task = run_narrative_coach(
        state["document"], state["context"], state["content_analysis"], vc
    )
    clarity_task = run_clarity_coach(
        state["document"], state["context"], state["content_analysis"], vc
    )
    qa_task = run_qa_predictor(
        state["document"], state["context"], state["content_analysis"], vc
    )
    delivery_task = (
        run_delivery_coach(
            state["transcript_segments"],
            state["delivery_metrics"],
            state["context"],
            vc,
        )
        if state["transcript_segments"] and state["delivery_metrics"]
        else None
    )
    tasks = [personas_task, narrative_task, clarity_task, qa_task]
    if delivery_task:
        tasks.append(delivery_task)
    results = await asyncio.gather(*tasks)
    personas, narrative, clarity, qa_prediction = results[:4]
    delivery_feedback = results[4] if delivery_task else None
    return {
        "personas": personas,
        "narrative": narrative,
        "clarity": clarity,
        "qa_prediction": qa_prediction,
        "delivery_feedback": delivery_feedback,
    }


async def revision_planner_node(state: AgentState) -> dict:
    result = await run_revision_planner(
        state["document"],
        state["context"],
        state["content_analysis"],
        state["narrative"],
        state["clarity"],
        state["personas"],
        state["qa_prediction"],
        state["venue_context"],
        state["delivery_feedback"],
        state["delivery_metrics"],
        state["transcript_segments"],
        state["application_fit"],
    )
    return {"revision_plan": result}


async def synthesizer_node(state: AgentState) -> dict:
    result = await run_synthesizer(
        state["session_id"],
        state["document"],
        state["context"],
        state["content_analysis"],
        state["personas"],
        state["narrative"],
        state["clarity"],
        state["revision_plan"],
        state["qa_prediction"],
        state["venue_context"],
        state["delivery_feedback"],
        state["delivery_metrics"],
        state["transcript_segments"],
        state["application_fit"],
    )
    return {"final_report": result}


def build_pipeline() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("content_analyst", content_analyst_node)
    graph.add_node("parallel_agents", parallel_agents_node)
    graph.add_node("revision_planner", revision_planner_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("content_analyst")
    graph.add_edge("content_analyst", "parallel_agents")
    graph.add_edge("parallel_agents", "revision_planner")
    graph.add_edge("revision_planner", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


pipeline = build_pipeline()


async def run_pipeline(document: InputDocument, context: UserContext) -> FinalReport:
    session_id = str(uuid.uuid4())
    venue_context = get_venue_context(context.venue)

    initial_state: AgentState = {
        "session_id": session_id,
        "document": document,
        "context": context,
        "venue_context": venue_context,
        "content_analysis": None,
        "personas": [],
        "narrative": None,
        "clarity": None,
        "qa_prediction": None,
        "transcript_segments": [],
        "delivery_metrics": None,
        "delivery_feedback": None,
        "application_target": None,
        "application_fit": None,
        "revision_plan": None,
        "final_report": None,
    }
    result = await pipeline.ainvoke(initial_state)
    return result["final_report"]


async def run_rehearsal_pipeline(
    document: InputDocument,
    context: UserContext,
    transcript_segments: list[TranscriptSegment],
    delivery_metrics: DeliveryMetrics,
) -> FinalReport:
    session_id = str(uuid.uuid4())
    venue_context = get_venue_context(context.venue)

    initial_state: AgentState = {
        "session_id": session_id,
        "document": document,
        "context": context,
        "venue_context": venue_context,
        "content_analysis": None,
        "personas": [],
        "narrative": None,
        "clarity": None,
        "qa_prediction": None,
        "transcript_segments": transcript_segments,
        "delivery_metrics": delivery_metrics,
        "delivery_feedback": None,
        "application_target": None,
        "application_fit": None,
        "revision_plan": None,
        "final_report": None,
    }
    result = await pipeline.ainvoke(initial_state)
    return result["final_report"]


async def run_application_pipeline(
    document: InputDocument,
    context: UserContext,
    target: ApplicationTarget,
) -> FinalReport:
    session_id = str(uuid.uuid4())
    venue_context = get_venue_context(context.venue)
    sources = await research_program_sources(target)
    application_fit = await run_application_coach(
        document, context, target, sources, venue_context
    )

    initial_state: AgentState = {
        "session_id": session_id,
        "document": document,
        "context": context,
        "venue_context": venue_context,
        "content_analysis": None,
        "personas": [],
        "narrative": None,
        "clarity": None,
        "qa_prediction": None,
        "transcript_segments": [],
        "delivery_metrics": None,
        "delivery_feedback": None,
        "application_target": target,
        "application_fit": application_fit,
        "revision_plan": None,
        "final_report": None,
    }
    result = await pipeline.ainvoke(initial_state)
    return result["final_report"]
