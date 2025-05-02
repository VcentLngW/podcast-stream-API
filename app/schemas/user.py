from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    LISTENER = "LISTENER"
    CREATOR = "CREATOR"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.LISTENER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    name: str
    username: Optional[str] = None
    role: UserRole
    is_creator: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: UserRole
    is_creator: Optional[bool] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for resetting a password with a token"""
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8) 