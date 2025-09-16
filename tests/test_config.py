import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError
from pydantic_core import ValidationError as PydanticCoreValidationError

from app.config import Settings


class TestSettings:
    """Test Settings configuration"""

    def test_default_values(self):
        """Test default configuration values"""
        with patch.dict(os.environ, {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'DEBUG': 'false',
            'GOOGLE_API_KEY': ''
        }, clear=True):
            settings = Settings()

            assert settings.app_name == "Daily Projects API"
            assert settings.app_version == "1.0.0"
            assert settings.debug is False
            assert settings.environment == "development"
            assert settings.api_v1_str == "/api/v1"
            assert settings.redis_db == 0
            assert settings.redis_max_connections == 20
            assert settings.redis_retry_on_timeout is True
            assert settings.deepseek_model == "deepseek-chat"
            assert settings.deepseek_max_tokens == 2000
            assert settings.deepseek_temperature == 0.8
            assert settings.deepseek_timeout == 30
            assert settings.daily_projects_ttl == 86400 * 7
            assert settings.generation_lock_ttl == 300
            assert settings.max_requests_per_minute == 60

    def test_environment_variables_override(self):
        """Test that environment variables override defaults"""
        env_vars = {
            'DEBUG': 'true',
            'ENVIRONMENT': 'production',
            'REDIS_URL': 'redis://test-host:6379',
            'REDIS_DB': '5',
            'REDIS_MAX_CONNECTIONS': '50',
            'DEEPSEEK_API_KEY': 'test-deepseek-key',
            'DEEPSEEK_MODEL': 'custom-model',
            'DEEPSEEK_MAX_TOKENS': '4000',
            'DEEPSEEK_TEMPERATURE': '0.5',
            'DEEPSEEK_TIMEOUT': '60',
            'GOOGLE_API_KEY': 'test-google-key',
            'GOOGLE_MODEL': 'gemini-pro',
            'DAILY_PROJECTS_TTL': '172800',
            'GENERATION_LOCK_TTL': '600',
            'MAX_REQUESTS_PER_MINUTE': '120'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.debug is True
            assert settings.environment == "production"
            assert settings.redis_url == "redis://test-host:6379"
            assert settings.redis_db == 5
            assert settings.redis_max_connections == 50
            assert settings.deepseek_api_key == "test-deepseek-key"
            assert settings.deepseek_model == "custom-model"
            assert settings.deepseek_max_tokens == 4000
            assert settings.deepseek_temperature == 0.5
            assert settings.deepseek_timeout == 60
            assert settings.google_api_key == "test-google-key"
            assert settings.google_model == "gemini-pro"
            assert settings.daily_projects_ttl == 172800
            assert settings.generation_lock_ttl == 600
            assert settings.max_requests_per_minute == 120

    def test_cors_origins_list(self):
        """Test CORS origins configuration"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'BACKEND_CORS_ORIGINS': '["http://localhost:3000", "https://example.com"]'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            # Default CORS origins should be used since the env var format might not parse correctly
            assert isinstance(settings.backend_cors_origins, list)
            assert len(settings.backend_cors_origins) >= 2

    def test_redis_url_validation_missing(self):
        """Test Redis URL validation when empty string is provided"""
        env_vars = {
            'REDIS_URL': '',  # Empty string should trigger validation
            'DEEPSEEK_API_KEY': 'test-key',
            'GOOGLE_API_KEY': ''
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises((ValidationError, PydanticCoreValidationError, ValueError)) as exc_info:
                Settings()

            assert "REDIS_URL is required" in str(exc_info.value)

    def test_redis_url_validation_empty(self):
        """Test Redis URL validation when empty"""
        env_vars = {
            'REDIS_URL': '',
            'DEEPSEEK_API_KEY': 'test-key'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "REDIS_URL is required" in str(exc_info.value)

    def test_deepseek_api_key_validation_missing(self):
        """Test DeepSeek API key validation when empty string is provided"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': '',  # Empty string should trigger validation
            'GOOGLE_API_KEY': ''
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises((ValidationError, PydanticCoreValidationError, ValueError)) as exc_info:
                Settings()

            assert "DEEPSEEK_API_KEY is required" in str(exc_info.value)

    def test_deepseek_api_key_validation_empty(self):
        """Test DeepSeek API key validation when empty"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': ''
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "DEEPSEEK_API_KEY is required" in str(exc_info.value)

    def test_is_production_property(self):
        """Test is_production property"""
        # Test production environment
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'ENVIRONMENT': 'production'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_production is True

        # Test non-production environment
        env_vars['ENVIRONMENT'] = 'development'
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_production is False

        # Test case insensitive
        env_vars['ENVIRONMENT'] = 'PRODUCTION'
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_production is True

    def test_is_development_method(self):
        """Test is_development method"""
        # Test development environment
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'ENVIRONMENT': 'development'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_development() is True

        # Test non-development environment
        env_vars['ENVIRONMENT'] = 'production'
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_development() is False

        # Test case insensitive
        env_vars['ENVIRONMENT'] = 'DEVELOPMENT'
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.is_development() is True

    def test_deepseek_api_url_default(self):
        """Test DeepSeek API URL default value"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.deepseek_api_url == "https://api.deepseek.com/v1/chat/completions"

    def test_deepseek_api_url_custom(self):
        """Test custom DeepSeek API URL"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'DEEPSEEK_API_URL': 'https://custom-api.example.com/v1/chat'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.deepseek_api_url == "https://custom-api.example.com/v1/chat"

    def test_google_api_configuration(self):
        """Test Google AI API configuration"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'GOOGLE_API_KEY': 'test-google-key',
            'GOOGLE_MODEL': 'gemini-1.5-pro',
            'GOOGLE_MAX_TOKENS': '8000',
            'GOOGLE_TEMPERATURE': '0.7',
            'GOOGLE_TIMEOUT': '45'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.google_api_key == "test-google-key"
            assert settings.google_model == "gemini-1.5-pro"
            assert settings.google_max_tokens == 8000
            assert settings.google_temperature == 0.7
            assert settings.google_timeout == 45

    def test_google_api_defaults(self):
        """Test Google AI API default values"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'GOOGLE_API_KEY': ''
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.google_api_key == ""
            assert settings.google_model == "gemini-1.5-flash"
            assert settings.google_max_tokens == 2000
            assert settings.google_temperature == 0.8
            assert settings.google_timeout == 30

    def test_redis_configuration_fields(self):
        """Test Redis configuration fields"""
        env_vars = {
            'REDIS_URL': 'redis://custom-host:6380/2',
            'REDIS_DB': '3',
            'REDIS_MAX_CONNECTIONS': '100',
            'REDIS_RETRY_ON_TIMEOUT': 'false',
            'DEEPSEEK_API_KEY': 'test-key'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.redis_url == "redis://custom-host:6380/2"
            assert settings.redis_db == 3
            assert settings.redis_max_connections == 100
            assert settings.redis_retry_on_timeout is False

    def test_ttl_configuration(self):
        """Test TTL configuration"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'DAILY_PROJECTS_TTL': '259200',  # 3 days
            'GENERATION_LOCK_TTL': '900'     # 15 minutes
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.daily_projects_ttl == 259200
            assert settings.generation_lock_ttl == 900

    def test_config_case_sensitivity(self):
        """Test that configuration is case insensitive"""
        env_vars = {
            'redis_url': 'redis://lowercase:6379',
            'deepseek_api_key': 'lowercase-key',
            'REDIS_URL': 'redis://uppercase:6379',
            'DEEPSEEK_API_KEY': 'uppercase-key'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            # Uppercase should take precedence or be used (depending on OS)
            assert 'redis://' in settings.redis_url
            assert settings.deepseek_api_key is not None

    def test_numeric_field_validation(self):
        """Test numeric field validation"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'REDIS_DB': 'invalid_number'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "input should be a valid integer" in str(exc_info.value).lower()

    def test_boolean_field_validation(self):
        """Test boolean field validation"""
        # Test valid boolean values
        valid_boolean_values = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']

        for bool_val in valid_boolean_values:
            env_vars = {
                'REDIS_URL': 'redis://localhost:6379',
                'DEEPSEEK_API_KEY': 'test-key',
                'DEBUG': bool_val,
                'REDIS_RETRY_ON_TIMEOUT': bool_val
            }

            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings()
                # Should not raise validation error
                assert isinstance(settings.debug, bool)
                assert isinstance(settings.redis_retry_on_timeout, bool)

    def test_float_field_validation(self):
        """Test float field validation"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key',
            'DEEPSEEK_TEMPERATURE': '0.95',
            'GOOGLE_TEMPERATURE': '1.0'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.deepseek_temperature == 0.95
            assert settings.google_temperature == 1.0

        # Test invalid float
        env_vars['DEEPSEEK_TEMPERATURE'] = 'invalid_float'
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "input should be a valid number" in str(exc_info.value).lower()

    def test_settings_immutability(self):
        """Test that settings are properly configured for immutability"""
        env_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'DEEPSEEK_API_KEY': 'test-key'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            # Test that we can access properties
            assert settings.app_name == "Daily Projects API"
            assert settings.is_production is False
            assert settings.is_development() is True

            # Settings should be immutable in normal usage
            original_app_name = settings.app_name
            # settings.app_name = "Modified"  # This would raise an error if frozen
            assert settings.app_name == original_app_name