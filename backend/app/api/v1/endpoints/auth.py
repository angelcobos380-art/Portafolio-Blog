from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import User, get_session
from app.core.security import (
    count_recent_failed,
    create_access_token,
    get_current_user,
    record_login_attempt,
    verify_password,
)
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, session: Session = Depends(get_session)):
    failed = count_recent_failed(session, credentials.email)
    if failed >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intenta de nuevo en unos minutos.",
        )

    user = session.exec(select(User).where(User.email == credentials.email)).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        record_login_attempt(session, credentials.email, success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    record_login_attempt(session, credentials.email, success=True)
    token_data = {"sub": user.user_id, "email": user.email, "role": user.role}
    return TokenResponse(access_token=create_access_token(token_data))


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: dict = Depends(get_current_user), session: Session = Depends(get_session)):
    user = session.get(User, current_user.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o usuario inactivo.")
    return UserMeResponse(user_id=user.user_id, email=user.email, role=user.role)
