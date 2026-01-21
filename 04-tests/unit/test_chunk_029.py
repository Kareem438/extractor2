"""
Unit tests for CHUNK-029: Database Service - Attribute Keys

Tests database service - attribute keys functionality.

Test Coverage:
- Key retrieval
- Key updates
- Attr1-8 protection
- 40 attributes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestChunk029DatabaseServiceAttributeKeys:
    """Test suite for CHUNK-029: Database Service - Attribute Keys"""

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_happy_path_key_retrieval(self, mock_get_table, mock_session_cls):
        """Test key retrieval"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock 40 attribute keys
        mock_rows = [
            Mock(attr_number=1, key_name='related_image'),
            Mock(attr_number=2, key_name='ocr_text_paddleocr'),
            Mock(attr_number=3, key_name='ocr_text_surya'),
            Mock(attr_number=9, key_name='Difficulty Level'),
            Mock(attr_number=18, key_name='Source Reference'),
            Mock(attr_number=40, key_name='')
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()
        keys = service.get_attribute_keys(book_id=1)

        assert keys[1] == 'related_image'
        assert keys[2] == 'ocr_text_paddleocr'
        assert keys[9] == 'Difficulty Level'
        assert len(keys) == 6
        mock_db.close.assert_called_once()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_error_handling(self, mock_get_table, mock_session_cls):
        """Test error scenarios"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock database error during UPDATE
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        with pytest.raises(Exception, match="Database error"):
            service.update_attribute_keys(book_id=1, key_updates={9: 'Custom Name'})

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_edge_cases(self, mock_get_table, mock_session_cls):
        """Test boundary conditions"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        # Empty updates should succeed
        success = service.update_attribute_keys(book_id=1, key_updates={})
        assert success is True

        # Should not call database for empty updates
        mock_db.execute.assert_not_called()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_input_validation(self, mock_get_table, mock_session_cls):
        """Test input validation"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        # Multiple key updates (attributes 9-40 are editable)
        updates = {
            9: 'Custom Difficulty',
            18: 'Source Reference',
            19: 'Related Topics'
        }

        success = service.update_attribute_keys(book_id=1, key_updates=updates)
        assert success is True
        # Should call execute 3 times (one per update)
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_key_updates(self, mock_get_table, mock_session_cls):
        """Test key updates"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        # Update single user-defined attribute (9-40)
        updates = {18: 'Source Reference'}
        success = service.update_attribute_keys(book_id=1, key_updates=updates)

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_attr1_protection(self, mock_get_table, mock_session_cls):
        """Test attr1-8 (system-reserved) protection"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        # Attempt to edit attribute 1 (system-reserved)
        with pytest.raises(ValueError, match="Cannot edit system-reserved attributes"):
            service.update_attribute_keys(book_id=1, key_updates={1: 'custom_name'})

        # Attempt to edit attribute 8 (system-reserved)
        with pytest.raises(ValueError, match="Cannot edit system-reserved attributes"):
            service.update_attribute_keys(book_id=1, key_updates={8: 'custom_status'})

        # Attempt to edit multiple system-reserved attributes
        with pytest.raises(ValueError, match="Cannot edit system-reserved attributes"):
            service.update_attribute_keys(book_id=1, key_updates={
                1: 'custom1',
                5: 'custom5',
                9: 'Custom9'  # 9 is editable, but 1 and 5 are not
            })

        # Should not have committed anything
        mock_db.commit.assert_not_called()

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_30_attributes(self, mock_get_table, mock_session_cls):
        """Test 80 attributes total (8 system + 72 user-defined)"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock all 80 attributes
        mock_rows = [
            Mock(attr_number=i, key_name=f'attr_{i}')
            for i in range(1, 81)
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()
        keys = service.get_attribute_keys(book_id=1)

        # Should have exactly 80 attributes
        assert len(keys) == 80
        assert 1 in keys
        assert 8 in keys
        assert 9 in keys  # First user-defined
        assert 80 in keys  # Last user-defined

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_get_attribute_key_details(self, mock_get_table, mock_session_cls):
        """Test retrieving full attribute key details"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock attribute key details
        mock_rows = [
            Mock(
                attr_number=1,
                key_name='related_image',
                is_system_reserved=True,
                is_editable=False,
                description='System-reserved: Links to related images',
                placeholder_example='image_id:IMG-XX',
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            Mock(
                attr_number=9,
                key_name='Difficulty Level',
                is_system_reserved=False,
                is_editable=True,
                description='Difficulty: Beginner, Intermediate, Advanced',
                placeholder_example='Intermediate',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()
        details = service.get_attribute_key_details(book_id=1)

        assert len(details) == 2
        assert details[0]['attr_number'] == 1
        assert details[0]['is_system_reserved'] is True
        assert details[0]['is_editable'] is False
        assert details[1]['attr_number'] == 9
        assert details[1]['is_system_reserved'] is False
        assert details[1]['is_editable'] is True

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_get_user_defined_keys(self, mock_get_table, mock_session_cls):
        """Test retrieving only user-defined keys (9-80)"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock user-defined attributes (9-80 = 72 attributes)
        mock_rows = [
            Mock(attr_number=i, key_name=f'User Attr {i}')
            for i in range(9, 81)
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()
        keys = service.get_user_defined_keys(book_id=1)

        # Should have exactly 72 user-defined attributes
        assert len(keys) == 72
        assert 9 in keys
        assert 80 in keys
        assert 1 not in keys  # System-reserved
        assert 8 not in keys  # System-reserved

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_get_system_reserved_keys(self, mock_get_table, mock_session_cls):
        """Test retrieving only system-reserved keys (1-8)"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        # Mock system-reserved attributes (1-8)
        mock_rows = [
            Mock(attr_number=1, key_name='related_image'),
            Mock(attr_number=2, key_name='ocr_text_paddleocr'),
            Mock(attr_number=3, key_name='ocr_text_surya'),
            Mock(attr_number=4, key_name='ocr_text_tesseract'),
            Mock(attr_number=5, key_name='ocr_confidence_paddleocr'),
            Mock(attr_number=6, key_name='ocr_confidence_surya'),
            Mock(attr_number=7, key_name='ocr_confidence_tesseract'),
            Mock(attr_number=8, key_name='record_status')
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()
        keys = service.get_system_reserved_keys(book_id=1)

        # Should have exactly 8 system-reserved attributes
        assert len(keys) == 8
        assert keys[1] == 'related_image'
        assert keys[8] == 'record_status'
        assert 9 not in keys  # User-defined

    @patch('src.database.services.attribute_key_service.SessionLocal')
    @patch('src.database.services.attribute_key_service.get_table_name')
    def test_boundary_attribute_numbers(self, mock_get_table, mock_session_cls):
        """Test boundary attribute numbers (8, 9, 80)"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_attribute_keys'

        from src.database.services.attribute_key_service import AttributeKeyService

        service = AttributeKeyService()

        # Attribute 8 is system-reserved (last reserved)
        with pytest.raises(ValueError, match="Cannot edit system-reserved attributes"):
            service.update_attribute_keys(book_id=1, key_updates={8: 'custom'})

        # Attribute 9 is user-defined (first user-defined) - should succeed
        success = service.update_attribute_keys(book_id=1, key_updates={9: 'Custom 9'})
        assert success is True

        # Attribute 80 is user-defined (last attribute) - should succeed
        mock_db.execute.reset_mock()
        mock_db.commit.reset_mock()
        success = service.update_attribute_keys(book_id=1, key_updates={80: 'Custom 80'})
        assert success is True
