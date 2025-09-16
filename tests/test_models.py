import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.project import (
    DifficultyLevel,
    TechnologyType,
    Technology,
    Project,
    ProjectCreateRequest
)


class TestDifficultyLevel:
    """Test DifficultyLevel enum"""

    def test_difficulty_levels(self):
        assert DifficultyLevel.BEGINNER == "beginner"
        assert DifficultyLevel.INTERMEDIATE == "intermediate"
        assert DifficultyLevel.ADVANCED == "advanced"

    def test_difficulty_level_values(self):
        values = [level.value for level in DifficultyLevel]
        assert "beginner" in values
        assert "intermediate" in values
        assert "advanced" in values


class TestTechnologyType:
    """Test TechnologyType enum"""

    def test_technology_types(self):
        assert TechnologyType.FRONTEND == "frontend"
        assert TechnologyType.BACKEND == "backend"
        assert TechnologyType.DATABASE == "database"
        assert TechnologyType.TOOL == "tool"
        assert TechnologyType.FRAMEWORK == "framework"
        assert TechnologyType.LIBRARY == "library"
        assert TechnologyType.LANGUAGE == "language"

    def test_technology_type_values(self):
        values = [tech_type.value for tech_type in TechnologyType]
        expected = ["frontend", "backend", "database", "tool", "framework", "library", "language"]
        for expected_value in expected:
            assert expected_value in values


class TestTechnology:
    """Test Technology model"""

    def test_valid_technology(self):
        tech = Technology(
            name="React",
            type=TechnologyType.FRONTEND,
            reason="For creating a modern and reactive user interface"
        )

        assert tech.name == "React"
        assert tech.type == TechnologyType.FRONTEND
        assert tech.reason == "For creating a modern and reactive user interface"

    def test_technology_name_validation(self):
        # Test empty name
        with pytest.raises(ValidationError) as exc_info:
            Technology(
                name="",
                type=TechnologyType.FRONTEND,
                reason="For creating a modern interface"
            )
        assert "at least 1 character" in str(exc_info.value)

        # Test name too long
        with pytest.raises(ValidationError) as exc_info:
            Technology(
                name="a" * 101,
                type=TechnologyType.FRONTEND,
                reason="For creating a modern interface"
            )
        assert "at most 100 characters" in str(exc_info.value)

    def test_technology_reason_validation(self):
        # Test reason too short
        with pytest.raises(ValidationError) as exc_info:
            Technology(
                name="React",
                type=TechnologyType.FRONTEND,
                reason="Too short"
            )
        assert "at least 10 characters" in str(exc_info.value)

        # Test reason too long
        with pytest.raises(ValidationError) as exc_info:
            Technology(
                name="React",
                type=TechnologyType.FRONTEND,
                reason="a" * 201
            )
        assert "at most 200 characters" in str(exc_info.value)

    def test_technology_type_validation(self):
        # Test invalid type
        with pytest.raises(ValidationError):
            Technology(
                name="React",
                type="invalid_type",
                reason="For creating a modern interface"
            )


