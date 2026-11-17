from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt

from app.core.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def decode_admin_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def get_admin_user(request: Request):
    token = request.cookies.get("access_token")
    payload = decode_admin_token(token) if token else None
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return payload
