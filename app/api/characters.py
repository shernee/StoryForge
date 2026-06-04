from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db, Character
from app.api.auth import require_code, AccessCode

router = APIRouter(prefix="/characters", tags=["characters"])

VALID_ROLES = ["parent", "grandparent", "sibling", "friend", "pet", "other"]


class CharacterCreate(BaseModel):
    name: str
    role: str
    age: str
    aliases: list[str] = []


class CharacterResponse(BaseModel):
    id: str
    name: str
    role: str
    age: str
    aliases: list[str]


@router.get("", response_model=list[CharacterResponse])
def list_characters(db: Session = Depends(get_db), access_code: AccessCode = Depends(require_code)):
    rows = db.query(Character).filter(Character.code == access_code.code).order_by(Character.created_at).all()
    return [CharacterResponse(id=r.id, name=r.name, role=r.role, age=r.age, aliases=r.aliases or []) for r in rows]


@router.post("", response_model=CharacterResponse, status_code=201)
def create_character(body: CharacterCreate, db: Session = Depends(get_db), access_code: AccessCode = Depends(require_code)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")
    aliases = [a.strip() for a in body.aliases if a.strip()]
    char = Character(
        code=access_code.code,
        name=name,
        role=body.role,
        age=body.age.strip(),
        visual_description="",
        aliases=aliases,
    )
    db.add(char)
    db.commit()
    db.refresh(char)
    return CharacterResponse(id=char.id, name=char.name, role=char.role, age=char.age, aliases=char.aliases or [])


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: str, db: Session = Depends(get_db), access_code: AccessCode = Depends(require_code)):
    char = db.query(Character).filter(Character.id == character_id, Character.code == access_code.code).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(char)
    db.commit()
