import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, SessionLocal, Memory, Story, Page
from app.workflow.graph import story_graph
from app.workflow.nodes.evaluate_text import evaluate_text
from app.workflow.nodes.generate_illustration_prompts import generate_illustration_prompts
from app.workflow.nodes.validate_illustration_prompts import validate_illustration_prompts
from app.workflow.nodes.generate_illustrations import create_illustrations
from app.workflow.state import StoryState, StoryPlan, PageOutline, PageText, IllustrationPrompt

router = APIRouter(prefix="/stories", tags=["stories"])

VALID_TONES = {"funny", "adventurous", "gentle", "moral"}


class GenerateStoryRequest(BaseModel):
    memory: str
    tone: str


class GenerateStoryResponse(BaseModel):
    story_id: str
    memory_id: str
    title: str
    status: str
    page_count: int


class StoryStatusResponse(BaseModel):
    story_id: str
    status: str


class PageResponse(BaseModel):
    page_number: int
    text: str
    illustration_prompt: str | None
    illustration_path: str | None
    mood: str | None
    arc_position: str | None


class StoryResponse(BaseModel):
    story_id: str
    title: str
    tone: str
    style_guide: str | None
    status: str
    pages: list[PageResponse]


class StorySummary(BaseModel):
    story_id: str
    memory_id: str
    title: str
    tone: str
    status: str
    page_count: int


def _run_story_generation(story_id: str, memory_id: str, raw_memory_text: str, tone: str):
    db = SessionLocal()
    try:
        initial_state: StoryState = {
            "story_id": story_id,
            "raw_memory_text": raw_memory_text,
            "tone": tone,
            "memory_metadata": None,
            "character_profiles": None,
            "story_plan": None,
            "pages": None,
            "illustration_prompts": None,
            "illustration_paths": None,
            "error": None,
            "evaluation_results": [],
            "retry_count": 0,
            "text_feedback": None,
        }

        result = story_graph.invoke(initial_state)

        metadata = result["memory_metadata"]
        plan = result["story_plan"]
        pages = result["pages"]
        illustration_by_page = {
            page_num: p
            for p in result["illustration_prompts"]
            for page_num in p.page_numbers
        }
        path_by_page = {
            page_num: path
            for illus, path in zip(result["illustration_prompts"], result["illustration_paths"] or [])
            for page_num in illus.page_numbers
        }

        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        memory.setting = metadata.setting
        memory.characters = metadata.characters
        memory.themes = metadata.themes
        memory.mood_arc = metadata.mood_arc

        story = db.query(Story).filter(Story.id == story_id).first()
        story.title = plan.title
        story.style_guide = plan.style_guide
        story.status = "complete"

        outline_by_page = {o.page_number: o.outline for o in plan.pages}
        for page in pages:
            db.add(Page(
                story_id=story_id,
                page_number=page.page_number,
                outline=outline_by_page.get(page.page_number),
                text=page.text,
                illustration_prompt=illustration_by_page[page.page_number].prompt if page.page_number in illustration_by_page else None,
                illustration_arc_group=illustration_by_page[page.page_number].arc_group if page.page_number in illustration_by_page else None,
                illustration_path=path_by_page.get(page.page_number),
                mood=page.mood,
                arc_position=page.arc_position,
            ))

        db.commit()
    except Exception:
        db.rollback()
        story = db.query(Story).filter(Story.id == story_id).first()
        if story:
            story.status = "error"
            db.commit()
    finally:
        db.close()


