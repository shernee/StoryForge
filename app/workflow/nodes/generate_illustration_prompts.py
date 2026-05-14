from pathlib import Path

from app.workflow.state import StoryState, GeneratedIllustrationPrompts
from app.workflow.llm import call_structured
from app.workflow.nodes.helpers.page_grouping import group_pages_by_arc

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "generate_illustration_prompts_system.txt").read_text()


def _build_user_prompt(state: StoryState) -> str:
    plan = state["story_plan"]
    pages = state["pages"] or []

    page_groups = group_pages_by_arc(pages, plan.pages)

    return (
        f"Style guide: {plan.style_guide}\n\n"
        f"Page groups:\n{page_groups}"
    )


def generate_illustration_prompts(state: StoryState) -> dict:
    result = call_structured(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(state),
        response_model=GeneratedIllustrationPrompts,
    )
    return {"illustration_prompts": result.prompts}
