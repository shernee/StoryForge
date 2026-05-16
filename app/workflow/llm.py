import json
import logging
import os
from typing import TypeVar, Type
from openai import OpenAI
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "gpt-4o"

logger = logging.getLogger(__name__)


class LLMParseError(Exception):
    """LLM response could not be parsed into the expected schema after all retries."""


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )


def call_structured(
    system: str,
    user: str,
    response_model: Type[T],
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
    temperature: float | None = None,
) -> T:
    client = get_client()
    schema_hint = json.dumps(response_model.model_json_schema(by_alias=True), indent=2)
    full_system = f"{system}\n\nRespond with a JSON object matching this schema:\n{schema_hint}"

    messages: list[dict] = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user},
    ]

    last_error: Exception | None = None

    base_kwargs: dict = {
        "model": model,
        "response_format": {"type": "json_object"},
    }
    if temperature is not None:
        base_kwargs["temperature"] = temperature

    for attempt in range(1, max_retries + 1):
        response = client.chat.completions.create(**base_kwargs, messages=messages)

        content = response.choices[0].message.content
        if not content:
            last_error = LLMParseError("LLM returned empty content")
            logger.warning("Attempt %d/%d: empty response from LLM", attempt, max_retries)
            continue

        try:
            return response_model.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "Attempt %d/%d: failed to parse response as %s.\nError: %s\nResponse: %.500s",
                attempt,
                max_retries,
                response_model.__name__,
                exc,
                content,
            )
            # Feed the bad response and the parse error back so the model can self-correct
            messages = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        f"That response could not be parsed. Error: {exc}\n"
                        "Please respond again with valid JSON that matches the schema exactly."
                    ),
                },
            ]

    raise LLMParseError(
        f"Failed to parse LLM response as {response_model.__name__} "
        f"after {max_retries} attempt(s)"
    ) from last_error
