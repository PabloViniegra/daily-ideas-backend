import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.redis_service import redis_service
from app.api.v1.projects import router as projects_router
from app.api.v1.health import router as health_router
from app.core.exceptions import ProjectServiceError, AIServiceError
from app.core.logging import setup_logging


setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle management for the application
    """
    # Startup
    logger.info("Starting up application")

    try:
        # Inicializar Redis
        await redis_service.initialize()
        logger.info("Redis initialized successfully")

        yield

    except Exception as e:
        logger.error("Failed to initialize application", error=str(e))
        raise

    finally:
        # Shutdown
        logger.info("Shutting down application")
        await redis_service.close()
        logger.info("Application shutdown complete")


# Crear instancia de FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for generating daily project ideas using AI",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None
)

# Middleware de CORS
if settings.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Middleware de seguridad para producción
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        # Configurar según dominios específicos en producción
        allowed_hosts=["*"]
    )

# Incluir routers
app.include_router(
    projects_router,
    prefix=settings.api_v1_str,
    tags=["projects"]
)

app.include_router(
    health_router,
    prefix=settings.api_v1_str,
    tags=["health"]
)


# Manejadores de excepciones globales
@app.exception_handler(ProjectServiceError)
async def project_service_exception_handler(request, exc: ProjectServiceError):
    """Handle project service errors"""
    logger.error("Project service error",
                 error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "service_error",
            "message": "Error interno del servicio de proyectos",
            "detail": str(exc) if settings.debug else None
        }
    )


@app.exception_handler(AIServiceError)
async def ai_service_exception_handler(request, exc: AIServiceError):
    """Handle AI service errors"""
    logger.error("AI service error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "error": "ai_service_error",
            "message": "El servicio de IA no está disponible temporalmente",
            "detail": str(exc) if settings.debug else None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unhandled exceptions"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Error interno del servidor",
            "detail": str(exc) if settings.debug else None
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Daily Projects API",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if not settings.is_production else "disabled",
        "status": "healthy"
    }


# HTTP request logging middleware (optional)
@app.middleware("http")
async def log_requests(request, call_next):
    """Log HTTP requests"""
    try:
        response = await call_next(request)

        logger.info(
            "Request completed",
            status_code=response.status_code,
            method=request.method,
            path=request.url.path
        )

        return response

    except Exception as exc:
        logger.error(
            "Request failed",
            error=str(exc),
            method=request.method,
            path=request.url.path
        )
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_config=None
    )
