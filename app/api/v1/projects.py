"""Project-related API endpoints."""

from typing import List, Optional
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.models.project import Project, ProjectCreateRequest, DifficultyLevel
from app.services.project_service import project_service
from app.core.exceptions import ProjectServiceError, AIServiceError, RateLimitError

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[Project])
async def get_projects(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. If not provided, uses today"),
    count: int = Query(5, ge=1, le=10, description="Number of projects to return"),
    force_regenerate: bool = Query(False, description="Force regeneration of projects")
):
    """
    Get projects for a specific date. If date is not provided, uses today.
    Projects are cached per date to ensure consistency.
    """
    try:
        logger.info("Fetching projects", date=date, count=count, force_regenerate=force_regenerate)

        projects = await project_service.get_projects_for_date(
            date=date,
            count=count,
            force_regenerate=force_regenerate
        )

        logger.info("Projects retrieved", project_count=len(projects))
        return projects

    except RateLimitError as e:
        logger.warning("Rate limit exceeded", error=str(e))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except AIServiceError as e:
        logger.error("AI service error", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except ProjectServiceError as e:
        logger.error("Project service error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error getting projects", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.get("/daily", response_model=List[Project])
async def get_daily_projects(
    force_regenerate: bool = Query(False, description="Force regeneration of daily projects"),
    count: int = Query(5, ge=1, le=10, description="Number of projects to return")
):
    """
    Get today's daily projects. If projects don't exist or force_regenerate is True,
    new projects will be generated.
    """
    try:
        logger.info("Fetching daily projects", count=count, force_regenerate=force_regenerate)
        
        projects = await project_service.get_daily_projects(
            force_regenerate=force_regenerate,
            count=count
        )
        
        logger.info("Daily projects retrieved", project_count=len(projects))
        return projects
        
    except RateLimitError as e:
        logger.warning("Rate limit exceeded", error=str(e))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except AIServiceError as e:
        logger.error("AI service error", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except ProjectServiceError as e:
        logger.error("Project service error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error getting daily projects", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.post("/generate", response_model=List[Project])
async def generate_projects(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate new projects based on the provided criteria.
    This endpoint allows for custom project generation with specific preferences.
    """
    try:
        logger.info(
            "Generating custom projects",
            count=request.count,
            difficulty_preference=request.difficulty_preference,
            category_preference=request.category_preference
        )
        
        projects = await project_service.generate_projects(
            count=request.count,
            difficulty_preference=request.difficulty_preference,
            category_preference=request.category_preference
        )
        
        # Cache the generated projects in the background
        background_tasks.add_task(
            project_service.cache_generated_projects,
            projects
        )
        
        logger.info("Custom projects generated", project_count=len(projects))
        return projects
        
    except RateLimitError as e:
        logger.warning("Rate limit exceeded for custom generation", error=str(e))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except AIServiceError as e:
        logger.error("AI service error during custom generation", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except ProjectServiceError as e:
        logger.error("Project service error during custom generation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error generating custom projects", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.get("/project/{project_id}", response_model=Project)
async def get_project_by_id(project_id: str):
    """
    Get a specific project by its ID.
    """
    try:
        logger.info("Fetching project by ID", project_id=project_id)
        
        project = await project_service.get_project_by_id(project_id)
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )
        
        logger.info("Project retrieved", project_id=project_id)
        return project
        
    except ProjectServiceError as e:
        logger.error("Project service error getting project by ID", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error getting project by ID", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.get("/stats")
async def get_project_stats():
    """
    Get statistics about generated projects.
    """
    try:
        logger.info("Fetching project statistics")
        
        stats = await project_service.get_stats()
        
        return {
            "total_projects_generated": stats.get("total_projects", 0),
            "daily_projects_available": stats.get("daily_projects_count", 0),
            "project_pool_size": stats.get("project_pool_size", 0),
            "last_generation_time": stats.get("last_generation_time"),
            "most_popular_difficulty": stats.get("most_popular_difficulty"),
            "most_popular_category": stats.get("most_popular_category")
        }
        
    except ProjectServiceError as e:
        logger.error("Project service error getting stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error getting project stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.delete("/cache")
async def clear_project_cache():
    """
    Clear the project cache. This will force regeneration of daily projects
    on the next request.
    """
    try:
        logger.info("Clearing project cache")
        
        await project_service.clear_cache()
        
        return JSONResponse(
            status_code=200,
            content={"message": "Project cache cleared successfully"}
        )
        
    except ProjectServiceError as e:
        logger.error("Project service error clearing cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error clearing cache", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.get("/pool/stats")
async def get_pool_stats():
    """
    Get statistics about the project pool.
    """
    try:
        logger.info("Fetching project pool statistics")

        pool_stats = await project_service.get_pool_stats()

        return {
            "pool_size": pool_stats.get("pool_size", 0),
            "pool_available": pool_stats.get("pool_available", False)
        }

    except ProjectServiceError as e:
        logger.error("Project service error getting pool stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error getting pool stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.delete("/pool")
async def clear_project_pool():
    """
    Clear the project pool. This will remove all projects from the pool.
    """
    try:
        logger.info("Clearing project pool")

        success = await project_service.clear_project_pool()

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear project pool"
            )

        return JSONResponse(
            status_code=200,
            content={"message": "Project pool cleared successfully"}
        )

    except ProjectServiceError as e:
        logger.error("Project service error clearing pool", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error clearing pool", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )


@router.post("/pool/seed")
async def seed_project_pool(
    background_tasks: BackgroundTasks,
    count: int = Query(10, ge=1, le=50, description="Number of projects to generate for the pool")
):
    """
    Seed the project pool with new projects. This generates projects specifically
    to populate the pool for random selection in daily endpoints.
    """
    try:
        logger.info("Seeding project pool", count=count)

        # Generate projects for the pool
        projects = await project_service.generate_projects(count=count)

        # Add to pool in the background
        background_tasks.add_task(
            project_service.add_projects_to_pool,
            projects
        )

        logger.info("Project pool seeded", count=len(projects))
        return {
            "message": f"Successfully generated {len(projects)} projects for the pool",
            "projects_generated": len(projects)
        }

    except RateLimitError as e:
        logger.warning("Rate limit exceeded for pool seeding", error=str(e))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    except AIServiceError as e:
        logger.error("AI service error during pool seeding", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except ProjectServiceError as e:
        logger.error("Project service error during pool seeding", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal project service error."
        )
    except Exception as e:
        logger.error("Unexpected error seeding pool", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred."
        )