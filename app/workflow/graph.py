from langgraph.graph import StateGraph, END
from app.workflow.state import StoryState
from app.workflow.nodes.extract_memory import extract_memory
from app.workflow.nodes.load_characters import load_characters
from app.workflow.nodes.plan_story import plan_story
from app.workflow.nodes.generate_text import generate_text
from app.workflow.nodes.generate_illustration_prompts import generate_illustration_prompts
from app.workflow.nodes.generate_illustrations import create_illustrations


def build_graph():
    workflow = StateGraph(StoryState)

    workflow.add_node("extract_memory", extract_memory)
    workflow.add_node("load_characters", load_characters)
    workflow.add_node("plan_story", plan_story)
    workflow.add_node("generate_text", generate_text)
    workflow.add_node("generate_illustration_prompts", generate_illustration_prompts)
    workflow.add_node("generate_illustrations", create_illustrations)

    workflow.set_entry_point("extract_memory")
    workflow.add_edge("extract_memory", "load_characters")
    workflow.add_edge("load_characters", "plan_story")
    workflow.add_edge("plan_story", "generate_text")
    workflow.add_edge("generate_text", "generate_illustration_prompts")
    workflow.add_edge("generate_illustration_prompts", "generate_illustrations")
    workflow.add_edge("generate_illustrations", END)

    return workflow.compile()


story_graph = build_graph()
