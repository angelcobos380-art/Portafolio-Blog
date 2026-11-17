from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.admin.deps import templates
from app.core.config import settings
from app.core.database import User, get_session
from app.core.security import (
    count_recent_failed,
    create_access_token,
    record_login_attempt,
    verify_password,
)

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    failed = count_recent_failed(session, email)
    if failed >= settings.LOGIN_MAX_ATTEMPTS:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Demasiados intentos fallidos. Intenta de nuevo en unos minutos."},
            status_code=429,
        )

    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.password_hash):
        record_login_attempt(session, email, success=False)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Credenciales incorrectas."},
            status_code=401,
        )

    record_login_attempt(session, email, success=True)
    token = create_access_token({"sub": user.user_id, "email": user.email, "role": user.role})
    response = RedirectResponse("/admin/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie("access_token")
    return response
