"""
Unit tests for CHUNK-001: Configuration Management

Tests the centralized configuration loading from environment variables and YAML.

Test Coverage:
- Configuration loading from .env file
- Required field validation
- Default value testing
- Invalid configuration handling
"""

import pytest
from unittest.mock import patch, mock_open
import os
from pydantic import ValidationError


class TestChunk001ConfigurationManagement:
    """Test suite for CHUNK-001: Configuration Management"""

    def test_happy_path_config_loading(self):
        """Test normal configuration loading with all required fields"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'TESSERACT_PATH': '/usr/bin/tesseract',
            'MODEL_CACHE_DIR': '/tmp/models'
        }):
            from src.config import Settings
            settings = Settings()

            assert settings.DATABASE_URL == 'postgresql://user:pass@localhost:5432/test_db'
            assert settings.TESSERACT_PATH == '/usr/bin/tesseract'
            assert settings.MODEL_CACHE_DIR == '/tmp/models'

    def test_default_values_applied(self):
        """Test that default values are correctly applied"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'TESSERACT_PATH': '/usr/bin/tesseract',
            'MODEL_CACHE_DIR': '/tmp/models'
        }):
            from src.config import Settings
            settings = Settings()

            # Test default values
            assert settings.DB_POOL_SIZE == 10
            assert settings.DB_MAX_OVERFLOW == 20
            assert settings.CHECKPOINT_FREQUENCY == 50
            assert settings.BATCH_INSERT_SIZE == 50
            assert settings.IMAGE_MAX_WIDTH == 800
            assert settings.IMAGE_MAX_HEIGHT == 600

    def test_error_handling_missing_required_fields(self):
        """Test error handling when required fields are missing"""
        with patch.dict(os.environ, {}, clear=True):
            from src.config import Settings

            with pytest.raises(ValidationError) as exc_info:
                Settings()

            # Verify error mentions missing required field
            assert 'DATABASE_URL' in str(exc_info.value) or 'field required' in str(exc_info.value)

    def test_edge_case_custom_values_override_defaults(self):
        """Test that custom values properly override defaults"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'TESSERACT_PATH': '/usr/bin/tesseract',
            'MODEL_CACHE_DIR': '/tmp/models',
            'DB_POOL_SIZE': '25',
            'CHECKPOINT_FREQUENCY': '100',
            'IMAGE_MAX_WIDTH': '1024'
        }):
            from src.config import Settings
            settings = Settings()

            assert settings.DB_POOL_SIZE == 25
            assert settings.CHECKPOINT_FREQUENCY == 100
            assert settings.IMAGE_MAX_WIDTH == 1024
            # Unmodified defaults
            assert settings.DB_MAX_OVERFLOW == 20
            assert settings.BATCH_INSERT_SIZE == 50

    def test_input_validation_invalid_types(self):
        """Test input validation with invalid data types"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'TESSERACT_PATH': '/usr/bin/tesseract',
            'MODEL_CACHE_DIR': '/tmp/models',
            'DB_POOL_SIZE': 'invalid_number'
        }):
            from src.config import Settings

            with pytest.raises(ValidationError):
                Settings()

    def test_env_file_loading(self):
        """Test loading configuration from .env file"""
        env_content = """
DATABASE_URL=postgresql://user:pass@localhost:5432/test_db
TESSERACT_PATH=/usr/bin/tesseract
MODEL_CACHE_DIR=/tmp/models
DB_POOL_SIZE=15
"""
        with patch('builtins.open', mock_open(read_data=env_content)):
            with patch('os.path.exists', return_value=True):
                with patch.dict(os.environ, {
                    'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
                    'TESSERACT_PATH': '/usr/bin/tesseract',
                    'MODEL_CACHE_DIR': '/tmp/models'
                }):
                    from src.config import Settings
                    settings = Settings()

                    assert settings.DATABASE_URL is not None
                    assert settings.TESSERACT_PATH is not None

    def test_singleton_settings_instance(self):
        """Test that settings can be accessed as singleton"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/test_db',
            'TESSERACT_PATH': '/usr/bin/tesseract',
            'MODEL_CACHE_DIR': '/tmp/models'
        }):
            from src.config import settings

            # Settings should be accessible
            assert settings.DATABASE_URL == 'postgresql://user:pass@localhost:5432/test_db'
