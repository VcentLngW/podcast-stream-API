import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer

from app.api import auth, users, testing, podcasts, categories, stream
from app.core.config import settings
from app.db.database import Base, engine

# Create security scheme
security = HTTPBearer()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI application with JWT authentication, MySQL, and email verification",
    # Add security scheme directly to FastAPI
    openapi_tags=[
        {"name": "auth", "description": "Authentication operations"},
        {"name": "users", "description": "User operations"},
        {"name": "podcasts", "description": "Podcast operations"},
        {"name": "categories", "description": "Podcast category operations"},
        {"name": "stream", "description": "Streaming operations"},
        {"name": "testing", "description": "Testing endpoints"}
    ],
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(podcasts.router, prefix="/api")
app.include_router(categories.router)  # Categories router already includes /api prefix
app.include_router(stream.router, prefix="/api")  # Include stream router
app.include_router(testing.router)  # Testing router already includes /api prefix in its definition


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app_name": settings.APP_NAME} 