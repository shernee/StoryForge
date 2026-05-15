import base64
import json
import logging
import os
from pathlib import Path

from app.workflow.llm import get_client
from app.workflow.state import StoryState

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "google/gemini-2.5-flash-image")
OUTPUT_DIR = Path("output")

logger = logging.getLogger(__name__)


def _fetch_image_bytes(prompt: str) -> bytes:
    client = get_client()
    raw = client.chat.completions.with_raw_response.create(
        model=IMAGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"modalities": ["text", "image"]},
    )
    data = json.loads(raw.text)
    message = data["choices"][0]["message"]
    content = message.get("content")
    return _extract_image_bytes(content, message)


def _extract_image_bytes(content, message: dict) -> bytes:
    # OpenRouter returns image data in message["images"], not message["content"]
    for part in message.get("images") or []:
        if part.get("type") == "image_url":
            url = part["image_url"]["url"]
            if url.startswith("data:"):
                _, b64 = url.split(",", 1)
                return base64.b64decode(b64)

    # Fallback: content as data URL string or list of parts
    parts = [content] if isinstance(content, str) else content or []
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

    raise ValueError(f"No image data found. Full message: {json.dumps(message)[:2000]}")


def create_illustrations(state: StoryState) -> dict:
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
