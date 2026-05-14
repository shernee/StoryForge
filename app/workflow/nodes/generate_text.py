from pathlib import Path

from app.workflow.state import StoryState, GeneratedPages
from app.workflow.llm import call_structured

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "generate_text_system.txt").read_text()


def _build_user_prompt(state: StoryState) -> str:
    plan = state["story_plan"]
    characters = state["character_profiles"] or []

    char_lines = "\n".join(
        f"- {c.name}: {c.visual_description}"
        for c in characters
    ) or "No character profiles on file."

    return (
        f"Story plan:\n{plan.model_dump_json(indent=2)}\n\n"
        f"Character visual descriptions:\n{char_lines}"
    )


def generate_text(state: StoryState) -> dict:
    result = call_structured(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(state),
        response_model=GeneratedPages,
    )
    return {"pages": result.pages}
