from fastapi import FastAPI, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from alembic.config import Config
from alembic import command
from app.models.database import get_db, SessionLocal, AccessCode
from app.api.stories import router as stories_router
from app.api.memories import router as memories_router
from app.api.auth import router as auth_router, COOKIE_NAME
import os

app = FastAPI(title="StoryForge", version="0.1.0")

PROTECTED_PAGES = {"/new", "/read"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PROTECTED_PAGES:
            code = request.cookies.get(COOKIE_NAME)
            if not code:
                return RedirectResponse(url="/login", status_code=302)
            db = SessionLocal()
            try:
                access_code = db.query(AccessCode).filter(AccessCode.code == code).first()
                if not access_code:
                    resp = RedirectResponse(url="/login", status_code=302)
                    resp.delete_cookie(COOKIE_NAME)
                    return resp
            finally:
                db.close()
        return await call_next(request)


app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(stories_router)
app.include_router(memories_router)


@app.on_event("startup")
async def startup_event():
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    _run_migrations()
    _seed_admin()


def _run_migrations():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def _seed_admin():
    admin_code = os.environ.get("ADMIN_CODE", "").strip()
    if not admin_code:
        return
    db = SessionLocal()
    try:
        existing = db.query(AccessCode).filter(AccessCode.is_admin == True).first()
        if not existing:
            db.add(AccessCode(code=admin_code, label="Admin", is_admin=True))
            db.commit()

        # Backfill any pre-migration rows that have no code
        for table in ("memories", "stories"):
            db.execute(text(f"UPDATE {table} SET code = :code WHERE code IS NULL"), {"code": admin_code})
        db.execute(text("UPDATE characters SET code = :code WHERE code IS NULL"), {"code": admin_code})
        db.commit()
    finally:
        db.close()


app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/read")
async def reader_page():
    return FileResponse("app/static/reader.html")


@app.get("/new")
async def create_page():
    return FileResponse("app/static/create.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0", "service": "StoryForge"}


@app.get("/")
async def root():
    return RedirectResponse(url="/login", status_code=302)


@app.get("/db-test")
async def db_test(db: Session = Depends(get_db)):
    return {"database": "connected", "status": "ok"}
