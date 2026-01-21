"""
Unit tests for CHUNK-028: Database Service - Book Settings

Tests database service - book settings functionality.

Test Coverage:
- Settings retrieval
- Settings update
- Single-row handling
- Defaults
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal


class TestChunk028DatabaseServiceBookSettings:
    """Test suite for CHUNK-028: Database Service - Book Settings"""

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_happy_path_settings_retrieval(self, mock_get_table, mock_session_cls):
        """Test settings retrieval"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Mock database result
        mock_row = Mock()
        mock_row.special_instructions = 'Focus on code examples'
        mock_row.language_setting = 'english'
        mock_row.extraction_sensitivity = 'balanced'
        mock_row.image_processing = 'all'
        mock_row.ocr_quality = 'high'
        mock_row.hierarchy_detection = 'auto'
        mock_row.auto_detect_chapters = True
        mock_row.auto_detect_topics = True
        mock_row.partial_processing_enabled = False
        mock_row.partial_processing_pages = None
        mock_row.ocr_retry_enabled = True
        mock_row.ocr_retry_max_attempts = 3
        mock_row.ocr_zoom_factor = Decimal('2.0')
        mock_row.image_max_width = 800
        mock_row.image_max_height = 600
        mock_row.image_compression = 'lz4'
        mock_row.thumbnail_size = 200
        mock_row.checkpoint_frequency = 50
        mock_row.batch_insert_size = 50
        mock_row.created_at = datetime(2025, 1, 1, 10, 0, 0)
        mock_row.updated_at = datetime(2025, 1, 1, 12, 0, 0)

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()
        settings = service.get_settings(book_id=1)

        assert settings['language_setting'] == 'english'
        assert settings['ocr_quality'] == 'high'
        assert settings['auto_detect_chapters'] is True
        assert settings['image_max_width'] == 800
        assert settings['checkpoint_frequency'] == 50
        mock_db.close.assert_called_once()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_error_handling(self, mock_get_table, mock_session_cls):
        """Test error scenarios"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Mock database error during UPDATE
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        with pytest.raises(Exception, match="Database error"):
            service.update_settings(book_id=1, updates={'language_setting': 'english'})

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_edge_cases(self, mock_get_table, mock_session_cls):
        """Test boundary conditions"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        # Empty updates should succeed
        success = service.update_settings(book_id=1, updates={})
        assert success is True

        # Should not call database for empty updates
        mock_db.execute.assert_not_called()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_input_validation(self, mock_get_table, mock_session_cls):
        """Test input validation"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        # Multiple settings update
        updates = {
            'language_setting': 'both',
            'ocr_quality': 'high',
            'checkpoint_frequency': 100,
            'auto_detect_chapters': False
        }

        success = service.update_settings(book_id=1, updates=updates)
        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_settings_update(self, mock_get_table, mock_session_cls):
        """Test settings update"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        # Update single setting
        updates = {'language_setting': 'arabic'}
        success = service.update_settings(book_id=1, updates=updates)

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_single_row_handling(self, mock_get_table, mock_session_cls):
        """Test single-row handling"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Verify UPDATE always targets id=1
        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        updates = {'ocr_quality': 'fast'}
        service.update_settings(book_id=1, updates=updates)

        # Check that SQL contains "WHERE id = 1"
        call_args = mock_db.execute.call_args
        sql_text = str(call_args[0][0])
        assert 'WHERE id = 1' in sql_text

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_defaults(self, mock_get_table, mock_session_cls):
        """Test defaults"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Mock default settings
        mock_row = Mock()
        mock_row.special_instructions = None
        mock_row.language_setting = 'auto'  # Default
        mock_row.extraction_sensitivity = 'balanced'  # Default
        mock_row.image_processing = 'all'  # Default
        mock_row.ocr_quality = 'balanced'  # Default
        mock_row.hierarchy_detection = 'auto'  # Default
        mock_row.auto_detect_chapters = True  # Default
        mock_row.auto_detect_topics = True  # Default
        mock_row.partial_processing_enabled = False  # Default
        mock_row.partial_processing_pages = None
        mock_row.ocr_retry_enabled = True  # Default
        mock_row.ocr_retry_max_attempts = 3  # Default
        mock_row.ocr_zoom_factor = Decimal('2.0')  # Default
        mock_row.image_max_width = 800  # Default
        mock_row.image_max_height = 600  # Default
        mock_row.image_compression = 'lz4'  # Default
        mock_row.thumbnail_size = 200  # Default
        mock_row.checkpoint_frequency = 50  # Default
        mock_row.batch_insert_size = 50  # Default
        mock_row.created_at = datetime.now()
        mock_row.updated_at = datetime.now()

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()
        settings = service.get_settings(book_id=1)

        # Verify all defaults
        assert settings['language_setting'] == 'auto'
        assert settings['extraction_sensitivity'] == 'balanced'
        assert settings['ocr_quality'] == 'balanced'
        assert settings['auto_detect_chapters'] is True
        assert settings['auto_detect_topics'] is True
        assert settings['partial_processing_enabled'] is False
        assert settings['ocr_retry_enabled'] is True
        assert settings['ocr_retry_max_attempts'] == 3
        assert settings['checkpoint_frequency'] == 50
        assert settings['batch_insert_size'] == 50

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_get_settings_not_found(self, mock_get_table, mock_session_cls):
        """Test get_settings when settings don't exist"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Mock no result
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        with pytest.raises(ValueError, match="Settings not found"):
            service.get_settings(book_id=1)

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_get_single_setting(self, mock_get_table, mock_session_cls):
        """Test retrieving a single setting"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        # Mock single field result
        mock_row = ('english',)
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()
        lang = service.get_setting(book_id=1, setting_name='language_setting')

        assert lang == 'english'
        mock_db.close.assert_called_once()

    @patch('src.database.services.book_settings_service.SessionLocal')
    @patch('src.database.services.book_settings_service.get_table_name')
    def test_partial_processing_settings(self, mock_get_table, mock_session_cls):
        """Test partial processing settings"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_settings'

        from src.database.services.book_settings_service import BookSettingsService

        service = BookSettingsService()

        # Enable partial processing for first 10 pages
        updates = {
            'partial_processing_enabled': True,
            'partial_processing_pages': 10
        }

        success = service.update_settings(book_id=1, updates=updates)
        assert success is True
        mock_db.commit.assert_called_once()
