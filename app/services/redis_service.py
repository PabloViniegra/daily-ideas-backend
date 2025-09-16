import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
import structlog

from app.config import settings
from app.models.project import Project

logger = structlog.get_logger(__name__)


class RedisService:
    """Singleton service for Redis operations."""
    _instance: Optional["RedisService"] = None
    _redis_pool: Optional[redis.ConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._redis: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize connection to Redis"""
        try:
            if self._redis_pool is None:
                self._redis_pool = redis.ConnectionPool.from_url(
                    settings.redis_url,
                    db=settings.redis_db,
                    max_connections=settings.redis_max_connections,
                    retry_on_timeout=settings.redis_retry_on_timeout,
                    decode_responses=True
                )

            self._redis = redis.Redis(connection_pool=self._redis_pool)

            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established successfully")

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise ConnectionError(f"Could not connect to Redis: {e}")

    async def close(self):
        """Close connection to Redis"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    @asynccontextmanager
    async def get_redis(self):
        """Context manager para obtener instancia de Redis"""
        if not self._redis:
            await self.initialize()

        try:
            yield self._redis
        except Exception as e:
            logger.error("Redis operation failed", error=str(e))
            raise

    async def get_daily_projects(self, date: str) -> Optional[List[Project]]:
        """
        Get daily projects from Redis

        Args:
            date: Date in format YYYY-MM-DD

        Returns:
            List of projects or None if not found
        """
        async with self.get_redis() as redis_client:
            try:
                key = self._get_daily_projects_key(date)
                data = await redis_client.get(key)

                if not data:
                    logger.info("No projects found for date", date=date)
                    return None

                projects_data = json.loads(data)
                projects = [Project.parse_obj(project_data)
                            for project_data in projects_data]

                logger.info("Retrieved daily projects",
                            date=date, count=len(projects))
                return projects

            except json.JSONDecodeError as e:
                logger.error("Failed to decode projects JSON",
                             date=date, error=str(e))
                return None
            except Exception as e:
                logger.error("Failed to get daily projects",
                             date=date, error=str(e))
                return None

    async def set_daily_projects(self, date: str, projects: List[Project]) -> bool:
        """
        Set daily projects in Redis with TTL

        Args:
            date: Date in format YYYY-MM-DD
            projects: List of projects to save

        Returns:
            True if saved successfully, False otherwise
        """
        async with self.get_redis() as redis_client:
            try:
                key = self._get_daily_projects_key(date)

                # Serializar proyectos
                projects_data = [project.model_dump() for project in projects]
                json_data = json.dumps(
                    projects_data, ensure_ascii=False, default=str)

                # Guardar con TTL
                await redis_client.setex(
                    key,
                    settings.daily_projects_ttl,
                    json_data
                )

                logger.info("Saved daily projects",
                            date=date, count=len(projects))
                return True

            except Exception as e:
                logger.error("Failed to save daily projects",
                             date=date, error=str(e))
                return False

    async def is_generation_locked(self, date: str) -> bool:
        """
        Check if generation is locked for a date

        Args:
            date: Date in format YYYY-MM-DD

        Returns:
            True if locked, False otherwise
        """
        async with self.get_redis() as redis_client:
            try:
                lock_key = self._get_generation_lock_key(date)
                exists = await redis_client.exists(lock_key)
                return bool(exists)

            except Exception as e:
                logger.error("Failed to check generation lock",
                             date=date, error=str(e))
                return False

    async def set_generation_lock(self, date: str) -> bool:
        """
        Set generation lock for a date

        Args:
            date: Date in format YYYY-MM-DD

        Returns:
            True if lock was set, False if it already existed or an error occurred
        """
        async with self.get_redis() as redis_client:
            try:
                lock_key = self._get_generation_lock_key(date)

                # Use SET with NX (not exists) to avoid overwriting
                result = await redis_client.set(
                    lock_key,
                    "locked",
                    ex=settings.generation_lock_ttl,
                    nx=True  # Only set if it doesn't exist
                )

                if result:
                    logger.info("Generation lock set", date=date)
                    return True
                else:
                    logger.info("Generation lock already exists", date=date)
                    return False

            except Exception as e:
                logger.error("Failed to set generation lock",
                             date=date, error=str(e))
                return False

    async def release_generation_lock(self, date: str) -> bool:
        """
        Release generation lock for a date

        Args:
            date: Date in format YYYY-MM-DD

        Returns:
            True if lock was released, False if it didn't exist or an error occurred
        """
        async with self.get_redis() as redis_client:
            try:
                lock_key = self._get_generation_lock_key(date)
                result = await redis_client.delete(lock_key)

                if result:
                    logger.info("Generation lock released", date=date)
                    return True
                else:
                    logger.info(
                        "No generation lock found to release", date=date)
                    return False

            except Exception as e:
                logger.error("Failed to release generation lock",
                             date=date, error=str(e))
                return False

    async def increment_api_calls(self, endpoint: str) -> int:
        """
        Increment API calls counter

        Args:
            endpoint: Endpoint name

        Returns:
            New counter value
        """
        async with self.get_redis() as redis_client:
            try:
                key = f"api_calls:{endpoint}:{datetime.now().strftime('%Y-%m-%d')}"
                count = await redis_client.incr(key)

                # Set TTL of 7 days for daily stats
                if count == 1:  # First time the key is created
                    await redis_client.expire(key, 86400 * 7)

                return count

            except Exception as e:
                logger.error("Failed to increment API calls",
                             endpoint=endpoint, error=str(e))
                return 0

    async def get_health_info(self) -> Dict[str, Any]:
        """
        Get Redis health information

        Returns:
            Dictionary with connection and statistics information
        """
        async with self.get_redis() as redis_client:
            try:
                info = await redis_client.info()
                ping_result = await redis_client.ping()

                return {
                    "connected": ping_result,
                    "version": info.get("redis_version", "unknown"),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0)
                }

            except Exception as e:
                logger.error("Failed to get Redis health info", error=str(e))
                return {"connected": False, "error": str(e)}

    async def ping(self) -> bool:
        """Ping Redis to check connection"""
        async with self.get_redis() as redis_client:
            try:
                result = await redis_client.ping()
                return result
            except Exception as e:
                logger.error("Redis ping failed", error=str(e))
                return False

    async def clear_daily_projects(self, date: str) -> bool:
        """Clear daily projects for a specific date"""
        async with self.get_redis() as redis_client:
            try:
                key = self._get_daily_projects_key(date)
                result = await redis_client.delete(key)
                logger.info("Cleared daily projects", date=date, deleted=bool(result))
                return bool(result)
            except Exception as e:
                logger.error("Failed to clear daily projects", date=date, error=str(e))
                return False

    async def set_projects_with_ttl(self, key: str, projects: List[Project], ttl: int) -> bool:
        """Set projects with a TTL"""
        async with self.get_redis() as redis_client:
            try:
                projects_data = [p.model_dump() for p in projects]
                serialized_data = json.dumps(projects_data, default=str)
                
                result = await redis_client.setex(
                    key, 
                    ttl, 
                    serialized_data
                )
                
                logger.info("Set projects with TTL", key=key, ttl=ttl, count=len(projects))
                return bool(result)
                
            except Exception as e:
                logger.error("Failed to set projects with TTL", key=key, error=str(e))
                return False

    async def add_projects_to_pool(self, projects: List[Project]) -> bool:
        """
        Add projects to the general project pool for random selection

        Args:
            projects: List of projects to add to the pool

        Returns:
            True if projects were successfully added
        """
        async with self.get_redis() as redis_client:
            try:
                pool_key = "project_pool"

                # Serialize projects and add to a Redis list
                for project in projects:
                    project_data = json.dumps(project.model_dump(), default=str)
                    await redis_client.lpush(pool_key, project_data)

                # Set TTL for the pool (7 days)
                await redis_client.expire(pool_key, 86400 * 7)

                logger.info("Added projects to pool", count=len(projects))
                return True

            except Exception as e:
                logger.error("Failed to add projects to pool", error=str(e))
                return False

    async def get_random_projects_from_pool(self, count: int = 5) -> List[Project]:
        """
        Get random projects from the project pool

        Args:
            count: Number of projects to retrieve

        Returns:
            List of random projects from the pool
        """
        async with self.get_redis() as redis_client:
            try:
                pool_key = "project_pool"

                # Get total number of projects in pool
                pool_size = await redis_client.llen(pool_key)

                if pool_size == 0:
                    logger.info("Project pool is empty")
                    return []

                projects = []
                selected_indices = set()

                # Randomly select projects from the pool
                import random
                for _ in range(min(count, pool_size)):
                    # Find an unused random index
                    while True:
                        random_index = random.randint(0, pool_size - 1)
                        if random_index not in selected_indices:
                            selected_indices.add(random_index)
                            break

                    # Get project at random index
                    project_data = await redis_client.lindex(pool_key, random_index)
                    if project_data:
                        try:
                            project_dict = json.loads(project_data)
                            project = Project.model_validate(project_dict)
                            projects.append(project)
                        except Exception as e:
                            logger.warning("Failed to parse project from pool", error=str(e))
                            continue

                logger.info("Retrieved random projects from pool",
                          requested=count, retrieved=len(projects), pool_size=pool_size)
                return projects

            except Exception as e:
                logger.error("Failed to get random projects from pool", error=str(e))
                return []

    async def get_pool_size(self) -> int:
        """Get the current size of the project pool"""
        async with self.get_redis() as redis_client:
            try:
                pool_key = "project_pool"
                size = await redis_client.llen(pool_key)
                return size
            except Exception as e:
                logger.error("Failed to get pool size", error=str(e))
                return 0

    async def clear_project_pool(self) -> bool:
        """Clear the entire project pool"""
        async with self.get_redis() as redis_client:
            try:
                pool_key = "project_pool"
                result = await redis_client.delete(pool_key)
                logger.info("Cleared project pool", deleted=bool(result))
                return bool(result)
            except Exception as e:
                logger.error("Failed to clear project pool", error=str(e))
                return False

    async def remove_old_projects_from_pool(self, days_old: int = 7) -> int:
        """
        Remove projects older than specified days from the pool
        This is a cleanup operation that should be run periodically

        Args:
            days_old: Remove projects older than this many days

        Returns:
            Number of projects removed
        """
        async with self.get_redis() as redis_client:
            try:
                pool_key = "project_pool"
                pool_size = await redis_client.llen(pool_key)

                removed_count = 0
                current_time = datetime.now()

                # Check each project in the pool
                for i in range(pool_size - 1, -1, -1):  # Iterate backwards
                    project_data = await redis_client.lindex(pool_key, i)
                    if project_data:
                        try:
                            project_dict = json.loads(project_data)
                            if "generated_at" in project_dict:
                                generated_at = datetime.fromisoformat(project_dict["generated_at"].replace('Z', '+00:00'))
                                age = current_time - generated_at

                                if age.days >= days_old:
                                    # Remove old project using LREM
                                    await redis_client.lrem(pool_key, 1, project_data)
                                    removed_count += 1
                        except Exception as e:
                            logger.warning("Failed to parse project during cleanup", error=str(e))
                            # Remove corrupted data
                            await redis_client.lrem(pool_key, 1, project_data)
                            removed_count += 1

                if removed_count > 0:
                    logger.info("Removed old projects from pool", removed=removed_count)

                return removed_count

            except Exception as e:
                logger.error("Failed to remove old projects from pool", error=str(e))
                return 0

    def _get_daily_projects_key(self, date: str) -> str:
        """Generate key for daily projects"""
        return f"daily_projects:{date}"

    def _get_generation_lock_key(self, date: str) -> str:
        """Generate key for generation lock"""
        return f"generation_lock:{date}"


redis_service = RedisService()