class TestProject:
    """Test Project model"""

    def get_valid_technologies(self):
        return [
            Technology(
                name="React",
                type=TechnologyType.FRONTEND,
                reason="For creating a modern and reactive user interface"
            ),
            Technology(
                name="Node.js",
                type=TechnologyType.BACKEND,
                reason="Server-side JavaScript runtime for API development"
            )
        ]

    def get_valid_features(self):
        return [
            "User authentication",
            "Real-time updates",
            "Data visualization",
            "Mobile responsive design"
        ]

    def test_valid_project(self):
        project = Project(
            title="Task Manager with Drag & Drop",
            description="An application for managing tasks that allows organizing activities by dragging and dropping, with automatic categorization.",
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time="2-3 days",
            category="Productivity",
            technologies=self.get_valid_technologies(),
            features=self.get_valid_features()
        )

        assert project.title == "Task Manager with Drag & Drop"
        assert project.difficulty == DifficultyLevel.INTERMEDIATE
        assert len(project.technologies) == 2
        assert len(project.features) == 4

    def test_project_title_validation(self):
        # Test title too short
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task",
                description="An application for managing tasks that allows organizing activities by dragging and dropping.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=self.get_valid_features()
            )
        assert "at least 5 characters" in str(exc_info.value)

        # Test title too long
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="a" * 151,
                description="An application for managing tasks that allows organizing activities by dragging and dropping.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=self.get_valid_features()
            )
        assert "at most 150 characters" in str(exc_info.value)

    def test_project_description_validation(self):
        # Test description too short
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="Too short",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=self.get_valid_features()
            )
        assert "at least 20 characters" in str(exc_info.value)

        # Test description too long
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="a" * 801,
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=self.get_valid_features()
            )
        assert "at most 800 characters" in str(exc_info.value)

    def test_project_technologies_validation(self):
        # Test too few technologies
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=[self.get_valid_technologies()[0]],  # Only one
                features=self.get_valid_features()
            )
        assert "at least 2 items" in str(exc_info.value)

        # Test too many technologies
        technologies = self.get_valid_technologies() * 4  # 8 technologies
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=technologies,
                features=self.get_valid_features()
            )
        assert "at most 6 items" in str(exc_info.value)

    def test_project_features_validation(self):
        # Test too few features
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=["Feature 1", "Feature 2"]  # Only 2 features
            )
        assert "at least 3 items" in str(exc_info.value)

        # Test too many features
        features = ["Feature " + str(i) for i in range(11)]  # 11 features
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=features
            )
        assert "at most 10 items" in str(exc_info.value)

    def test_project_empty_features_validation(self):
        # Test empty features
        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=self.get_valid_technologies(),
                features=["Feature 1", "", "Feature 3"]
            )
        assert "Features cannot be empty" in str(exc_info.value)

    def test_project_technology_type_validation(self):
        # Test missing frontend/backend/framework technology
        technologies = [
            Technology(
                name="MySQL",
                type=TechnologyType.DATABASE,
                reason="For data storage"
            ),
            Technology(
                name="Docker",
                type=TechnologyType.TOOL,
                reason="For containerization"
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            Project(
                title="Task Manager",
                description="An application for managing tasks with features.",
                difficulty=DifficultyLevel.INTERMEDIATE,
                estimated_time="2-3 days",
                category="Productivity",
                technologies=technologies,
                features=self.get_valid_features()
            )
        assert "Must include at least one frontend, backend or framework technology" in str(exc_info.value)

    def test_project_with_framework_technology(self):
        # Test with framework technology (should be valid)
        technologies = [
            Technology(
                name="Django",
                type=TechnologyType.FRAMEWORK,
                reason="Full-stack web framework"
            ),
            Technology(
                name="PostgreSQL",
                type=TechnologyType.DATABASE,
                reason="For data storage"
            )
        ]

        project = Project(
            title="Task Manager",
            description="An application for managing tasks with features.",
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time="2-3 days",
            category="Productivity",
            technologies=technologies,
            features=self.get_valid_features()
        )

        assert project.technologies[0].type == TechnologyType.FRAMEWORK

    def test_project_optional_fields(self):
        project = Project(
            title="Task Manager",
            description="An application for managing tasks with features.",
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time="2-3 days",
            category="Productivity",
            technologies=self.get_valid_technologies(),
            features=self.get_valid_features()
        )

        # Optional fields should be None by default
        assert project.id is None
        assert project.generated_at is None

    def test_project_with_generated_at(self):
        timestamp = datetime.now()
        project = Project(
            title="Task Manager",
            description="An application for managing tasks with features.",
            difficulty=DifficultyLevel.INTERMEDIATE,
            estimated_time="2-3 days",
            category="Productivity",
            technologies=self.get_valid_technologies(),
            features=self.get_valid_features(),
            generated_at=timestamp
        )

        assert project.generated_at == timestamp


class TestProjectCreateRequest:
    """Test ProjectCreateRequest model"""

    def test_valid_request(self):
        request = ProjectCreateRequest(
            count=5,
            difficulty_preference=[DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED],
            category_preference="Web Development"
        )

        assert request.count == 5
        assert DifficultyLevel.INTERMEDIATE in request.difficulty_preference
        assert request.category_preference == "Web Development"

    def test_default_values(self):
        request = ProjectCreateRequest()

        assert request.count == 5
        assert request.difficulty_preference is None
        assert request.category_preference is None

    def test_count_validation(self):
        # Test count too low
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(count=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Test count too high
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(count=11)
        assert "less than or equal to 10" in str(exc_info.value)

    def test_category_preference_validation(self):
        # Test category too long
        with pytest.raises(ValidationError) as exc_info:
            ProjectCreateRequest(
                count=5,
                category_preference="a" * 51
            )
        assert "at most 50 characters" in str(exc_info.value)

    def test_valid_difficulty_preferences(self):
        request = ProjectCreateRequest(
            count=3,
            difficulty_preference=[DifficultyLevel.BEGINNER]
        )

        assert len(request.difficulty_preference) == 1
        assert request.difficulty_preference[0] == DifficultyLevel.BEGINNER

    def test_mixed_difficulty_preferences(self):
        request = ProjectCreateRequest(
            count=5,
            difficulty_preference=[
                DifficultyLevel.BEGINNER,
                DifficultyLevel.INTERMEDIATE,
                DifficultyLevel.ADVANCED
            ]
        )

        assert len(request.difficulty_preference) == 3
        assert DifficultyLevel.BEGINNER in request.difficulty_preference
        assert DifficultyLevel.INTERMEDIATE in request.difficulty_preference
        assert DifficultyLevel.ADVANCED in request.difficulty_preference