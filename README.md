# Daily Ideas API

A FastAPI-based backend application for generating daily project ideas using AI. This application leverages the DeepSeek API to create innovative, practical programming project suggestions for developers of all skill levels.

## ✨ Features

- **AI-Powered Project Generation**: Uses DeepSeek API to generate creative, realistic project ideas
- **Daily Project Caching**: Automatically caches daily projects with Redis for optimal performance
- **Skill-Level Filtering**: Projects categorized by beginner, intermediate, and advanced difficulty
- **Technology Recommendations**: Each project includes specific technology suggestions with justifications
- **Rate Limiting**: Built-in rate limiting to prevent API abuse
- **Health Monitoring**: Comprehensive health checks for all services
- **Fallback System**: Provides backup projects when AI service is unavailable
- **RESTful API**: Clean, documented API with automatic OpenAPI/Swagger documentation

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ 
- Redis server (local or cloud)
- DeepSeek API key

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd daily-ideas-backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Linux/Mac
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the project root:
   ```env
   # Required
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   REDIS_URL=redis://localhost:6379
   
   # Optional
   ENVIRONMENT=development
   DEBUG=true
   BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
   ```

5. **Run the application:**
   ```bash
   # Method 1: Using uvicorn directly (recommended)
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Method 2: Using the main.py file
   python app/main.py
   ```

6. **Verify the API is running:**
   ```bash
   curl http://localhost:8000/
   ```

## 📚 API Documentation

Once running, access the interactive documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🛠 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and status |
| `GET` | `/api/v1/health` | Health check with service status |
| `GET` | `/api/v1/health/live` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe |

### Project Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|-----------|
| `GET` | `/api/v1/daily` | Get today's daily projects | `?count=5&force_regenerate=false` |
| `POST` | `/api/v1/generate` | Generate custom projects | JSON body with preferences |
| `GET` | `/api/v1/project/{id}` | Get specific project by ID | - |
| `GET` | `/api/v1/stats` | Get project generation statistics | - |
| `DELETE` | `/api/v1/cache` | Clear project cache | - |

### Usage Examples

**Get Daily Projects:**
```bash
# Get 5 daily projects (default)
curl http://localhost:8000/api/v1/daily

# Get 3 daily projects
curl "http://localhost:8000/api/v1/daily?count=3"

# Force regenerate daily projects
curl "http://localhost:8000/api/v1/daily?force_regenerate=true"
```

**Generate Custom Projects:**
```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "count": 3,
    "difficulty_preference": ["beginner", "intermediate"],
    "category_preference": "Web Development"
  }'
```

**Health Check:**
```bash
curl http://localhost:8000/api/v1/health
```

## 📊 Example Response

**Daily Projects Response:**
```json
[
  {
    "id": "2025-09-13-1",
    "title": "Todo List con Dark Mode",
    "description": "Una aplicación de tareas pendientes con interfaz moderna, modo oscuro automático y sincronización local.",
    "difficulty": "beginner",
    "estimated_time": "1-2 días",
    "category": "Web Application",
    "technologies": [
      {
        "name": "React",
        "type": "frontend",
        "reason": "Componentes reutilizables y hooks para estado"
      }
    ],
    "features": [
      "Agregar/eliminar tareas",
      "Modo oscuro",
      "Filtros por estado"
    ],
    "generated_at": "2025-09-13T12:33:35.786083"
  }
]
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API key for AI generation | - | ✅ |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | ✅ |
| `ENVIRONMENT` | Environment (development/production) | `development` | ❌ |
| `DEBUG` | Enable debug mode | `true` | ❌ |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins (JSON array) | `[]` | ❌ |
| `MAX_REQUESTS_PER_MINUTE` | Rate limiting | `60` | ❌ |
| `DAILY_PROJECTS_TTL` | Daily projects cache TTL (seconds) | `604800` | ❌ |

### Project Structure

```
daily-ideas-backend/
├── app/
│   ├── api/v1/          # API route handlers
│   ├── core/            # Core functionality (exceptions, logging)
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic services
│   ├── config.py        # Configuration management
│   └── main.py          # FastAPI application
├── tests/               # Test files
├── .env                 # Environment variables
├── requirements.txt     # Python dependencies
├── CLAUDE.md           # Development guidance
└── README.md           # This file
```

## 🧪 Testing

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov=app
```

**Run specific test file:**
```bash
pytest tests/test_projects.py
```

## 🔧 Development

### Local Development Setup

1. Ensure Redis is running locally or use a cloud Redis instance
2. Set up your DeepSeek API key in the `.env` file
3. Run the development server with auto-reload:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### API Client Libraries

The API follows OpenAPI 3.1 standards, so you can generate client libraries for various languages using the schema at `/openapi.json`.

## 🚨 Important Notes

1. **DeepSeek API Balance**: The AI generation features require a valid DeepSeek API key with sufficient balance. Without balance, the API will fall back to predefined project templates.

2. **Redis Requirement**: Redis is required for caching and rate limiting. Ensure it's accessible via the `REDIS_URL`.

3. **CORS Configuration**: In production, properly configure `BACKEND_CORS_ORIGINS` to only allow your frontend domains.

4. **Rate Limiting**: The API includes rate limiting to prevent abuse. Adjust `MAX_REQUESTS_PER_MINUTE` as needed.

## 🛡️ Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in your environment variables
2. Use a secure Redis instance (not localhost)
3. Configure proper CORS origins
4. Set up monitoring and logging
5. Use a proper ASGI server like Gunicorn with Uvicorn workers
6. Implement proper secret management for API keys

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.