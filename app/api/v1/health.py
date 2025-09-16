"""Health check endpoints."""

from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.config import settings
from app.services.redis_service import redis_service

logger = structlog.get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    services: Dict[str, str]


async def check_redis_health() -> str:
    """Check Redis connection health."""
    try:
        # Try to ping Redis
        await redis_service.ping()
        return "healthy"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return "unhealthy"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint that verifies the status of the application and its dependencies.
    """
    redis_status = await check_redis_health()
    
    # Determine overall status
    overall_status = "healthy" if redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        environment=settings.environment,
        services={
            "redis": redis_status,
            "deepseek_api": "configured" if settings.deepseek_api_key else "not_configured"
        }
    )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe endpoint for Kubernetes or container orchestration.
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe endpoint for Kubernetes or container orchestration.
    Returns 200 if the application is ready to serve requests.
    """
    redis_status = await check_redis_health()
    
    if redis_status != "healthy":
        raise HTTPException(
            status_code=503,
            detail="Service not ready: Redis connection failed"
        )
    
    return {"status": "ready", "timestamp": datetime.utcnow()}