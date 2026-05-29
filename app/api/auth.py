from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.models.database import get_db, AccessCode

router = APIRouter(tags=["auth"])


def require_code(request: Request, db: Session = Depends(get_db)) -> AccessCode:
    code = request.cookies.get(COOKIE_NAME)
    if not code:
        raise HTTPException(status_code=401, detail="Authentication required")
    access_code = db.query(AccessCode).filter(AccessCode.code == code).first()
    if not access_code:
        raise HTTPException(status_code=401, detail="Invalid access code")
    return access_code

COOKIE_NAME = "sf_access_code"
DAILY_LIMIT = 3


@router.get("/login")
async def login_page():
    return FileResponse("app/static/login.html")


@router.post("/auth/login")
async def do_login(code: str = Form(...), db: Session = Depends(get_db)):
    access_code = db.query(AccessCode).filter(AccessCode.code == code.strip()).first()
    if not access_code:
        return RedirectResponse(url="/login?error=1", status_code=303)
    resp = RedirectResponse(url="/new", status_code=303)
    resp.set_cookie(key=COOKIE_NAME, value=code.strip(), httponly=True, max_age=30 * 24 * 3600, samesite="lax")
    return resp


@router.post("/auth/logout")
async def do_logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("/auth/status")
async def auth_status(request: Request, db: Session = Depends(get_db)):
    from datetime import date
    code = request.cookies.get(COOKIE_NAME)
    if not code:
        return {"authenticated": False}
    access_code = db.query(AccessCode).filter(AccessCode.code == code).first()
    if not access_code:
        return {"authenticated": False}

    today = date.today()
    generations_today = access_code.generations_today
    if access_code.last_generation_date != today:
        generations_today = 0

    return {
        "authenticated": True,
        "label": access_code.label,
        "is_admin": access_code.is_admin,
        "generations_today": generations_today,
        "daily_limit": None if access_code.is_admin else DAILY_LIMIT,
        "remaining": None if access_code.is_admin else max(0, DAILY_LIMIT - generations_today),
    }
