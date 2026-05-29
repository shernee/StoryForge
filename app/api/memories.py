from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, Memory, AccessCode
from app.api.auth import require_code

router = APIRouter(prefix="/memories", tags=["memories"])


class MemoryResponse(BaseModel):
    memory_id: str
    raw_text: str
    setting: str | None
    characters: list[str] | None
    themes: list[str] | None
    mood_arc: str | None


@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str, db: Session = Depends(get_db), access_code: AccessCode = Depends(require_code)):
    memory = db.query(Memory).filter(Memory.id == memory_id, Memory.code == access_code.code).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryResponse(
        memory_id=memory.id,
        raw_text=memory.raw_text,
        setting=memory.setting,
        characters=memory.characters,
        themes=memory.themes,
        mood_arc=memory.mood_arc,
    )
