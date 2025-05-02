from datetime import timedelta
from typing import Annotated, Optional, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status, Header, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_verification_token, verify_password, create_password_reset_token
from app.db.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse, UserRole, PasswordResetRequest, PasswordReset
from app.services.email import send_verification_email
from app.api.deps import get_current_user  # Import the correct implementation

router = APIRouter(prefix="/api/auth", tags=["auth"])

# No need to redefine get_current_user since we're importing it from deps.py

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new user",
             description="Register a new user and send verification email")
async def register(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    db_user = UserRepository.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Generate username from name and check uniqueness
    base_username = user.name.lower().replace(" ", "_")
    username = base_username
    
    # Check if username exists, if so add a random suffix
    suffix = 1
    while UserRepository.get_user_by_username(db, username=username):
        username = f"{base_username}_{suffix}"
        suffix += 1
    
    # Create verification token
    verification_token = create_verification_token(user.email)
    
    # Create user in database
    user_data = user.model_dump()
    user_data["username"] = username
    
    # Ensure role is correct for public registration (no admin role allowed)
    if user_data.get("role") == UserRole.ADMIN:
        user_data["role"] = UserRole.LISTENER  # Default to listener if someone tries to register as admin
    
    created_user = UserRepository.create_user(db, user_data, verification_token)
    
    # Send verification email
    await send_verification_email(
        background_tasks,
        username=created_user.name,  # Use name instead of username for email
        email_to=created_user.email,
        token=verification_token
    )
    
    return created_user


@router.post("/login", response_model=Token,
            summary="User login",
            description="Authenticate with email and password to get an access token")
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with JSON payload.
    
    This endpoint accepts application/json content-type with email and password
    in the request body.
    
    Example:
    ```json
    {
        "email": "user@example.com",
        "password": "userpassword"
    }
    ```
    
    Returns a JWT token that can be used to authenticate further requests.
    """
    # Get user by email
    user = UserRepository.get_user_by_email(db, email=user_data.email)
    
    # Check if user exists and password is correct
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify", status_code=status.HTTP_200_OK,
           summary="Verify email address",
           description="Verify a user's email address using a verification token")
async def verify_email(
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    
    # Verify user
    user = UserRepository.verify_user(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {"message": "Email verified successfully"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK,
            summary="Request password reset",
            description="Request a password reset email with a secure reset link")
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.
    
    This endpoint accepts a JSON payload with the user's email.
    A reset token will be generated and sent to the provided email if the account exists.
    
    Example:
    ```json
    {
        "email": "user@example.com"
    }
    ```
    
    For security reasons, this endpoint always returns a success message,
    even if the email does not exist in the database.
    """
    # Check if the email exists in the database
    user = UserRepository.get_user_by_email(db, email=request.email)
    
    # Always return success, even if email doesn't exist (for security reasons)
    if not user:
        return {"message": "If the email exists, a password reset link will be sent"}
    
    # Create a password reset token
    token = create_password_reset_token(user.email)
    
    # Store the token in the database
    UserRepository.set_password_reset_token(db, user.email, token)
    
    # Import the necessary function for sending password reset emails
    from app.services.password_reset import send_password_reset_email
    
    # Send the password reset email
    await send_password_reset_email(
        background_tasks,
        username=user.name,
        email_to=user.email,
        token=token
    )
    
    return {"message": "If the email exists, a password reset link will be sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK,
            summary="Reset password",
            description="Reset password using a valid reset token")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset a user's password with a valid token.
    
    This endpoint accepts a JSON payload with:
    - email: The user's email address
    - token: The password reset token received via email
    - new_password: The new password to set
    
    Example:
    ```json
    {
        "email": "user@example.com",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "new_password": "mynewpassword123"
    }
    ```
    
    If the token is valid and not expired, the password will be updated.
    """
    try:
        # Verify token
        payload = jwt.decode(reset_data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_email = payload.get("sub")
        token_type = payload.get("type")
        
        if token_email != reset_data.email or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Verify token in database
    if not UserRepository.verify_password_reset_token(db, reset_data.email, reset_data.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Reset the password
    user = UserRepository.reset_password(db, reset_data.email, reset_data.new_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {"message": "Password has been reset successfully"} 