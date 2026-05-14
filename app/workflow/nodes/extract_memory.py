from app.workflow.state import StoryState, MemoryMetadata
from app.workflow.llm import call_structured

SYSTEM_PROMPT = """\
You are a story metadata extractor. Given a short description of a real family memory, \
extract structured metadata. Use the exact character names mentioned in the text. \
Identify the setting, the characters involved, recurring themes (e.g. courage, humour, \
animals, nature), and the emotional arc of the moment.\
"""


def extract_memory(state: StoryState) -> dict:
    metadata = call_structured(
        system=SYSTEM_PROMPT,
        user=state["raw_memory_text"],
        response_model=MemoryMetadata,
    )
    return {"memory_metadata": metadata}
