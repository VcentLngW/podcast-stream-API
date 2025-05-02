from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserLogin, Token

router = APIRouter(prefix="/api/testing", tags=["testing"])


@router.get("/protected", summary="Protected test endpoint")
async def protected_test(current_user: User = Depends(get_current_user)):
    """
    Test endpoint that requires authentication.
    """
    return {"message": "You are authenticated", "user_email": current_user.email}


@router.post("/token", response_model=Token, summary="Get test token")
async def get_test_token(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Generate a JWT token for testing the API.
    
    This endpoint is specifically for testing the API through Swagger UI.
    It returns a token that can be used with the "Authorize" button.
    
    Steps to use:
    1. Call this endpoint with valid credentials
    2. Copy the access_token from the response
    3. Click the "Authorize" button at the top of the page
    4. Enter the token in the format: Bearer {token}
    5. Click "Authorize" and close the dialog
    6. Now you can test protected endpoints
    """
    # Get user by email
    user = UserRepository.get_user_by_email(db, email=user_data.email)
    
    # Check if user exists and password is correct
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "note": "Use this token with the Authorize button. Format: Bearer {token}"
    }