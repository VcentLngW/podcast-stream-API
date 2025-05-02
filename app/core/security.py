from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    """Verify that a plain password matches the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def create_verification_token(email: str):
    """Create a verification token for email confirmation"""
    data = {"sub": email, "type": "verification"}
    # Set expiration to 24 hours for verification tokens
    expiration = timedelta(hours=24)
    return create_access_token(data=data, expires_delta=expiration)


def create_password_reset_token(email: str):
    """Create a token for password reset"""
    data = {"sub": email, "type": "password_reset"}
    # Set expiration to 1 hour for password reset tokens
    expiration = timedelta(hours=1)
    return create_access_token(data=data, expires_delta=expiration) 