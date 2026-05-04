from langgraph.graph import StateGraph, END
from graph.state import GraphState
from agents.interview_prep import build_interview_prep_agent


def interview_prep_node(state: GraphState) -> dict:
    try:
        agent = build_interview_prep_agent(state["num_questions"])
        result = agent(state["resume_text"], state["job_description"])
        return {"questions": result.questions, "status": "completed"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("interview_prep", interview_prep_node)
    graph.set_entry_point("interview_prep")
    graph.add_edge("interview_prep", END)
    return graph.compile()
