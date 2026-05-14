from __future__ import annotations
from typing import TypedDict, Optional
from pydantic import BaseModel


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


class StoryState(TypedDict):
    story_id: str
    raw_memory_text: str
    tone: str
    memory_metadata: Optional[MemoryMetadata]
    character_profiles: Optional[list[CharacterProfile]]
    story_plan: Optional[StoryPlan]
    pages: Optional[list[PageText]]
    illustration_prompts: Optional[list[IllustrationPrompt]]
    illustration_paths: Optional[list[str]]
    error: Optional[str]
