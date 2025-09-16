# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Activate virtual environment (if not already active)
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Run the development server
python app/main.py
# or
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_filename.py

# Run tests with verbose output
pytest -v
```

### Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Update requirements
pip freeze > requirements.txt
```

## Architecture Overview

This is a FastAPI-based backend application for generating daily project ideas using AI. The application uses a service-oriented architecture with the following key components:

### Core Structure
- **FastAPI Application**: Main web framework with async support
- **Pydantic Models**: Data validation and serialization via `app/models/`
- **Service Layer**: Business logic in `app/services/`
- **Configuration**: Centralized settings in `app/config.py`

### Key Services
- **AI Service** (`ai_service.py`): Integrates with DeepSeek API for AI-powered project generation
- **Project Service** (`project_service.py`): Manages project creation, validation, and business logic
- **Redis Service** (`redis_service.py`): Handles caching, rate limiting, and data persistence

### Data Models
- **Project**: Core data model with title, description, difficulty levels, technologies, and features
- **Technology**: Represents technologies used in projects with types (frontend, backend, database, etc.)
- **DifficultyLevel**: Enum for beginner, intermediate, advanced levels

### API Structure
The application expects API endpoints to be organized under:
- `/api/v1/projects` - Project-related endpoints
- `/api/v1/health` - Health check endpoints

Note: API router files appear to be missing from the current codebase but are imported in `main.py`.

### Configuration
- Environment-based configuration using Pydantic Settings
- Required environment variables: `DEEPSEEK_API_KEY`, `REDIS_URL`
- Optional variables for CORS, rate limiting, and Redis configuration
- Development/production environment detection

### Key Features
- **Rate Limiting**: Configurable requests per minute
- **Caching**: Redis-based caching with TTL for generated projects
- **Error Handling**: Custom exceptions for AI service and project service errors
- **Logging**: Structured logging with structlog
- **CORS**: Configurable CORS middleware
- **Lifecycle Management**: Proper startup/shutdown handling for Redis connections

### Dependencies
- FastAPI with uvicorn for web server
- httpx for HTTP client functionality
- Redis for caching and rate limiting
- Pydantic for data validation
- structlog for structured logging
- APScheduler for scheduling tasks
- pytest for testing framework

## Development Notes

### Missing Components
The main.py file imports API routers that don't exist in the current codebase:
- `app.api.v1.projects`
- `app.api.v1.health`
- `app.core.exceptions`
- `app.core.logging`

These should be created to match the imports or the imports should be updated.

### Environment Setup
Ensure `.env` file contains required variables:
- `DEEPSEEK_API_KEY`: API key for DeepSeek service
- `REDIS_URL`: Redis connection URL
- `ENVIRONMENT`: Set to "development" or "production"