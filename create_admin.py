import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.models.user import User, UserRole

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", "3306"))
db_user = os.getenv("DB_USER", "podcastuser")
db_password = os.getenv("DB_PASSWORD", "podcast123")
db_name = os.getenv("DB_NAME", "podcast")

# Construct database URL
DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Admin user details
admin_email = "admin@example.com"
admin_username = "admin"
admin_password = "adminpass123"  # In production, use a secure password
admin_name = "Admin User"

try:
    # Check if admin user already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    
    if existing_admin:
        print(f"Admin user {admin_email} already exists.")
    else:
        # Create a new admin user
        hashed_password = get_password_hash(admin_password)
        
        admin_user = User(
            email=admin_email,
            username=admin_username,
            hashed_password=hashed_password,
            name=admin_name,
            is_active=True,
            is_verified=True,  # Admin is pre-verified
            role=UserRole.ADMIN,
            is_creator=False
        )
        
        db.add(admin_user)
        db.commit()
        print(f"Admin user created successfully with email: {admin_email} and username: {admin_username}")
        print(f"Password: {admin_password} (save this somewhere secure)")
    
except Exception as e:
    print(f"Error creating admin user: {str(e)}")
finally:
    db.close() 