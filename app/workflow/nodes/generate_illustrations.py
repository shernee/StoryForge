import base64
import logging
import os
from pathlib import Path

from app.workflow.llm import get_client
from app.workflow.state import StoryState

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "google/gemini-2.0-flash-exp")
OUTPUT_DIR = Path("output")

logger = logging.getLogger(__name__)


def _fetch_image_bytes(prompt: str) -> bytes:
    client = get_client()
    raw = client.chat.completions.with_raw_response.create(
        model=IMAGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "modalities": ["image"],
            "generation_config": {
                "response_modalities": ["IMAGE"],
                "image_generation_config": {
                    "aspect_ratio": "3:2",
                },
            },
        },
    )
    return _extract_image_bytes(raw.json()["choices"][0]["message"]["content"])


def _extract_image_bytes(content) -> bytes:
    parts = [content] if isinstance(content, str) else content
    if not isinstance(parts, list):
        raise ValueError(f"Unexpected content type: {type(content)}")

    for part in parts:
        if isinstance(part, str) and part.startswith("data:"):
            _, b64 = part.split(",", 1)
            return base64.b64decode(b64)
        if isinstance(part, dict):
            if part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    _, b64 = url.split(",", 1)
                    return base64.b64decode(b64)
            inline = part.get("inline_data") or part.get("inlineData")
            if inline:
                return base64.b64decode(inline["data"])

    raise ValueError(f"No image data found in response: {str(content)[:300]}")


def generate_illustrations(state: StoryState) -> dict:
    story_id = state["story_id"]
    prompts = state["illustration_prompts"] or []

    out_dir = OUTPUT_DIR / story_id
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for idx, illus in enumerate(prompts):
        arc_slug = illus.arc_group.lower().replace(" ", "_")
        dest = out_dir / f"illustration_{idx}_{arc_slug}.png"

        logger.info("Generating illustration %d/%d (%s)", idx + 1, len(prompts), illus.arc_group)
        image_bytes = _fetch_image_bytes(illus.prompt)
        dest.write_bytes(image_bytes)
        logger.info("Saved %s (%d bytes)", dest, len(image_bytes))

        paths.append(str(dest))

    return {"illustration_paths": paths}
