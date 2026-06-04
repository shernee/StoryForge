from app.workflow.state import StoryState, CharacterProfile
from app.models.database import SessionLocal, Character


def load_characters(state: StoryState) -> dict:
    character_names = state["memory_metadata"].characters
    profiles: list[CharacterProfile] = []

    db = SessionLocal()
    try:
        user_code = state["user_code"]
        all_chars = db.query(Character).filter(Character.code == user_code).all()

        # Build lookup: lowercase name + any alias → Character row
        lookup: dict[str, Character] = {}
        for row in all_chars:
            lookup[row.name.lower()] = row
            for alias in (row.aliases or []):
                if alias.strip():
                    lookup[alias.strip().lower()] = row

        for name in character_names:
            row = lookup.get(name.lower())
            if row:
                profiles.append(CharacterProfile(
                    name=row.name,
                    role=row.role,
                    age=row.age,
                    visual_description=row.visual_description or "",
                ))
            else:
                profiles.append(CharacterProfile(
                    name=name,
                    role="family member",
                    age="unknown",
                    visual_description="",
                ))
    finally:
        db.close()

    return {"character_profiles": profiles}
