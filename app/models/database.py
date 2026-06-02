from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

DATABASE_URL = "sqlite:///./data/storyforge.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=lambda: f"char_{uuid.uuid4().hex[:8]}")
    code = Column(String, ForeignKey("access_codes.code"), nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    age = Column(String, nullable=False)
    visual_description = Column(Text, nullable=False)
    personality_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    code = Column(String, ForeignKey("access_codes.code"), nullable=True)
    raw_text = Column(Text, nullable=False)
    setting = Column(String)
    characters = Column(JSON)
    themes = Column(JSON)
    mood_arc = Column(String)
    date_approximate = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    stories = relationship("Story", back_populates="memory")

class Story(Base):
    __tablename__ = "stories"

    id = Column(String, primary_key=True, default=lambda: f"story_{uuid.uuid4().hex[:8]}")
    code = Column(String, ForeignKey("access_codes.code"), nullable=True)
    title = Column(String, nullable=False)
    memory_id = Column(String, ForeignKey("memories.id"), nullable=False)
    tone = Column(String, nullable=False)
    style_guide = Column(Text)
    status = Column(String, default="planned")
    created_at = Column(DateTime, default=datetime.utcnow)

    memory = relationship("Memory", back_populates="stories")
    pages = relationship("Page", back_populates="story", cascade="all, delete-orphan")

class Page(Base):
    __tablename__ = "pages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(String, ForeignKey("stories.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    outline = Column(Text)
    text = Column(Text, nullable=False)
    illustration_prompt = Column(Text)
    illustration_arc_group = Column(String)
    illustration_path = Column(String)
    mood = Column(String)
    arc_position = Column(String)
    
    story = relationship("Story", back_populates="pages")

class AccessCode(Base):
    __tablename__ = "access_codes"

    code = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    generations_today = Column(Integer, default=0, nullable=False)
    last_generation_date = Column(Date, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()