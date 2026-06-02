from collections import Counter
from pathlib import Path

from app.workflow.state import StoryState, EvaluationResult, PageText
from app.workflow.llm import call_structured

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "evaluate_text_system.txt").read_text()

EVAL_TEMPERATURE = 0.2


def _format_pages(pages: list[PageText]) -> str:
    return "\n\n".join(
        f"Page {p.page_number}:\n{p.text}"
        for p in sorted(pages, key=lambda p: p.page_number)
    )


def evaluate_text(state: StoryState) -> dict:
    pages = state["pages"] or []

    result = call_structured(
        system=SYSTEM_PROMPT,
        user=_format_pages(pages),
        response_model=EvaluationResult,
        temperature=EVAL_TEMPERATURE,
    )

    counts: Counter = Counter()
    for page in result.pages:
        counts.update(page.soft_failures)
    result.soft_failure_counts = dict(counts)

    text_feedback: dict[int, str] = {}

    for page in result.pages:
        if not page.page_pass and page.feedback:
            text_feedback[page.page_number] = page.feedback

    for pf in result.pattern_failures:
        note = f"[Pattern: {pf.type} across {len(pf.affected_pages)} pages] {pf.note}"
        for page_num in pf.affected_pages:
            existing = text_feedback.get(page_num, "")
            text_feedback[page_num] = f"{existing} | {note}" if existing else note

    return {
        "evaluation_results": [result],
        "text_feedback": text_feedback or None,
    }
