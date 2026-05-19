from pathlib import Path

from app.workflow.state import StoryState, IllustrationPromptValidationResult
from app.workflow.llm import call_structured

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "validate_illustration_prompts_system.txt").read_text()

EVAL_TEMPERATURE = 0.2


def _build_user_prompt(state: StoryState) -> str:
    plan = state["story_plan"]
    prompts = state["illustration_prompts"] or []

    page_outlines = "\n".join(
        f"Page {p.page_number} ({p.arc_position}): {p.outline}"
        for p in sorted(plan.pages, key=lambda p: p.page_number)
    )

    prompts_text = "\n\n".join(
        f"Pages {p.page_numbers} [{p.arc_group}]:\n{p.prompt}"
        for p in prompts
    )

    return (
        f"Style guide: {plan.style_guide}\n\n"
        f"Page outlines:\n{page_outlines}\n\n"
        f"Illustration prompts:\n{prompts_text}"
    )


def validate_illustration_prompts(state: StoryState) -> dict:
    result = call_structured(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(state),
        response_model=IllustrationPromptValidationResult,
        temperature=EVAL_TEMPERATURE,
    )
    return {"illustration_prompt_validation": result}
