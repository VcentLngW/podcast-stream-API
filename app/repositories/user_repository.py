from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole


class UserRepository:
    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str):
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user_data: dict, verification_token: str = None):
        hashed_password = get_password_hash(user_data["password"])
        
        # Get role or default to LISTENER
        role = user_data.get("role", UserRole.LISTENER)
        is_creator = False
        
        # If role is CREATOR, set is_creator to True
        if role == UserRole.CREATOR:
            is_creator = True
        # If role is ADMIN, ensure is_creator is False
        elif role == UserRole.ADMIN:
            is_creator = False
            
        db_user = User(
            email=user_data["email"],
            username=user_data.get("username"),
            hashed_password=hashed_password,
            name=user_data.get("name"),
            is_active=True,  # Users are active by default
            is_verified=False,  # But require email verification
            verification_token=verification_token,
            role=role,
            is_creator=is_creator
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def verify_user(db: Session, email: str):
        user = UserRepository.get_user_by_email(db, email)
        
        if user:
            user.is_verified = True
            user.verification_token = None
            db.commit()
            db.refresh(user)
        
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: dict):
        user = UserRepository.get_user_by_id(db, user_id)
        
        if user:
            for key, value in user_data.items():
                if hasattr(user, key) and key != "id":
                    # Special handling for role changes
                    if key == "role":
                        # If changing to CREATOR, set is_creator to True
                        if value == UserRole.CREATOR:
                            user.is_creator = True
                        # If changing to ADMIN, ensure is_creator is False
                        elif value == UserRole.ADMIN:
                            user.is_creator = False
                    setattr(user, key, value)
            
            db.commit()
            db.refresh(user)
        
        return user
    
    @staticmethod
    def update_user_role(db: Session, user_id: int, role: UserRole, is_creator: bool = None):
        user = UserRepository.get_user_by_id(db, user_id)
        
        if user:
            user.role = role
            
            # Update is_creator based on role if not explicitly provided
            if is_creator is not None:
                user.is_creator = is_creator
            else:
                # If role is CREATOR, set is_creator to True
                if role == UserRole.CREATOR:
                    user.is_creator = True
                # If role is ADMIN, ensure is_creator is False
                elif role == UserRole.ADMIN:
                    user.is_creator = False
            
            db.commit()
            db.refresh(user)
        
        return user
        
    @staticmethod
    def set_password_reset_token(db: Session, email: str, token: str):
        """Store a password reset token for a user"""
        user = UserRepository.get_user_by_email(db, email)
        
        if user:
            user.password_reset_token = token
            # Set token expiration to 1 hour from now
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.commit()
            db.refresh(user)
            
        return user
    
    @staticmethod
    def verify_password_reset_token(db: Session, email: str, token: str):
        """Verify that a password reset token is valid"""
        user = UserRepository.get_user_by_email(db, email)
        
        if not user or user.password_reset_token != token:
            return False
            
        # Check if token has expired
        if not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
            return False
            
        return True
    
    @staticmethod
    def reset_password(db: Session, email: str, new_password: str):
        """Reset a user's password"""
        user = UserRepository.get_user_by_email(db, email)
        
        if user:
            user.hashed_password = get_password_hash(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            db.commit()
            db.refresh(user)
            
        return user 