from pathlib import Path

from app.workflow.state import StoryState, GeneratedPages, PageText
from app.workflow.llm import call_structured

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "generate_text_system.txt").read_text()


def _build_prompt(state: StoryState) -> str:
    plan = state["story_plan"]
    characters = state["character_profiles"] or []
    pages = state["pages"] or []
    text_feedback: dict[int, str] = state.get("text_feedback") or {}

    failing_nums = set(text_feedback.keys())
    passing_pages = sorted(
        (p for p in pages if p.page_number not in failing_nums),
        key=lambda p: p.page_number,
    )
    failing_pages = sorted(
        (p for p in pages if p.page_number in failing_nums),
        key=lambda p: p.page_number,
    )

    char_lines = "\n".join(
        f"- {c.name}: {c.visual_description}" for c in characters
    ) or "No character profiles on file."

    passing_block = "\n\n".join(
        f"Page {p.page_number} (passing — shown for context only):\n{p.text}"
        for p in passing_pages
    )

    failing_block = "\n\n".join(
        f"Page {p.page_number} (regenerate):\n"
        f"Current text:\n{p.text}\n"
        f"Feedback: {text_feedback[p.page_number]}"
        for p in failing_pages
    )

    return (
        f"Story plan:\n{plan.model_dump_json(indent=2)}\n\n"
        f"Character visual descriptions:\n{char_lines}\n\n"
        f"Passing pages (for narrative coherence — do NOT return these):\n{passing_block}\n\n"
        f"Pages to regenerate:\n{failing_block}\n\n"
        "INSTRUCTIONS:\n"
        "- Rewrite ONLY the pages marked 'regenerate' above.\n"
        "- Apply the specific feedback for each failing page.\n"
        "- Preserve narrative flow: your pages must connect naturally to the passing pages.\n"
        "- Maintain any structural repetition established across the book.\n"
        "- Return ONLY the regenerated pages in your response."
    )


def regenerate_text(state: StoryState) -> dict:
    text_feedback: dict[int, str] = state.get("text_feedback") or {}
    pages = state["pages"] or []
    failing_nums = set(text_feedback.keys())

    result = call_structured(
        system=SYSTEM_PROMPT,
        user=_build_prompt(state),
        response_model=GeneratedPages,
    )

    regen_by_num: dict[int, PageText] = {p.page_number: p for p in result.pages}
    merged = [
        regen_by_num.get(p.page_number, p)
        for p in sorted(pages, key=lambda p: p.page_number)
    ]

    return {
        "pages": merged,
        "retry_count": (state.get("retry_count") or 0) + 1,
    }
