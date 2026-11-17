from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@example.com")
    password: str = Field(..., example="Admin123!")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
