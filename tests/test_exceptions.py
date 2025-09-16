import pytest

from app.core.exceptions import (
    ProjectServiceError,
    AIServiceError,
    RedisConnectionError,
    RateLimitError,
    ValidationError
)


class TestCustomExceptions:
    """Test custom exception classes"""

    def test_project_service_error(self):
        """Test ProjectServiceError exception"""
        message = "Project service failed"
        details = "Database connection lost"

        exc = ProjectServiceError(message, details)

        assert str(exc) == message
        assert exc.message == message
        assert exc.details == details

    def test_project_service_error_without_details(self):
        """Test ProjectServiceError without details"""
        message = "Project service failed"

        exc = ProjectServiceError(message)

        assert str(exc) == message
        assert exc.message == message
        assert exc.details is None

    def test_ai_service_error(self):
        """Test AIServiceError exception"""
        message = "AI service failed"
        details = "API rate limit exceeded"

        exc = AIServiceError(message, details)

        assert str(exc) == message
        assert exc.message == message
        assert exc.details == details

    def test_ai_service_error_without_details(self):
        """Test AIServiceError without details"""
        message = "AI service failed"

        exc = AIServiceError(message)

        assert str(exc) == message
        assert exc.message == message
        assert exc.details is None

    def test_redis_connection_error(self):
        """Test RedisConnectionError exception"""
        message = "Could not connect to Redis"

        exc = RedisConnectionError(message)

        assert str(exc) == message
        assert exc.message == message

    def test_rate_limit_error_default_message(self):
        """Test RateLimitError with default message"""
        exc = RateLimitError()

        assert str(exc) == "Rate limit exceeded"
        assert exc.message == "Rate limit exceeded"

    def test_rate_limit_error_custom_message(self):
        """Test RateLimitError with custom message"""
        message = "Too many requests per minute"

        exc = RateLimitError(message)

        assert str(exc) == message
        assert exc.message == message

    def test_validation_error(self):
        """Test ValidationError exception"""
        message = "Invalid input data"
        field = "email"

        exc = ValidationError(message, field)

        assert str(exc) == message
        assert exc.message == message
        assert exc.field == field

    def test_validation_error_without_field(self):
        """Test ValidationError without field"""
        message = "Invalid input data"

        exc = ValidationError(message)

        assert str(exc) == message
        assert exc.message == message
        assert exc.field is None

    def test_exception_inheritance(self):
        """Test that custom exceptions inherit from Exception"""
        assert issubclass(ProjectServiceError, Exception)
        assert issubclass(AIServiceError, Exception)
        assert issubclass(RedisConnectionError, Exception)
        assert issubclass(RateLimitError, Exception)
        assert issubclass(ValidationError, Exception)

    def test_exception_raising(self):
        """Test that exceptions can be raised and caught"""
        # Test ProjectServiceError
        with pytest.raises(ProjectServiceError) as exc_info:
            raise ProjectServiceError("Test error")
        assert "Test error" in str(exc_info.value)

        # Test AIServiceError
        with pytest.raises(AIServiceError) as exc_info:
            raise AIServiceError("AI error")
        assert "AI error" in str(exc_info.value)

        # Test RedisConnectionError
        with pytest.raises(RedisConnectionError) as exc_info:
            raise RedisConnectionError("Redis error")
        assert "Redis error" in str(exc_info.value)

        # Test RateLimitError
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("Rate limit error")
        assert "Rate limit error" in str(exc_info.value)

        # Test ValidationError
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Validation error")
        assert "Validation error" in str(exc_info.value)