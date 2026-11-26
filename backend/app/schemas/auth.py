from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["admin@example.com"])
    password: str = Field(..., examples=["Admin123!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
