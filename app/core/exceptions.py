"""Custom exceptions for the application."""


class ProjectServiceError(Exception):
    """Exception raised for errors in the project service."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class AIServiceError(Exception):
    """Exception raised for errors in the AI service."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class RedisConnectionError(Exception):
    """Exception raised for Redis connection errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)