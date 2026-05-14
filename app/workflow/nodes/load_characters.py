from app.workflow.state import StoryState, CharacterProfile
from app.models.database import SessionLocal, Character


def load_characters(state: StoryState) -> dict:
    character_names = state["memory_metadata"].characters
    profiles: list[CharacterProfile] = []

    db = SessionLocal()
    try:
        for name in character_names:
            row = db.query(Character).filter(Character.name == name).first()
            if row:
                profiles.append(CharacterProfile(
                    name=row.name,
                    role=row.role,
                    age=row.age,
                    visual_description=row.visual_description,
                    personality_notes=row.personality_notes,
                ))
            else:
                # No profile on file — proceed with name only so generation still works
                profiles.append(CharacterProfile(
                    name=name,
                    role="family member",
                    age="unknown",
                    visual_description="no description available",
                ))
    finally:
        db.close()

    return {"character_profiles": profiles}
