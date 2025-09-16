from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class DifficultyLevel(str, Enum):
    """Difficulty level of the project."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TechnologyType(str, Enum):
    """Technology type of the project."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    TOOL = "tool"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    LANGUAGE = "language"


class Technology(BaseModel):
    """Technology of the project."""
    name: str = Field(..., min_length=1, max_length=100,
                      description="Technology's name")
    type: TechnologyType = Field(..., description="Technology's type")
    reason: str = Field(..., min_length=10, max_length=200,
                        description="Reason for using this technology")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "React",
                "type": "frontend",
                "reason": "For creating a modern and reactive user interface"
            }
        }


class Project(BaseModel):
    """Project model."""
    id: Optional[str] = Field(None, description="ID unique of the project")
    title: str = Field(..., min_length=5, max_length=150,
                       description="Project's title")
    description: str = Field(..., min_length=20,
                             max_length=800, description="Project's description")
    difficulty: DifficultyLevel = Field(...,
                                        description="Project's difficulty")
    estimated_time: str = Field(..., min_length=3,
                                max_length=50, description="Estimated time")
    category: str = Field(..., min_length=3, max_length=50,
                          description="Project's category")
    technologies: List[Technology] = Field(
        ..., min_items=2, max_items=6, description="Recommended technologies")
    features: List[str] = Field(..., min_items=3, max_items=10,
                                description="Project's features")
    generated_at: Optional[datetime] = Field(
        None, description="Timestamp of generation")

    @validator("features")
    def validate_features(cls, v):
        """Validate that features are not empty"""
        if not all(feature.strip() for feature in v):
            raise ValueError("Features cannot be empty")
        return v

    @validator("technologies")
    def validate_technologies(cls, v):
        """Validate that there is at least one frontend or backend technology"""
        tech_types = [tech.type for tech in v]
        if not any(t in [TechnologyType.FRONTEND, TechnologyType.BACKEND, TechnologyType.FRAMEWORK] for t in tech_types):
            raise ValueError(
                "Must include at least one frontend, backend or framework technology")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Task Manager with Drag & Drop",
                "description": "An application for managing tasks that allows organizing activities by dragging and dropping, with automatic categorization and intelligent notifications.",
                "difficulty": "intermediate",
                "estimated_time": "2-3 days",
                "category": "Productivity",
                "technologies": [
                    {
                        "name": "Vue.js",
                        "type": "frontend",
                        "reason": "Framework reactive ideal for dynamic interfaces"
                    },
                    {
                        "name": "Node.js",
                        "type": "backend",
                        "reason": "API REST scalable for data management"
                    }
                ],
                "features": [
                    "Drag & drop intuitive",
                    "Automatic categorization",
                    "Real-time notifications",
                    "Advanced filters",
                    "Offline mode"
                ]
            }
        }


class ProjectCreateRequest(BaseModel):
    """Request to create projects manually (optional)"""
    count: int = Field(default=5, ge=1, le=10,
                       description="Number of projects to generate")
    difficulty_preference: Optional[List[DifficultyLevel]] = Field(
        None, description="Difficulty preferences")
    category_preference: Optional[str] = Field(
        None, max_length=50, description="Category preference")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 5,
                "difficulty_preference": ["intermediate", "advanced"],
                "category_preference": "Web Development"
            }
        }
