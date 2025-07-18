"""
Main FastAPI application module.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, create_tables, connect_database, disconnect_database
from app.api.health import router as health_router
from app.api.repositories import router as repositories_router
from app.services.llm_service import llm_service


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting GitHub Repository Monitor...")
    await connect_database()
    logger.info("Connected to database")
    await create_tables()
    logger.info("Database tables created/verified")
    
    # Initialize LLM service
    logger.info("Initializing LLM service...")
    llm_initialized = await llm_service.initialize()
    if llm_initialized:
        logger.info("LLM service initialized successfully")
    else:
        logger.warning("LLM service initialization failed - AI summaries will not be available")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GitHub Repository Monitor...")
    await disconnect_database()
    logger.info("Disconnected from database")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A comprehensive GitHub repository monitoring and analysis platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(repositories_router, prefix=settings.API_V1_STR, tags=["repositories"])

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main frontend page."""
    try:
        with open("frontend/index.html", "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>GitHub Repository Monitor</h1><p>Frontend not found</p>",
            status_code=200
        )


@app.get("/info")
async def get_app_info():
    """Get application information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "environment": "development" if settings.DEBUG else "production"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )