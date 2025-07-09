"""
Health check API endpoints.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import logging

from app.config import settings
from app.database import db_manager
from app.services.llm_service import llm_service

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


async def check_huggingface_llm() -> ServiceStatus:
    """Check Hugging Face LLM service health."""
    start_time = time.time()
    try:
        # Get service status from LLM service
        service_status = await llm_service.get_service_status()
        response_time = (time.time() - start_time) * 1000
        
        if service_status.get("is_model_loaded") and service_status.get("model_healthy"):
            return ServiceStatus(
                status="healthy",
                response_time=response_time,
                details={
                    "model_name": service_status.get("model_name"),
                    "device": service_status.get("device"),
                    "max_length": service_status.get("max_length"),
                    "model_loaded": service_status.get("is_model_loaded"),
                    "model_healthy": service_status.get("model_healthy")
                }
            )
        else:
            return ServiceStatus(
                status="unhealthy",
                response_time=response_time,
                details={
                    "error": "Model not loaded or unhealthy",
                    "model_loaded": service_status.get("is_model_loaded", False),
                    "model_healthy": service_status.get("model_healthy", False)
                }
            )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Hugging Face LLM health check error: {e}")
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
        llm_task = asyncio.create_task(check_huggingface_llm())
        
        # Wait for all health checks to complete
        db_status, llm_status = await asyncio.gather(
            db_task, llm_task, return_exceptions=True
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
            
        if isinstance(llm_status, Exception):
            services["huggingface_llm"] = ServiceStatus(
                status="error",
                response_time=0,
                details={"error": str(llm_status)}
            )
        else:
            services["huggingface_llm"] = llm_status
        
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


@router.get("/health/llm")
async def llm_health():
    """Get detailed Hugging Face LLM service health information."""
    try:
        llm_status = await check_huggingface_llm()
        return {
            "service": "huggingface_llm",
            "timestamp": datetime.utcnow(),
            **llm_status.dict()
        }
    except Exception as e:
        logger.error(f"Hugging Face LLM health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hugging Face LLM health check failed: {str(e)}"
        )