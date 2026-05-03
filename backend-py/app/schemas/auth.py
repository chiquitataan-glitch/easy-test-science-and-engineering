from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    displayName: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    tokenType: str = "bearer"
    user: "UserResponse | None" = None


class UserStats(BaseModel):
    totalGenerations: int = 0
    totalPapers: int = 0
    monthGenerations: int = 0


class UserResponse(BaseModel):
    id: str
    displayName: str | None
    email: str
    role: str
    membershipType: str
    membershipExpire: datetime | None = None
    remainingGenerations: int
    identities: list[dict] = []
    stats: UserStats | None = None

    model_config = {"from_attributes": True}