@router.post("/generate", response_model=GenerateStoryResponse)
def generate_story(request: GenerateStoryRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if request.tone not in VALID_TONES:
        raise HTTPException(
            status_code=422,
            detail=f"tone must be one of {sorted(VALID_TONES)}",
        )

    story_id = f"story_{uuid.uuid4().hex[:8]}"
    memory_id = f"mem_{uuid.uuid4().hex[:8]}"

    db.add(Memory(id=memory_id, raw_text=request.memory))
    db.add(Story(id=story_id, title="Generating...", memory_id=memory_id, tone=request.tone, status="generating"))
    db.commit()

    background_tasks.add_task(_run_story_generation, story_id, memory_id, request.memory, request.tone)

    return GenerateStoryResponse(
        story_id=story_id,
        memory_id=memory_id,
        title="Generating...",
        status="generating",
        page_count=0,
    )


@router.get("/{story_id}/status", response_model=StoryStatusResponse)
def get_story_status(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StoryStatusResponse(story_id=story_id, status=story.status)


@router.get("", response_model=list[StorySummary])
def list_stories(db: Session = Depends(get_db)):
    stories = db.query(Story).order_by(Story.created_at.desc()).all()
    return [
        StorySummary(
            story_id=s.id,
            memory_id=s.memory_id,
            title=s.title,
            tone=s.tone,
            status=s.status,
            page_count=len(s.pages),
        )
        for s in stories
    ]


@router.post("/{story_id}/generate-illustration-prompts", response_model=StoryResponse)
def generate_illustration_prompts_endpoint(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    sorted_pages = sorted(story.pages, key=lambda p: p.page_number)

    state: StoryState = {
        "raw_memory_text": story.memory.raw_text,
        "tone": story.tone,
        "memory_metadata": None,
        "character_profiles": None,
        "story_plan": StoryPlan(
            title=story.title,
            page_count=len(sorted_pages),
            style_guide=story.style_guide or "",
            pages=[
                PageOutline(
                    page_number=p.page_number,
                    outline=p.outline or "",
                    mood=p.mood or "",
                    arc_position=p.arc_position or "",
                )
                for p in sorted_pages
            ],
        ),
        "pages": [
            PageText(
                page_number=p.page_number,
                text=p.text,
                mood=p.mood or "",
                arc_position=p.arc_position or "",
            )
            for p in sorted_pages
        ],
        "illustration_prompts": None,
        "error": None,
    }

    result = generate_illustration_prompts(state)
    illustration_by_page = {
        page_num: p
        for p in result["illustration_prompts"]
        for page_num in p.page_numbers
    }

    for page in story.pages:
        if page.page_number in illustration_by_page:
            page.illustration_prompt = illustration_by_page[page.page_number].prompt
            page.illustration_arc_group = illustration_by_page[page.page_number].arc_group
    db.commit()

    db.refresh(story)
    return StoryResponse(
        story_id=story.id,
        title=story.title,
        tone=story.tone,
        style_guide=story.style_guide,
        status=story.status,
        pages=[
            PageResponse(
                page_number=p.page_number,
                text=p.text,
                illustration_prompt=p.illustration_prompt,
                illustration_path=p.illustration_path,
                mood=p.mood,
                arc_position=p.arc_position,
            )
            for p in sorted(story.pages, key=lambda p: p.page_number)
        ],
    )


@router.post("/{story_id}/generate-illustrations", response_model=StoryResponse)
def generate_illustrations(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    sorted_pages = sorted(story.pages, key=lambda p: p.page_number)

    groups: dict[str, IllustrationPrompt] = {}
    for p in sorted_pages:
        if not p.illustration_prompt or not p.illustration_arc_group:
            continue
        if p.illustration_arc_group not in groups:
            groups[p.illustration_arc_group] = IllustrationPrompt(
                page_numbers=[p.page_number],
                arc_group=p.illustration_arc_group,
                prompt=p.illustration_prompt,
            )
        else:
            groups[p.illustration_arc_group].page_numbers.append(p.page_number)

    if not groups:
        raise HTTPException(status_code=422, detail="No illustration prompts found — run regenerate-illustrations first")

    state: StoryState = {
        "story_id": story_id,
        "raw_memory_text": "",
        "tone": story.tone,
        "memory_metadata": None,
        "character_profiles": None,
        "story_plan": None,
        "pages": None,
        "illustration_prompts": list(groups.values()),
        "illustration_paths": None,
        "error": None,
    }

    result = create_illustrations(state)
    path_by_page = {
        page_num: path
        for illus, path in zip(state["illustration_prompts"], result["illustration_paths"] or [])
        for page_num in illus.page_numbers
    }

    for page in story.pages:
        if page.page_number in path_by_page:
            page.illustration_path = path_by_page[page.page_number]
    db.commit()

    db.refresh(story)
    return StoryResponse(
        story_id=story.id,
        title=story.title,
        tone=story.tone,
        style_guide=story.style_guide,
        status=story.status,
        pages=[
            PageResponse(
                page_number=p.page_number,
                text=p.text,
                illustration_prompt=p.illustration_prompt,
                illustration_path=p.illustration_path,
                mood=p.mood,
                arc_position=p.arc_position,
            )
            for p in sorted_pages
        ],
    )


@router.post("/{story_id}/validate-illustration-prompts")
def validate_illustration_prompts_endpoint(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    sorted_pages = sorted(story.pages, key=lambda p: p.page_number)

    groups: dict[str, IllustrationPrompt] = {}
    for p in sorted_pages:
        if not p.illustration_prompt or not p.illustration_arc_group:
            continue
        if p.illustration_arc_group not in groups:
            groups[p.illustration_arc_group] = IllustrationPrompt(
                page_numbers=[p.page_number],
                arc_group=p.illustration_arc_group,
                prompt=p.illustration_prompt,
            )
        else:
            groups[p.illustration_arc_group].page_numbers.append(p.page_number)

    if not groups:
        raise HTTPException(status_code=422, detail="No illustration prompts found — run generate-illustration-prompts first")

    state: StoryState = {
        "story_plan": StoryPlan(
            title=story.title,
            page_count=len(sorted_pages),
            style_guide=story.style_guide or "",
            pages=[
                PageOutline(
                    page_number=p.page_number,
                    outline=p.outline or "",
                    mood=p.mood or "",
                    arc_position=p.arc_position or "",
                )
                for p in sorted_pages
            ],
        ),
        "illustration_prompts": list(groups.values()),
    }

    result = validate_illustration_prompts(state)
    return JSONResponse(content=result["illustration_prompt_validation"].model_dump(by_alias=True))


@router.post("/{story_id}/evaluate-text")
def evaluate_story_text(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not story.pages:
        raise HTTPException(status_code=422, detail="Story has no pages to evaluate")

    sorted_pages = sorted(story.pages, key=lambda p: p.page_number)
    state: StoryState = {
        "pages": [
            PageText(
                page_number=p.page_number,
                text=p.text,
                mood=p.mood or "",
                arc_position=p.arc_position or "",
            )
            for p in sorted_pages
        ],
    }

    result = evaluate_text(state)
    eval_result = result["evaluation_results"][0]
    return JSONResponse(content=eval_result.model_dump(by_alias=True))


@router.get("/{story_id}", response_model=StoryResponse)
def get_story(story_id: str, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StoryResponse(
        story_id=story.id,
        title=story.title,
        tone=story.tone,
        style_guide=story.style_guide,
        status=story.status,
        pages=[
            PageResponse(
                page_number=p.page_number,
                text=p.text,
                illustration_prompt=p.illustration_prompt,
                illustration_path=p.illustration_path,
                mood=p.mood,
                arc_position=p.arc_position,
            )
            for p in sorted(story.pages, key=lambda p: p.page_number)
        ],
    )
