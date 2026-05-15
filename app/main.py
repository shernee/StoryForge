from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.models.database import create_tables, get_db
from app.api.stories import router as stories_router
from app.api.memories import router as memories_router
import os

app = FastAPI(title="StoryForge", version="0.1.0")

app.include_router(stories_router)
app.include_router(memories_router)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    create_tables()

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0", "service": "StoryForge"}

@app.get("/")
async def root():
    return {"message": "Welcome to StoryForge v0.1", "docs": "/docs"}

# Test database connection
@app.get("/db-test")
async def db_test(db: Session = Depends(get_db)):
    return {"database": "connected", "status": "ok"}