"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
import os
from unittest.mock import patch
from datetime import datetime

from app.models.project import Project, DifficultyLevel, TechnologyType, Technology


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    env_vars = {
        'REDIS_URL': 'redis://localhost:6379/15',  # Use test database
        'DEEPSEEK_API_KEY': 'test-deepseek-key',
        'GOOGLE_API_KEY': 'test-google-key',
        'ENVIRONMENT': 'development',
        'DEBUG': 'true'
    }

    with patch.dict(os.environ, env_vars, clear=True):
        yield env_vars


@pytest.fixture
def sample_technology():
    """Sample technology for testing"""
    return Technology(
        name="React",
        type=TechnologyType.FRONTEND,
        reason="For building interactive user interfaces with component-based architecture"
    )


@pytest.fixture
def sample_project():
    """Sample project for testing"""
    return Project(
        id="test-2025-01-15-1",
        title="Sample Test Project",
        description="A comprehensive test project designed for unit testing and validation purposes with multiple features",
        difficulty=DifficultyLevel.INTERMEDIATE,
        estimated_time="2-3 days",
        category="Testing",
        technologies=[
            Technology(
                name="React",
                type=TechnologyType.FRONTEND,
                reason="For building interactive user interfaces"
            ),
            Technology(
                name="Node.js",
                type=TechnologyType.BACKEND,
                reason="For server-side JavaScript execution"
            )
        ],
        features=[
            "User authentication",
            "Real-time updates",
            "Data visualization",
            "Mobile responsive design"
        ],
        generated_at=datetime.now()
    )


@pytest.fixture
def sample_projects_list():
    """List of sample projects for testing"""
    return [
        Project(
            id="test-2025-01-15-1",
            title="Web Dashboard",
            description="A comprehensive dashboard application for data visualization and analytics with real-time updates",
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time="3-4 days",
            category="Data Visualization",
            technologies=[
                Technology(name="Vue.js", type=TechnologyType.FRONTEND, reason="For reactive data binding"),
                Technology(name="Python", type=TechnologyType.BACKEND, reason="For data processing")
            ],
            features=["Real-time charts", "Data filtering", "Export functionality", "User management"],
            generated_at=datetime.now()
        ),
        Project(
            id="test-2025-01-15-2",
            title="Mobile Task Manager",
            description="A mobile-first task management application with offline capabilities and synchronization features",
            difficulty=DifficultyLevel.BEGINNER,
            estimated_time="1-2 days",
            category="Productivity",
            technologies=[
                Technology(name="React Native", type=TechnologyType.FRAMEWORK, reason="For cross-platform development"),
                Technology(name="SQLite", type=TechnologyType.DATABASE, reason="For offline data storage")
            ],
            features=["Offline mode", "Task categories", "Push notifications", "Cloud sync"],
            generated_at=datetime.now()
        ),
        Project(
            id="test-2025-01-15-3",
            title="E-commerce API",
            description="A scalable REST API for e-commerce operations with advanced features for inventory and order management",
            difficulty=DifficultyLevel.ADVANCED,
            estimated_time="1-2 weeks",
            category="E-commerce",
            technologies=[
                Technology(name="FastAPI", type=TechnologyType.FRAMEWORK, reason="For high-performance API development"),
                Technology(name="PostgreSQL", type=TechnologyType.DATABASE, reason="For reliable data storage"),
                Technology(name="Redis", type=TechnologyType.DATABASE, reason="For caching and session management")
            ],
            features=["Product management", "Order processing", "Payment integration", "Inventory tracking", "Analytics"],
            generated_at=datetime.now()
        )
    ]


@pytest.fixture
def mock_redis_responses():
    """Mock Redis responses for testing"""
    return {
        "ping": True,
        "get": None,
        "set": True,
        "setex": True,
        "delete": 1,
        "exists": 0,
        "incr": 1,
        "info": {
            "redis_version": "6.2.0",
            "used_memory_human": "1.5M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600
        }
    }


@pytest.fixture
def mock_ai_response():
    """Mock AI service response for testing"""
    return {
        "choices": [
            {
                "message": {
                    "content": """[
                        {
                            "title": "AI-Generated Project",
                            "description": "A project generated by AI for testing purposes with comprehensive features",
                            "difficulty": "intermediate",
                            "estimated_time": "3-4 days",
                            "category": "Web Development",
                            "technologies": [
                                {"name": "React", "type": "frontend", "reason": "For building user interfaces"},
                                {"name": "FastAPI", "type": "backend", "reason": "For creating REST APIs"}
                            ],
                            "features": ["Feature 1", "Feature 2", "Feature 3", "Feature 4"]
                        }
                    ]"""
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_singleton_instances():
    """Reset singleton instances before each test"""
    # Reset Redis service singleton
    from app.services.redis_service import RedisService
    RedisService._instance = None
    RedisService._redis_pool = None

    yield

    # Clean up after test
    RedisService._instance = None
    RedisService._redis_pool = None


@pytest.fixture
def valid_project_data():
    """Valid project data for testing"""
    return {
        "title": "Test Project for Validation",
        "description": "A comprehensive test project designed specifically for validation testing with multiple components",
        "difficulty": "intermediate",
        "estimated_time": "2-3 days",
        "category": "Testing",
        "technologies": [
            {
                "name": "Python",
                "type": "backend",
                "reason": "For backend logic and data processing"
            },
            {
                "name": "React",
                "type": "frontend",
                "reason": "For user interface development"
            }
        ],
        "features": [
            "Unit testing framework",
            "Integration testing",
            "Test coverage reporting",
            "Automated CI/CD"
        ]
    }


@pytest.fixture
def invalid_project_data():
    """Invalid project data for testing validation"""
    return {
        "title": "Bad",  # Too short
        "description": "Too short",  # Too short
        "difficulty": "invalid",  # Invalid difficulty
        "estimated_time": "2-3 days",
        "category": "Testing",
        "technologies": [
            # Only one technology (minimum is 2)
            {
                "name": "Python",
                "type": "database",  # Wrong type, no frontend/backend/framework
                "reason": "For backend logic"
            }
        ],
        "features": [
            "Feature 1",
            "Feature 2"  # Only 2 features (minimum is 3)
        ]
    }