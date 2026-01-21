"""
Unit tests for CHUNK-024: Database Service - Knowledge Units CRUD

Tests database service - knowledge units crud functionality.

Test Coverage:
- Batch insert
- Pagination
- Update operations
- Merge records
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestChunk024DatabaseServiceKnowledgeUnitsCRUD:
    """Test suite for CHUNK-024: Database Service - Knowledge Units CRUD"""

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_happy_path_batch_insert(self, mock_get_table, mock_session_cls):
        """Test batch insert of knowledge units"""
        # Mock database session
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()

        units = [
            {
                'text_content': 'Unit 1 text',
                'text_length': 11,
                'line_count': 1,
                'page_number': 1,
                'language': 'english',
                'confidence_score': 95.0
            },
            {
                'text_content': 'Unit 2 text',
                'text_length': 11,
                'line_count': 1,
                'page_number': 1,
                'language': 'english',
                'confidence_score': 90.0
            }
        ]

        count = service.insert_knowledge_units(book_id=1, knowledge_units=units)

        # Verify insert was called
        assert count == 2
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_empty_batch_insert(self, mock_get_table, mock_session_cls):
        """Test batch insert with empty list"""
        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        count = service.insert_knowledge_units(book_id=1, knowledge_units=[])

        # Should return 0 without database calls
        assert count == 0

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_batch_insert_with_optional_fields(self, mock_get_table, mock_session_cls):
        """Test batch insert with optional position fields"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()

        units = [
            {
                'text_content': 'Unit with position',
                'text_length': 19,
                'line_count': 1,
                'page_number': 1,
                'language': 'english',
                'confidence_score': 95.0,
                'position_x': 100,
                'position_y': 200,
                'position_width': 300,
                'position_height': 50
            }
        ]

        count = service.insert_knowledge_units(book_id=1, knowledge_units=units)

        assert count == 1
        mock_db.execute.assert_called_once()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_get_knowledge_units_pagination(self, mock_get_table, mock_session_cls):
        """Test paginated retrieval of knowledge units"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 100

        # Mock data query
        mock_data_result = Mock()
        mock_data_result.__iter__ = lambda self: iter([
            Mock(_mapping={'id': 1, 'text_content': 'Unit 1', 'page_number': 1, 'verified': False}),
            Mock(_mapping={'id': 2, 'text_content': 'Unit 2', 'page_number': 1, 'verified': False})
        ])

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        result = service.get_knowledge_units(book_id=1, page=1, limit=2)

        assert result['total'] == 100
        assert result['page'] == 1
        assert result['limit'] == 2
        assert result['has_more'] is True
        assert len(result['records']) == 2
        mock_db.close.assert_called_once()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_get_knowledge_units_with_verified_filter(self, mock_get_table, mock_session_cls):
        """Test retrieval with verified filter"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 10
        mock_data_result = Mock()
        mock_data_result.__iter__ = lambda self: iter([])

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        result = service.get_knowledge_units(book_id=1, page=1, limit=50, verified=True)

        # Verify that the WHERE clause includes verified filter
        assert result['total'] == 10
        mock_db.execute.assert_called()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_get_knowledge_units_with_page_number_filter(self, mock_get_table, mock_session_cls):
        """Test retrieval with page_number filter"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 5
        mock_data_result = Mock()
        mock_data_result.__iter__ = lambda self: iter([])

        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        result = service.get_knowledge_units(book_id=1, page_number=5)

        assert result['total'] == 5

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_update_knowledge_unit(self, mock_get_table, mock_session_cls):
        """Test updating a single knowledge unit"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock successful update (1 row affected)
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        updates = {
            'verified': True,
            'chapter': 'Chapter 1'
        }
        success = service.update_knowledge_unit(book_id=1, record_id=123, updates=updates)

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_update_knowledge_unit_not_found(self, mock_get_table, mock_session_cls):
        """Test updating non-existent record"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock no rows affected
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        success = service.update_knowledge_unit(book_id=1, record_id=999, updates={'verified': True})

        assert success is False

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_update_knowledge_unit_empty_updates(self, mock_get_table, mock_session_cls):
        """Test update with empty updates dict"""
        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        success = service.update_knowledge_unit(book_id=1, record_id=123, updates={})

        assert success is False

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_merge_knowledge_units(self, mock_get_table, mock_session_cls):
        """Test merging two knowledge units"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock fetching both records
        keep_record = Mock()
        keep_record.id = 100
        keep_record.text_content = 'Keep text'
        keep_record.text_length = 9
        keep_record.original_record_ids = []

        delete_record = Mock()
        delete_record.id = 101
        delete_record.text_content = 'Delete text'
        delete_record.text_length = 11
        delete_record.original_record_ids = []

        mock_db.execute.side_effect = [
            Mock(fetchone=lambda: keep_record),   # Get keep record
            Mock(fetchone=lambda: delete_record),  # Get delete record
            Mock(),  # Update keep record
            Mock()   # Update delete record
        ]

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        success = service.merge_knowledge_units(book_id=1, keep_id=100, delete_id=101)

        assert success is True
        assert mock_db.execute.call_count == 4  # 2 selects + 2 updates
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_merge_knowledge_units_not_found(self, mock_get_table, mock_session_cls):
        """Test merging when one record doesn't exist"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock keep record exists but delete record doesn't
        mock_db.execute.side_effect = [
            Mock(fetchone=lambda: Mock(id=100, text_content='Text', original_record_ids=[])),
            Mock(fetchone=lambda: None)  # Delete record not found
        ]

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        success = service.merge_knowledge_units(book_id=1, keep_id=100, delete_id=999)

        assert success is False
        # Should not commit if records not found
        mock_db.commit.assert_not_called()

    @patch('src.database.services.knowledge_unit_service.SessionLocal')
    @patch('src.database.services.knowledge_unit_service.get_table_name')
    def test_batch_insert_rollback_on_error(self, mock_get_table, mock_session_cls):
        """Test that batch insert rolls back on error"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_knowledge_units'

        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.knowledge_unit_service import KnowledgeUnitService

        service = KnowledgeUnitService()
        units = [
            {
                'text_content': 'Test',
                'text_length': 4,
                'line_count': 1,
                'page_number': 1,
                'language': 'english',
                'confidence_score': 95.0
            }
        ]

        with pytest.raises(Exception, match="Database error"):
            service.insert_knowledge_units(book_id=1, knowledge_units=units)

        # Should rollback on error
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
