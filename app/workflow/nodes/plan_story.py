from app.workflow.state import StoryState, StoryPlan
from app.workflow.llm import call_structured

SYSTEM_PROMPT = """\
You are planning a personalised illustrated children's storybook for toddlers (ages 2–4). \
Given a family memory and a chosen tone, create a story plan with: a warm, engaging title; \
a page count of 5–7 pages; a per-page outline with the mood and arc position for each page \
(setup, rising action, climax, resolution, ending); and a visual style guide describing the \
overall look and color palette for the book's scene illustrations. Focus on: the dominant \
colors of the setting (warm sandy yellows, ocean blues, forest greens), the lighting \
(bright midday sun, soft golden evening, grey rainy day), and the general atmosphere \
(busy and colorful, quiet and calm, wild and messy). Do not describe characters, expressions, \
or actions — the style guide is for backgrounds and settings only. \
The story must be grounded in the \
specific events described in the memory. The key moments, conflict, and resolution from the \
real experience should form the backbone of the story arc. Do not invent new scenes or replace \
the real events with generic ones. Embellish for storytelling purposes, but the core narrative \
must come from the memory.\
"""


def _build_user_prompt(state: StoryState) -> str:
    metadata = state["memory_metadata"]
    characters = state["character_profiles"] or []

    char_lines = "\n".join(
        f"- {c.name} ({c.role}, {c.age}): {c.visual_description}"
        for c in characters
    ) or "No character profiles on file."

    return (
        f"Memory (in the user's own words):\n{state['raw_memory_text']}\n\n"
        f"Extracted metadata (for reference):\n{metadata.model_dump_json(indent=2)}\n\n"
        f"Character profiles:\n{char_lines}\n\n"
        f"Tone: {state['tone']}"
    )


def plan_story(state: StoryState) -> dict:
    story_plan = call_structured(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(state),
        response_model=StoryPlan,
    )
    return {"story_plan": story_plan}
