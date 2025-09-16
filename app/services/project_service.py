"""
Servicio principal para lógica de negocio de proyectos
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import structlog

from app.config import settings
from app.models.project import Project, DifficultyLevel, ProjectCreateRequest
from app.services.redis_service import redis_service
from app.services.ai_service import ai_service, AIServiceError
from app.core.exceptions import ProjectServiceError, RateLimitError


logger = structlog.get_logger(__name__)




class ProjectService:
    """Service for project management"""

    def __init__(self):
        self.redis = redis_service
        self.ai = ai_service

    async def get_daily_projects(self, date: Optional[str] = None, force_regenerate: bool = False, count: int = 5) -> List[Project]:
        """
        Get daily projects, generating them if they don't exist

        Args:
            date: Date in YYYY-MM-DD format, default today
            force_regenerate: Force regeneration even if cached projects exist
            count: Number of projects to return (1-10)

        Returns:
            List of daily projects

        Raises:
            ProjectServiceError: If projects cannot be retrieved/generated
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            # Check for rate limiting
            await self._check_rate_limit()
            
            if not force_regenerate:
                projects = await self.redis.get_daily_projects(date)
                if projects and len(projects) >= count:
                    logger.info("Retrieved existing projects for date",
                                date=date, count=len(projects))
                    return projects[:count]
                elif projects and len(projects) < count:
                    # We have some projects but not enough, supplement from pool
                    logger.info("Insufficient cached projects, supplementing from pool",
                              cached=len(projects), needed=count - len(projects))

                    pool_projects = await self.redis.get_random_projects_from_pool(count - len(projects))

                    # Combine cached and pool projects
                    combined_projects = projects + pool_projects

                    # If we still don't have enough, generate more
                    if len(combined_projects) < count:
                        logger.info("Still insufficient projects, generating additional",
                                  have=len(combined_projects), need=count)
                        additional_needed = count - len(combined_projects)
                        new_projects = await self.generate_daily_projects(date, additional_needed)
                        combined_projects.extend(new_projects)

                    return combined_projects[:count]

            logger.info(
                "No existing projects found or force regeneration, generating new ones",
                date=date, force_regenerate=force_regenerate)

            # Try to get from pool first
            if not force_regenerate:
                pool_projects = await self.redis.get_random_projects_from_pool(count)
                if len(pool_projects) >= count:
                    logger.info("Got sufficient projects from pool", count=len(pool_projects))
                    return pool_projects[:count]
                elif pool_projects:
                    logger.info("Got partial projects from pool, generating remaining",
                              pool_count=len(pool_projects), need_more=count - len(pool_projects))
                    additional_projects = await self.generate_daily_projects(date, count - len(pool_projects))
                    combined = pool_projects + additional_projects
                    return combined[:count]

            return await self.generate_daily_projects(date, count)

        except Exception as e:
            logger.error("Failed to get daily projects",
                         date=date, error=str(e))
            raise ProjectServiceError(f"Error obteniendo proyectos: {str(e)}")

    async def generate_daily_projects(self, date: Optional[str] = None, count: int = 5) -> List[Project]:
        """
        Generate new projects for a specific date

        Args:
            date: Date in YYYY-MM-DD format, default today

        Returns:
            List of generated projects

        Raises:
            ProjectServiceError: If projects cannot be generated
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        if await self.redis.is_generation_locked(date):
            logger.info("Generation already in progress, waiting", date=date)

            for attempt in range(6):
                await asyncio.sleep(5)
                projects = await self.redis.get_daily_projects(date)
                if projects:
                    logger.info("Found projects after waiting",
                                date=date, attempt=attempt + 1)
                    return projects

            logger.warning(
                "Timeout waiting for generation, proceeding anyway", date=date)

        lock_set = await self.redis.set_generation_lock(date)
        if not lock_set:
            return await self._wait_for_generation(date)

        try:
            logger.info("Starting project generation", date=date)
            projects = await self._generate_with_ai(date, count)

            for i, project in enumerate(projects):
                project.id = f"{date}-{i+1}"

            success = await self.redis.set_daily_projects(date, projects)
            if not success:
                logger.error("Failed to save generated projects", date=date)
                raise ProjectServiceError(
                    "No se pudieron guardar los proyectos generados")

            logger.info("Successfully generated and saved projects",
                        date=date, count=len(projects))
            return projects

        except Exception as e:
            logger.error("Failed to generate projects",
                         date=date, error=str(e))

            try:
                fallback_projects = await self._get_fallback_projects(date)
                await self.redis.set_daily_projects(date, fallback_projects)
                logger.info("Using fallback projects", date=date)
                return fallback_projects
            except Exception as fallback_error:
                logger.error("Fallback also failed", date=date,
                             error=str(fallback_error))
                raise ProjectServiceError(
                    "No se pudieron generar proyectos ni usar fallback")

        finally:
            await self.redis.release_generation_lock(date)

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """
        Get a specific project by its ID

        Args:
            project_id: ID del proyecto en formato YYYY-MM-DD-N

        Returns:
            Proyecto encontrado o None
        """
        try:
            parts = project_id.split('-')
            if len(parts) < 4:
                logger.warning("Invalid project ID format",
                               project_id=project_id)
                return None

            date = '-'.join(parts[:3])

            projects = await self.get_daily_projects(date)

            for project in projects:
                if project.id == project_id:
                    return project

            logger.info("Project not found", project_id=project_id)
            return None

        except Exception as e:
            logger.error("Failed to get project by ID",
                         project_id=project_id, error=str(e))
            return None

    async def get_projects_archive(self, days: int = 7) -> List[dict]:
        """
        Get projects archive for previous days

        Args:
            days: Number of previous days to retrieve

        Returns:
            List of dictionaries with date and projects
        """
        archive = []
        today = datetime.now()

        for i in range(1, min(days + 1, 30)):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")

            try:
                projects = await self.redis.get_daily_projects(date)
                if projects:
                    archive.append({
                        "date": date,
                        "projects": [p.model_dump() for p in projects[:3]],
                        "total": len(projects)
                    })
            except Exception as e:
                logger.warning("Failed to get archive for date",
                               date=date, error=str(e))
                continue

        return archive

    async def generate_custom_projects(self, request: ProjectCreateRequest) -> List[Project]:
        """
        Generate custom projects based on specific parameters

        Args:
            request: Request parameters

        Returns:
            List of generated projects
        """
        try:
            projects = await ai_service.generate_projects(
                count=request.count,
                difficulty_preference=request.difficulty_preference,
                category_preference=request.category_preference
            )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            for i, project in enumerate(projects):
                project.id = f"custom-{timestamp}-{i+1}"

            logger.info("Generated custom projects", count=len(projects))
            return projects

        except AIServiceError as e:
            logger.error("AI service error in custom generation", error=str(e))
            raise ProjectServiceError(
                f"Error generando proyectos personalizados: {str(e)}")
        except Exception as e:
            logger.error("Unexpected error in custom generation", error=str(e))
            raise ProjectServiceError(
                "Error inesperado generando proyectos personalizados")

    async def _generate_with_ai(self, date: str, count: int = 5) -> List[Project]:
        """
        Generate projects using the AI service

        Args:
            date: Fecha para contextualizar la generación
            count: Number of projects to generate

        Returns:
            Lista de proyectos generados
        """
        try:
            difficulty_distribution = [
                DifficultyLevel.BEGINNER,
                DifficultyLevel.INTERMEDIATE,
                DifficultyLevel.INTERMEDIATE,
                DifficultyLevel.ADVANCED,
                DifficultyLevel.ADVANCED
            ]

            projects = await ai_service.generate_projects(
                count=count,
                difficulty_preference=difficulty_distribution
            )

            return projects

        except AIServiceError as e:
            logger.error("AI service failed", date=date, error=str(e))
            raise ProjectServiceError(f"Servicio de IA falló: {str(e)}")

    async def _wait_for_generation(self, date: str, max_wait: int = 30) -> List[Project]:
        """
        Wait for the generation to complete

        Args:
            date: Date to wait for
            max_wait: Maximum wait time in seconds

        Returns:
            List of projects once generated
        """
        for attempt in range(max_wait // 5):
            await asyncio.sleep(5)

            projects = await self.redis.get_daily_projects(date)
            if projects:
                logger.info("Found projects after waiting",
                            date=date, attempt=attempt + 1)
                return projects

        # Si no se encontraron después de esperar, generar fallback
        logger.warning(
            "Timeout waiting for generation, using fallback", date=date)
        return await self._get_fallback_projects(date)

    async def _get_fallback_projects(self, date: str) -> List[Project]:
        """
        Get fallback projects when AI fails

        Args:
            date: Date for fallback

        Returns:
            List of fallback projects
        """
        fallback_data = [
            {
                "title": "Todo List con Dark Mode",
                "description": "Una aplicación de tareas pendientes con interfaz moderna, modo oscuro automático y sincronización local. Perfecta para aprender gestión de estado y persistencia de datos.",
                "difficulty": "beginner",
                "estimated_time": "1-2 días",
                "category": "Web Application",
                "technologies": [
                    {"name": "React", "type": "frontend",
                        "reason": "Componentes reutilizables y hooks para estado"},
                    {"name": "localStorage", "type": "database",
                        "reason": "Persistencia simple sin backend"},
                    {"name": "CSS Modules", "type": "tool",
                        "reason": "Estilos encapsulados y mantenibles"}
                ],
                "features": ["Agregar/eliminar tareas", "Modo oscuro", "Filtros por estado", "Persistencia local", "Animaciones suaves"]
            },
            {
                "title": "Weather Dashboard",
                "description": "Dashboard meteorológico que muestra el clima actual y pronóstico de múltiples ciudades con gráficos interactivos y geolocalización automática.",
                "difficulty": "intermediate",
                "estimated_time": "3-4 días",
                "category": "Data Visualization",
                "technologies": [
                    {"name": "Vue.js", "type": "frontend",
                        "reason": "Reactividad para actualizaciones de datos en tiempo real"},
                    {"name": "Chart.js", "type": "library",
                        "reason": "Gráficos interactivos para visualizar datos meteorológicos"},
                    {"name": "OpenWeather API", "type": "tool",
                        "reason": "Datos meteorológicos precisos y actualizados"}
                ],
                "features": ["Geolocalización automática", "Búsqueda de ciudades", "Gráficos de temperatura", "Pronóstico 5 días", "Diseño responsive"]
            },
            {
                "title": "E-commerce Product Filter",
                "description": "Sistema de filtros avanzado para productos en línea con búsqueda en tiempo real, filtros por categorías, precio y ratings con animaciones suaves.",
                "difficulty": "intermediate",
                "estimated_time": "4-5 días",
                "category": "E-commerce",
                "technologies": [
                    {"name": "Next.js", "type": "framework",
                        "reason": "SSR y optimización automática para mejor rendimiento"},
                    {"name": "MongoDB", "type": "database",
                        "reason": "Base de datos flexible para productos con diferentes atributos"},
                    {"name": "Tailwind CSS", "type": "framework",
                        "reason": "Estilos utility-first para desarrollo rápido"}
                ],
                "features": ["Búsqueda en tiempo real", "Filtros múltiples", "Ordenamiento dinámico", "Paginación infinita", "Favoritos de usuario"]
            },
            {
                "title": "Personal Finance Tracker",
                "description": "Aplicación para seguimiento de gastos personales con categorización automática, presupuestos y reportes visuales con gráficos interactivos.",
                "difficulty": "advanced",
                "estimated_time": "1-2 semanas",
                "category": "Finance",
                "technologies": [
                    {"name": "Python", "type": "backend",
                        "reason": "Excelente para análisis de datos y cálculos financieros"},
                    {"name": "FastAPI", "type": "framework",
                        "reason": "API rápida con validación automática de datos"},
                    {"name": "PostgreSQL", "type": "database",
                        "reason": "Base de datos robusta para datos financieros críticos"},
                    {"name": "D3.js", "type": "library",
                        "reason": "Visualizaciones personalizadas y interactivas"}
                ],
                "features": ["Categorización automática", "Presupuestos inteligentes", "Reportes exportables", "Alertas personalizadas", "Análisis de tendencias"]
            },
            {
                "title": "URL Shortener with Analytics",
                "description": "Servicio de acortamiento de URLs con panel de analytics, estadísticas de clics, geolocalización y códigos QR generados automáticamente.",
                "difficulty": "beginner",
                "estimated_time": "2-3 días",
                "category": "Web Service",
                "technologies": [
                    {"name": "Node.js", "type": "backend",
                        "reason": "Ideal para servicios web ligeros y rápidos"},
                    {"name": "Express.js", "type": "framework",
                        "reason": "Framework minimalista para APIs REST"},
                    {"name": "Redis", "type": "database",
                        "reason": "Cache rápido para URLs y estadísticas"}
                ],
                "features": ["URLs personalizadas", "Analytics en tiempo real", "Generación de QR", "Expiración programada", "API RESTful"]
            },
            {
                "title": "Recipe Finder with AI",
                "description": "Buscador de recetas inteligente que sugiere platos basados en ingredientes disponibles, restricciones dietéticas y preferencias personales.",
                "difficulty": "advanced",
                "estimated_time": "2-3 semanas",
                "category": "AI Application",
                "technologies": [
                    {"name": "React", "type": "frontend",
                        "reason": "Interfaz interactiva para búsqueda y filtros complejos"},
                    {"name": "OpenAI API", "type": "tool",
                        "reason": "IA para sugerencias inteligentes y análisis nutricional"},
                    {"name": "Elasticsearch", "type": "database",
                        "reason": "Búsqueda avanzada y filtrado de recetas"},
                    {"name": "Docker", "type": "tool",
                        "reason": "Containerización para deployment sencillo"}
                ],
                "features": ["Sugerencias por ingredientes", "Análisis nutricional", "Lista de compras automática", "Planificador de comidas", "Recomendaciones personalizadas"]
            }
        ]

        projects = []
        timestamp = datetime.now()

        for i, data in enumerate(fallback_data[:5]):
            project = Project.model_validate(data)
            project.id = f"{date}-fallback-{i+1}"
            project.generated_at = timestamp
            projects.append(project)

        logger.info("Created fallback projects",
                    date=date, count=len(projects))
        return projects

    async def generate_projects(self, count: int = 5, 
                               difficulty_preference: Optional[List[DifficultyLevel]] = None,
                               category_preference: Optional[str] = None) -> List[Project]:
        """
        Generate projects with custom parameters
        """
        try:
            await self._check_rate_limit()
            
            projects = await ai_service.generate_projects(
                count=count,
                difficulty_preference=difficulty_preference,
                category_preference=category_preference
            )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            for i, project in enumerate(projects):
                project.id = f"custom-{timestamp}-{i+1}"
                project.generated_at = datetime.now()

            logger.info("Generated custom projects", count=len(projects))
            return projects

        except AIServiceError as e:
            logger.error("AI service error in custom generation", error=str(e))
            
            # Try fallback when AI service fails
            try:
                logger.info("Using fallback projects for custom generation", count=count)
                fallback_projects = await self._get_fallback_projects("custom")
                
                # Limit to requested count and customize IDs
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                selected_projects = fallback_projects[:count]
                
                for i, project in enumerate(selected_projects):
                    project.id = f"custom-{timestamp}-{i+1}"
                    project.generated_at = datetime.now()
                
                logger.info("Successfully provided fallback projects", count=len(selected_projects))
                return selected_projects
                
            except Exception as fallback_error:
                logger.error("Fallback also failed for custom generation", error=str(fallback_error))
                raise ProjectServiceError(f"Error generando proyectos personalizados: {str(e)}")
            
        except Exception as e:
            logger.error("Unexpected error in custom generation", error=str(e))
            raise ProjectServiceError("Error inesperado generando proyectos personalizados")

    async def cache_generated_projects(self, projects: List[Project]):
        """Cache generated projects for future reference and add to pool"""
        try:
            # Add projects to the general pool for random selection
            await self.redis.add_projects_to_pool(projects)
            logger.info("Added generated projects to pool", count=len(projects))

            # Also cache in the traditional way for compatibility
            cache_key = f"generated:{datetime.now().strftime('%Y-%m-%d-%H')}"
            await self.redis.set_projects_with_ttl(cache_key, projects, ttl=3600)  # 1 hour
            logger.info("Cached generated projects", key=cache_key, count=len(projects))
        except Exception as e:
            logger.warning("Failed to cache generated projects", error=str(e))

    async def get_stats(self) -> dict:
        """Get project statistics"""
        try:
            stats = {}
            today = datetime.now().strftime("%Y-%m-%d")

            # Get today's projects count
            today_projects = await self.redis.get_daily_projects(today)
            stats["daily_projects_count"] = len(today_projects) if today_projects else 0

            # Get project pool statistics
            pool_size = await self.redis.get_pool_size()
            stats["project_pool_size"] = pool_size

            # Calculate total available projects
            stats["total_projects"] = stats["daily_projects_count"] + pool_size
            stats["last_generation_time"] = datetime.now().isoformat() if today_projects else None
            stats["most_popular_difficulty"] = "intermediate"  # Could be enhanced to analyze pool
            stats["most_popular_category"] = "Web Development"  # Could be enhanced to analyze pool

            return stats
        except Exception as e:
            logger.error("Error getting stats", error=str(e))
            return {}

    async def clear_cache(self):
        """Clear project cache"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            await self.redis.clear_daily_projects(today)
            logger.info("Cleared project cache", date=today)
        except Exception as e:
            logger.error("Error clearing cache", error=str(e))
            raise ProjectServiceError("Error clearing cache")

    async def add_projects_to_pool(self, projects: List[Project]) -> bool:
        """Add projects directly to the pool"""
        try:
            return await self.redis.add_projects_to_pool(projects)
        except Exception as e:
            logger.error("Error adding projects to pool", error=str(e))
            return False

    async def get_pool_stats(self) -> dict:
        """Get pool-specific statistics"""
        try:
            pool_size = await self.redis.get_pool_size()
            return {
                "pool_size": pool_size,
                "pool_available": pool_size > 0
            }
        except Exception as e:
            logger.error("Error getting pool stats", error=str(e))
            return {"pool_size": 0, "pool_available": False}

    async def clear_project_pool(self) -> bool:
        """Clear the entire project pool"""
        try:
            return await self.redis.clear_project_pool()
        except Exception as e:
            logger.error("Error clearing project pool", error=str(e))
            return False

    async def get_projects_for_date(self, date: Optional[str] = None, count: int = 5, force_regenerate: bool = False) -> List[Project]:
        """
        Get projects for a specific date (alias for get_daily_projects for API consistency)

        Args:
            date: Date in YYYY-MM-DD format, default today
            count: Number of projects to return (1-10)
            force_regenerate: Force regeneration even if cached projects exist

        Returns:
            List of projects for the specified date
        """
        return await self.get_daily_projects(date=date, force_regenerate=force_regenerate, count=count)

    async def _check_rate_limit(self):
        """Check if rate limit is exceeded"""
        try:
            # Simple rate limiting implementation
            # This should be implemented in Redis service
            pass  # For now, no rate limiting
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            raise RateLimitError("Rate limit check failed")


project_service = ProjectService()
