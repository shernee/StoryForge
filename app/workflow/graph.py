from langgraph.graph import StateGraph, END
from app.workflow.state import StoryState
from app.workflow.nodes.extract_memory import extract_memory
from app.workflow.nodes.load_characters import load_characters
from app.workflow.nodes.plan_story import plan_story
from app.workflow.nodes.generate_text import generate_text
from app.workflow.nodes.evaluate_text import evaluate_text
from app.workflow.nodes.regenerate_text import regenerate_text
from app.workflow.nodes.generate_illustration_prompts import generate_illustration_prompts
from app.workflow.nodes.generate_illustrations import create_illustrations


def _route_after_evaluation(state: StoryState) -> str:
    eval_results = state.get("evaluation_results") or []
    if not eval_results:
        return "generate_illustration_prompts"

    latest = eval_results[-1]
    retry_count = state.get("retry_count") or 0

    if latest.book_pass or retry_count >= 2:
        return "generate_illustration_prompts"
    return "regenerate_text"


def build_graph():
    workflow = StateGraph(StoryState)

    workflow.add_node("extract_memory", extract_memory)
    workflow.add_node("load_characters", load_characters)
    workflow.add_node("plan_story", plan_story)
    workflow.add_node("generate_text", generate_text)
    workflow.add_node("evaluate_text", evaluate_text)
    workflow.add_node("regenerate_text", regenerate_text)
    workflow.add_node("generate_illustration_prompts", generate_illustration_prompts)
    workflow.add_node("generate_illustrations", create_illustrations)

    workflow.set_entry_point("extract_memory")
    workflow.add_edge("extract_memory", "load_characters")
    workflow.add_edge("load_characters", "plan_story")
    workflow.add_edge("plan_story", "generate_text")
    workflow.add_edge("generate_text", "evaluate_text")
    workflow.add_conditional_edges(
        "evaluate_text",
        _route_after_evaluation,
        {
            "regenerate_text": "regenerate_text",
            "generate_illustration_prompts": "generate_illustration_prompts",
        },
    )
    workflow.add_edge("regenerate_text", "evaluate_text")
    workflow.add_edge("generate_illustration_prompts", "generate_illustrations")
    workflow.add_edge("generate_illustrations", END)

    return workflow.compile()


story_graph = build_graph()
