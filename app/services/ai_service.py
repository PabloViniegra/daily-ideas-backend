import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

import httpx
import structlog

# Google AI imports
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False

from app.config import settings
from app.models.project import Project, DifficultyLevel

logger = structlog.get_logger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass


class DeepSeekService:
    """Service for interacting with the DeepSeek API"""

    def __init__(self):
        self.api_url = settings.deepseek_api_url
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model
        self.max_tokens = settings.deepseek_max_tokens
        self.temperature = settings.deepseek_temperature
        self.timeout = settings.deepseek_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager for handling HTTP client"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=10,
                                max_keepalive_connections=5)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()

    async def generate_projects(
        self,
        count: int = 5,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> List[Project]:
        """
        Generate projects using DeepSeek AI

        Args:
            count: Number of projects to generate (1-10)
            difficulty_preference: List of preferred difficulty levels
            category_preference: Preferred category

        Returns:
            List of generated projects

        Raises:
            AIServiceError: If there is an error in the generation
        """
        if not 1 <= count <= 10:
            raise AIServiceError(
                "The number of projects must be between 1 and 10")

        prompt = self._build_prompt(
            count, difficulty_preference, category_preference)

        try:
            async with self:  # Use context manager
                response = await self._make_api_request(prompt)
                projects = self._parse_ai_response(response)

                # Ensure we have the exact number of projects requested
                if len(projects) != count:
                    logger.warning(
                        "Generated projects count mismatch, adjusting",
                        expected=count,
                        actual=len(projects)
                    )

                    if len(projects) > count:
                        # Take only the requested number
                        projects = projects[:count]
                        logger.info("Trimmed projects to requested count", count=count)
                    elif len(projects) < count:
                        # Generate additional projects to reach the target
                        needed = count - len(projects)
                        logger.info("Generating additional projects", needed=needed)
                        try:
                            additional_projects = await self._generate_additional_projects(
                                needed, difficulty_preference, category_preference
                            )
                            projects.extend(additional_projects)
                            logger.info("Successfully added additional projects", total=len(projects))
                        except Exception as e:
                            logger.warning("Failed to generate additional projects, using fallback", error=str(e))
                            # Use fallback projects to fill the gap
                            fallback_projects = self._get_fallback_projects_minimal(needed)
                            projects.extend(fallback_projects)
                            logger.info("Used fallback projects to complete count", total=len(projects))

                # Agregar timestamps y IDs temporales
                timestamp = datetime.now()
                for i, project in enumerate(projects):
                    project.generated_at = timestamp
                    project.id = f"temp-{timestamp.strftime('%Y%m%d%H%M%S')}-{i+1}"

                # Final validation - ensure we have exactly the requested count
                if len(projects) != count:
                    logger.error("Unable to generate exact project count", expected=count, actual=len(projects))
                    # Final fallback - pad or trim to exact count
                    if len(projects) > count:
                        projects = projects[:count]
                    elif len(projects) < count:
                        fallback_projects = self._get_fallback_projects_minimal(count - len(projects))
                        projects.extend(fallback_projects)

                logger.info("Successfully generated projects",
                            count=len(projects))
                return projects

        except Exception as e:
            logger.error("Failed to generate projects", error=str(e))
            raise AIServiceError(f"Error generating projects: {str(e)}")

    async def _make_api_request(self, prompt: str) -> dict:
        """
        Make API request to DeepSeek

        Args:
            prompt: Prompt to send to the AI

        Returns:
            API response

        Raises:
            AIServiceError: If the request fails
        """
        if not self._client:
            raise AIServiceError("HTTP client not initialized")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }

        try:
            response = await self._client.post(
                self.api_url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise AIServiceError(
                    "Respuesta de IA inválida: no hay choices")

            return data

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error from DeepSeek API",
                         status_code=e.response.status_code)
            raise AIServiceError(
                f"Error HTTP {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            logger.error("Timeout calling DeepSeek API")
            raise AIServiceError("Timeout al llamar a la API de DeepSeek")
        except Exception as e:
            logger.error("Unexpected error calling DeepSeek API", error=str(e))
            raise AIServiceError(f"Error inesperado: {str(e)}")

    def _parse_ai_response(self, response: dict) -> List[Project]:
        """
        Parse the AI response and convert to Project objects

        Args:
            response: API response from DeepSeek

        Returns:
            List of parsed projects

        Raises:
            AIServiceError: If the response cannot be parsed
        """
        try:
            content = response["choices"][0]["message"]["content"]

            # Try to extract JSON from the response
            # The AI sometimes includes extra text before/after the JSON
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1

            if start_idx == -1 or end_idx == 0:
                raise AIServiceError(
                    "No valid JSON found in the response")

            json_content = content[start_idx:end_idx]
            projects_data = json.loads(json_content)

            # Validate that it is a list
            if not isinstance(projects_data, list):
                raise AIServiceError(
                    "The response must be a list of projects")

            # Convert to Project objects
            projects = []
            for i, project_data in enumerate(projects_data):
                try:
                    project = Project.parse_obj(project_data)
                    projects.append(project)
                except Exception as e:
                    logger.warning(
                        "Failed to parse project from AI response",
                        project_index=i,
                        error=str(e),
                        data=project_data
                    )
                    continue

            if not projects:
                raise AIServiceError(
                    "No valid projects could be parsed")

            return projects

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to decode JSON from AI response", error=str(e))
            raise AIServiceError(f"Error decodificando JSON: {str(e)}")
        except KeyError as e:
            logger.error("Missing key in AI response", error=str(e))
            raise AIServiceError(f"Clave faltante en respuesta: {str(e)}")

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for AI

        Returns:
            Optimized system prompt
        """
        return """Eres un experto arquitecto de software y mentor de desarrollo con más de 15 años de experiencia. 
Tu especialidad es crear ideas de proyectos prácticos, innovadores y educativos para desarrolladores de todos los niveles.

IMPORTANTE: Debes responder ÚNICAMENTE con un array JSON válido, sin texto adicional antes o después.

Características de tus proyectos:
- Son proyectos reales que resuelven problemas genuinos
- Incluyen tecnologías modernas y relevantes del mercado actual
- Tienen alcance realista según el nivel de dificultad
- Son atractivos y motivadores para implementar
- Incluyen funcionalidades específicas y bien definidas

Niveles de dificultad:
- beginner: 1-3 días, conceptos básicos, pocas tecnologías
- intermediate: 3-7 días, integración de sistemas, múltiples tecnologías
- advanced: 1-3 semanas, arquitecturas complejas, optimizaciones avanzadas"""

    def _build_prompt(
        self,
        count: int,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> str:
        """
        Construir prompt específico para generación de proyectos

        Args:
            count: Número de proyectos
            difficulty_preference: Preferencias de dificultad
            category_preference: Categoría preferida

        Returns:
            Prompt construido
        """
        # Default difficulty distribution
        if not difficulty_preference:
            if count == 5:
                difficulty_dist = "1 beginner, 2 intermediate, 2 advanced"
            elif count <= 3:
                difficulty_dist = "distribución equilibrada"
            else:
                difficulty_dist = f"distribución equilibrada entre los {count} proyectos"
        else:
            difficulty_dist = f"preferentemente: {', '.join(difficulty_preference)}"

        # Suggested categories if no preference
        categories = [
            "Web Applications", "Mobile Apps", "Desktop Tools", "APIs & Microservices",
            "Data Analysis", "Automation Tools", "Games", "Developer Tools",
            "IoT Projects", "AI/ML Applications", "Blockchain", "DevOps Tools"
        ]

        category_hint = f"Preferentemente en: {category_preference}" if category_preference else f"Varia entre: {', '.join(categories[:6])}"

        current_year = datetime.now().year
        current_trends = self._get_current_tech_trends()

        return f"""Genera exactamente {count} ideas de proyectos de desarrollo de software únicos y creativos para {current_year}.

DISTRIBUCIÓN DE DIFICULTAD: {difficulty_dist}
CATEGORÍAS: {category_hint}

TENDENCIAS ACTUALES A CONSIDERAR: {current_trends}

Para cada proyecto, proporciona la información en este formato JSON EXACTO:

{{
  "title": "Nombre conciso y atractivo del proyecto",
  "description": "Descripción detallada en 2-3 oraciones que explique el problema que resuelve y su propuesta de valor",
  "difficulty": "beginner|intermediate|advanced",
  "estimated_time": "tiempo realista (ej: 2-3 días, 1 semana, 2-3 semanas)",
  "category": "categoría específica del proyecto",
  "technologies": [
    {{
      "name": "Nombre exacto de la tecnología",
      "type": "frontend|backend|database|tool|framework|library|language",
      "reason": "Justificación específica y técnica de por qué usar esta tecnología"
    }}
  ],
  "features": ["característica específica 1", "característica específica 2", "característica específica 3", "característica específica 4", "característica específica 5"]
}}

REQUISITOS ESPECÍFICOS:
1. Cada proyecto debe tener entre 2-5 tecnologías
2. Las características deben ser funcionalidades concretas, no generalidades
3. Los títulos deben ser únicos y memorables
4. Las descripciones deben mostrar el valor real del proyecto
5. Las tecnologías deben ser apropiadas para el nivel de dificultad
6. Incluir al menos una tecnología frontend o framework por proyecto

RESPONDE ÚNICAMENTE CON EL ARRAY JSON, SIN TEXTO ADICIONAL."""

    def _get_current_tech_trends(self) -> str:
        """
        Obtener tendencias tecnológicas actuales

        Returns:
            String con tendencias actuales
        """
        trends = [
            "Next.js 14 con App Router",
            "React Server Components",
            "TypeScript 5+",
            "Tailwind CSS",
            "Prisma ORM",
            "tRPC",
            "Supabase",
            "Vercel AI SDK",
            "Astro",
            "SvelteKit",
            "Bun runtime",
            "Drizzle ORM",
            "Shadcn/ui",
            "FastAPI",
            "LangChain",
            "Docker & Kubernetes",
            "Serverless Functions"
        ]

        return ", ".join(trends[:10])

    async def _generate_additional_projects(
        self,
        count: int,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> List[Project]:
        """
        Generate additional projects to meet the exact count requirement
        """
        prompt = self._build_prompt(count, difficulty_preference, category_preference)

        async with self:  # Use context manager
            response = await self._make_api_request(prompt)
            projects = self._parse_ai_response(response)

            # Add timestamps and IDs
            timestamp = datetime.now()
            for i, project in enumerate(projects):
                project.generated_at = timestamp
                project.id = f"temp-additional-{timestamp.strftime('%Y%m%d%H%M%S')}-{i+1}"

            return projects[:count]  # Ensure we don't exceed the requested count

    def _get_fallback_projects_minimal(self, count: int) -> List[Project]:
        """
        Get minimal fallback projects when AI fails or we need to fill gaps
        """
        fallback_templates = [
            {
                "title": "Personal Task Manager",
                "description": "A simple task management app with CRUD operations and local storage. Perfect for practicing fundamental web development skills.",
                "difficulty": "beginner",
                "estimated_time": "1-2 días",
                "category": "Web Application",
                "technologies": [
                    {"name": "React", "type": "frontend", "reason": "Component-based architecture for interactive UI"},
                    {"name": "localStorage", "type": "database", "reason": "Client-side persistence without backend complexity"}
                ],
                "features": ["Add/edit/delete tasks", "Mark as complete", "Filter by status", "Local storage", "Responsive design"]
            },
            {
                "title": "Weather Information App",
                "description": "A weather application that displays current conditions and forecasts with location-based services.",
                "difficulty": "intermediate",
                "estimated_time": "2-3 días",
                "category": "Data Application",
                "technologies": [
                    {"name": "Vue.js", "type": "frontend", "reason": "Reactive framework for dynamic weather data display"},
                    {"name": "OpenWeather API", "type": "tool", "reason": "Reliable weather data source"}
                ],
                "features": ["Current weather display", "5-day forecast", "Geolocation", "Search by city", "Weather icons"]
            },
            {
                "title": "Simple Blog Platform",
                "description": "A minimal blogging platform with post creation, editing, and basic content management features.",
                "difficulty": "intermediate",
                "estimated_time": "3-4 días",
                "category": "Content Management",
                "technologies": [
                    {"name": "Node.js", "type": "backend", "reason": "Server-side JavaScript for unified language"},
                    {"name": "SQLite", "type": "database", "reason": "Lightweight database for simple data storage"}
                ],
                "features": ["Create/edit posts", "Rich text editor", "Post categories", "Basic search", "Responsive layout"]
            },
            {
                "title": "URL Shortener Service",
                "description": "A URL shortening service with analytics tracking and custom short link generation capabilities.",
                "difficulty": "advanced",
                "estimated_time": "4-5 días",
                "category": "Web Service",
                "technologies": [
                    {"name": "FastAPI", "type": "backend", "reason": "High-performance async API framework for URL processing"},
                    {"name": "Redis", "type": "database", "reason": "Fast caching for URL lookups"}
                ],
                "features": ["Custom short URLs", "Click analytics", "Expiration dates", "QR code generation", "API endpoints"]
            },
            {
                "title": "Recipe Finder",
                "description": "A recipe discovery application that helps users find recipes based on available ingredients and dietary preferences.",
                "difficulty": "beginner",
                "estimated_time": "2-3 días",
                "category": "Lifestyle Application",
                "technologies": [
                    {"name": "React", "type": "frontend", "reason": "Component-based UI for recipe cards and search interface"},
                    {"name": "Recipe API", "type": "tool", "reason": "External recipe data source"}
                ],
                "features": ["Ingredient-based search", "Recipe details", "Nutritional info", "Save favorites", "Shopping list"]
            }
        ]

        projects = []
        timestamp = datetime.now()

        for i in range(min(count, len(fallback_templates))):
            template = fallback_templates[i % len(fallback_templates)]
            project = Project.model_validate(template)
            project.id = f"fallback-{timestamp.strftime('%Y%m%d%H%M%S')}-{i+1}"
            project.generated_at = timestamp
            projects.append(project)

        return projects


class GoogleAIService:
    """Service for interacting with Google AI (Gemini) API"""

    def __init__(self):
        if not GOOGLE_AI_AVAILABLE:
            raise AIServiceError("Google AI library not available")
        
        if not settings.google_api_key:
            raise AIServiceError("Google API key not configured")
            
        genai.configure(api_key=settings.google_api_key)
        self.model_name = settings.google_model
        self.max_tokens = settings.google_max_tokens
        self.temperature = settings.google_temperature

    async def generate_projects(
        self,
        count: int = 5,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> List[Project]:
        """
        Generate projects using Google AI (Gemini)
        """
        try:
            model = genai.GenerativeModel(self.model_name)
            prompt = self._build_prompt(count, difficulty_preference, category_preference)
            
            # Generate content asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                )
            )
            
            # Parse response
            projects = self._parse_ai_response(response)
            
            # Add timestamps and IDs
            timestamp = datetime.now()
            for i, project in enumerate(projects):
                project.generated_at = timestamp
                project.id = f"google-{timestamp.strftime('%Y%m%d%H%M%S')}-{i+1}"
            
            logger.info("Successfully generated projects with Google AI", count=len(projects))
            return projects
            
        except Exception as e:
            logger.error("Failed to generate projects with Google AI", error=str(e))
            raise AIServiceError(f"Error generating projects with Google AI: {str(e)}")

    def _parse_ai_response(self, response) -> List[Project]:
        """Parse Google AI response"""
        try:
            content = response.text
            
            # Extract JSON from response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise AIServiceError("No valid JSON found in Google AI response")
            
            json_content = content[start_idx:end_idx]
            projects_data = json.loads(json_content)
            
            if not isinstance(projects_data, list):
                raise AIServiceError("Google AI response must be a list of projects")
            
            projects = []
            for i, project_data in enumerate(projects_data):
                try:
                    project = Project.parse_obj(project_data)
                    projects.append(project)
                except Exception as e:
                    logger.warning(
                        "Failed to parse project from Google AI response",
                        project_index=i,
                        error=str(e),
                        data=project_data
                    )
                    continue
            
            if not projects:
                raise AIServiceError("No valid projects could be parsed from Google AI response")
            
            return projects
            
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON from Google AI response", error=str(e))
            raise AIServiceError(f"Error decoding JSON from Google AI: {str(e)}")
        except Exception as e:
            logger.error("Error parsing Google AI response", error=str(e))
            raise AIServiceError(f"Error parsing Google AI response: {str(e)}")

    def _build_prompt(
        self,
        count: int,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> str:
        """Build prompt for Google AI"""
        # Use the same prompt building logic
        # Default difficulty distribution
        if not difficulty_preference:
            if count == 5:
                difficulty_dist = "1 beginner, 2 intermediate, 2 advanced"
            elif count <= 3:
                difficulty_dist = "distribución equilibrada"
            else:
                difficulty_dist = f"distribución equilibrada entre los {count} proyectos"
        else:
            difficulty_dist = f"preferentemente: {', '.join(difficulty_preference)}"

        # Suggested categories if no preference
        categories = [
            "Web Applications", "Mobile Apps", "Desktop Tools", "APIs & Microservices",
            "Data Analysis", "Automation Tools", "Games", "Developer Tools",
            "IoT Projects", "AI/ML Applications", "Blockchain", "DevOps Tools"
        ]

        category_hint = f"Preferentemente en: {category_preference}" if category_preference else f"Varia entre: {', '.join(categories[:6])}"

        current_year = datetime.now().year
        current_trends = self._get_current_tech_trends()

        return f"""Genera exactamente {count} ideas de proyectos de desarrollo de software únicos y creativos para {current_year}.

DISTRIBUCIÓN DE DIFICULTAD: {difficulty_dist}
CATEGORÍAS: {category_hint}

TENDENCIAS ACTUALES A CONSIDERAR: {current_trends}

Para cada proyecto, proporciona la información en este formato JSON EXACTO:

{{
  "title": "Nombre conciso y atractivo del proyecto",
  "description": "Descripción detallada en 2-3 oraciones que explique el problema que resuelve y su propuesta de valor",
  "difficulty": "beginner|intermediate|advanced",
  "estimated_time": "tiempo realista (ej: 2-3 días, 1 semana, 2-3 semanas)",
  "category": "categoría específica del proyecto",
  "technologies": [
    {{
      "name": "Nombre exacto de la tecnología",
      "type": "frontend|backend|database|tool|framework|library|language",
      "reason": "Justificación específica y técnica de por qué usar esta tecnología"
    }}
  ],
  "features": ["característica específica 1", "característica específica 2", "característica específica 3", "característica específica 4", "característica específica 5"]
}}

REQUISITOS ESPECÍFICOS:
1. Cada proyecto debe tener entre 2-5 tecnologías
2. Las características deben ser funcionalidades concretas, no generalidades
3. Los títulos deben ser únicos y memorables
4. Las descripciones deben mostrar el valor real del proyecto
5. Las tecnologías deben ser apropiadas para el nivel de dificultad
6. Incluir al menos una tecnología frontend o framework por proyecto

RESPONDE ÚNICAMENTE CON EL ARRAY JSON, SIN TEXTO ADICIONAL."""

    def _get_current_tech_trends(self) -> str:
        """Get current tech trends"""
        trends = [
            "Next.js 14 con App Router",
            "React Server Components",
            "TypeScript 5+",
            "Tailwind CSS",
            "Prisma ORM",
            "tRPC",
            "Supabase",
            "Vercel AI SDK",
            "Astro",
            "SvelteKit",
            "Bun runtime",
            "Drizzle ORM",
            "Shadcn/ui",
            "FastAPI",
            "LangChain",
            "Docker & Kubernetes",
            "Serverless Functions"
        ]

        return ", ".join(trends[:10])


class HybridAIService:
    """Hybrid AI service that tries DeepSeek first, then falls back to Google AI"""
    
    def __init__(self):
        self.deepseek = DeepSeekService()
        self.google_ai = None
        
        # Initialize Google AI if available
        if GOOGLE_AI_AVAILABLE and settings.google_api_key:
            try:
                self.google_ai = GoogleAIService()
                logger.info("Google AI service initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize Google AI service", error=str(e))
        else:
            logger.warning("Google AI not available or not configured")

    async def generate_projects(
        self,
        count: int = 5,
        difficulty_preference: Optional[List[DifficultyLevel]] = None,
        category_preference: Optional[str] = None
    ) -> List[Project]:
        """
        Generate projects using hybrid approach: try DeepSeek first, then Google AI
        """
        # Try DeepSeek first
        try:
            logger.info("Attempting to generate projects with DeepSeek")
            projects = await self.deepseek.generate_projects(
                count=count,
                difficulty_preference=difficulty_preference,
                category_preference=category_preference
            )
            logger.info("Successfully generated projects with DeepSeek")
            return projects
        except AIServiceError as e:
            logger.warning("DeepSeek failed, trying Google AI fallback", error=str(e))
            
            # Try Google AI as fallback
            if self.google_ai:
                try:
                    logger.info("Attempting to generate projects with Google AI")
                    projects = await self.google_ai.generate_projects(
                        count=count,
                        difficulty_preference=difficulty_preference,
                        category_preference=category_preference
                    )
                    logger.info("Successfully generated projects with Google AI fallback")
                    return projects
                except AIServiceError as google_error:
                    logger.error("Both DeepSeek and Google AI failed", 
                               deepseek_error=str(e), google_error=str(google_error))
                    raise AIServiceError(f"Both AI services failed. DeepSeek: {str(e)}, Google: {str(google_error)}")
            else:
                logger.error("Google AI not available as fallback")
                raise AIServiceError(f"DeepSeek failed and Google AI not available: {str(e)}")


ai_service = HybridAIService()
