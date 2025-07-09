"""
Health check API endpoints.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import redis
import httpx
import logging

from app.config import settings
from app.database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    uptime: float
    services: Dict[str, Any]


class ServiceStatus(BaseModel):
    """Individual service status model."""
    status: str
    response_time: float
    details: Dict[str, Any] = {}


# Store application start time for uptime calculation
app_start_time = time.time()


async def check_database() -> ServiceStatus:
    """Check database connectivity and health."""
    start_time = time.time()
    try:
        is_healthy = await db_manager.health_check()
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if is_healthy:
            connection_info = await db_manager.get_connection_info()
            return ServiceStatus(
                status="healthy",
                response_time=response_time,
                details=connection_info
            )
        else:
            return ServiceStatus(
                status="unhealthy",
                response_time=response_time,
                details={"error": "Database health check failed"}
            )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Database health check error: {e}")
        return ServiceStatus(
            status="unhealthy",
            response_time=response_time,
            details={"error": str(e)}
        )


async def check_redis() -> ServiceStatus:
    """Check Redis connectivity and health."""
    start_time = time.time()
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await asyncio.get_event_loop().run_in_executor(None, redis_client.ping)
        response_time = (time.time() - start_time) * 1000
        
        # Get Redis info
        info = await asyncio.get_event_loop().run_in_executor(None, redis_client.info)
        redis_client.close()
        
        return ServiceStatus(
            status="healthy",
            response_time=response_time,
            details={
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown")
            }
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Redis health check error: {e}")
        return ServiceStatus(
            status="unhealthy",
            response_time=response_time,
            details={"error": str(e)}
        )


async def check_ollama() -> ServiceStatus:
    """Check Ollama service connectivity and health."""
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return ServiceStatus(
                    status="healthy",
                    response_time=response_time,
                    details={
                        "url": settings.OLLAMA_URL,
                        "available_models": len(models),
                        "models": [model.get("name", "unknown") for model in models[:5]]  # Show first 5
                    }
                )
            else:
                return ServiceStatus(
                    status="unhealthy",
                    response_time=response_time,
                    details={"error": f"HTTP {response.status_code}"}
                )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Ollama health check error: {e}")
        return ServiceStatus(
            status="unhealthy",
            response_time=response_time,
            details={"error": str(e)}
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns the health status of the application and all its dependencies.
    """
    try:
        # Calculate uptime
        uptime = time.time() - app_start_time
        
        # Check all services concurrently
        db_task = asyncio.create_task(check_database())
        redis_task = asyncio.create_task(check_redis())
        ollama_task = asyncio.create_task(check_ollama())
        
        # Wait for all health checks to complete
        db_status, redis_status, ollama_status = await asyncio.gather(
            db_task, redis_task, ollama_task, return_exceptions=True
        )
        
        # Handle any exceptions from the health checks
        services = {}
        
        if isinstance(db_status, Exception):
            services["database"] = ServiceStatus(
                status="error",
                response_time=0,
                details={"error": str(db_status)}
            )
        else:
            services["database"] = db_status
            
        if isinstance(redis_status, Exception):
            services["redis"] = ServiceStatus(
                status="error",
                response_time=0,
                details={"error": str(redis_status)}
            )
        else:
            services["redis"] = redis_status
            
        if isinstance(ollama_status, Exception):
            services["ollama"] = ServiceStatus(
                status="error",
                response_time=0,
                details={"error": str(ollama_status)}
            )
        else:
            services["ollama"] = ollama_status
        
        # Determine overall status
        all_healthy = all(
            service.status == "healthy" 
            for service in services.values()
        )
        overall_status = "healthy" if all_healthy else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.APP_VERSION,
            uptime=uptime,
            services=services
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    
    Returns a simple OK response to indicate the application is running.
    """
    return {"status": "ok", "timestamp": datetime.utcnow()}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to serve traffic.
    """
    try:
        # Check critical services only (database)
        db_status = await check_database()
        
        if db_status.status == "healthy":
            return {
                "status": "ready",
                "timestamp": datetime.utcnow(),
                "database": db_status.dict()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Application not ready - database unavailable"
            )
            
    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Application not ready: {str(e)}"
        )


@router.get("/health/database")
async def database_health():
    """Get detailed database health information."""
    try:
        db_status = await check_database()
        return {
            "service": "database",
            "timestamp": datetime.utcnow(),
            **db_status.dict()
        }
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/health/redis")
async def redis_health():
    """Get detailed Redis health information."""
    try:
        redis_status = await check_redis()
        return {
            "service": "redis",
            "timestamp": datetime.utcnow(),
            **redis_status.dict()
        }
    except Exception as e:
        logger.error(f"Redis health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Redis health check failed: {str(e)}"
        )


@router.get("/health/ollama")
async def ollama_health():
    """Get detailed Ollama service health information."""
    try:
        ollama_status = await check_ollama()
        return {
            "service": "ollama",
            "timestamp": datetime.utcnow(),
            **ollama_status.dict()
        }
    except Exception as e:
        logger.error(f"Ollama health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama health check failed: {str(e)}"
        )