from __future__ import annotations
import operator
from typing import Annotated, TypedDict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MemoryMetadata(BaseModel):
    setting: str
    characters: list[str]
    themes: list[str]
    mood_arc: str


class CharacterProfile(BaseModel):
    name: str
    role: str
    age: str
    visual_description: str
    personality_notes: Optional[str] = None


class PageOutline(BaseModel):
    page_number: int
    outline: str
    mood: str
    arc_position: str


class StoryPlan(BaseModel):
    title: str
    page_count: int
    pages: list[PageOutline]
    style_guide: str


class PageText(BaseModel):
    page_number: int
    text: str
    mood: str
    arc_position: str


class GeneratedPages(BaseModel):
    pages: list[PageText]


class IllustrationPrompt(BaseModel):
    page_numbers: list[int]
    arc_group: str
    prompt: str


class GeneratedIllustrationPrompts(BaseModel):
    prompts: list[IllustrationPrompt]


class PromptWarning(BaseModel):
    rule: str
    offending_text: str


class PromptValidation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page_numbers: list[int]
    prompt_pass: bool = Field(alias="pass")
    warnings: list[PromptWarning] = Field(default_factory=list)


class IllustrationPromptValidationResult(BaseModel):
    prompts: list[PromptValidation]


class PageEvaluation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page_number: int
    page_pass: bool = Field(alias="pass")
    hard_failures: list[str] = Field(default_factory=list)
    soft_failures: list[str] = Field(default_factory=list)
    failing_text: list[str] = Field(default_factory=list)
    feedback: Optional[str] = None


class PatternFailure(BaseModel):
    type: str
    affected_pages: list[int]
    note: str


class EvaluationResult(BaseModel):
    book_pass: bool
    pages: list[PageEvaluation]
    pattern_failures: list[PatternFailure] = Field(default_factory=list)


class StoryState(TypedDict):
    story_id: str
    user_code: str
    raw_memory_text: str
    tone: str
    memory_metadata: Optional[MemoryMetadata]
    character_profiles: Optional[list[CharacterProfile]]
    story_plan: Optional[StoryPlan]
    pages: Optional[list[PageText]]
    illustration_prompts: Optional[list[IllustrationPrompt]]
    illustration_prompt_validation: Optional[IllustrationPromptValidationResult]
    illustration_paths: Optional[list[str]]
    error: Optional[str]
    evaluation_results: Annotated[list[EvaluationResult], operator.add]
    retry_count: Optional[int]
    text_feedback: Optional[dict[int, str]]
