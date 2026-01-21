"""
Unit tests for CHUNK-026: Database Service - Pages CRUD

Tests database service - pages crud functionality.

Test Coverage:
- Page insertion
- Rectangle data storage
- Image compression
- Retrieval
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk026DatabaseServicePagesCRUD:
    """Test suite for CHUNK-026: Database Service - Pages CRUD"""

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    @patch('src.database.services.page_service.compress_image')
    def test_happy_path_page_insertion(self, mock_compress, mock_get_table, mock_session_cls):
        """Test page insertion with images and rectangles"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'
        mock_compress.side_effect = lambda img: b'compressed'

        from src.database.services.page_service import PageService

        service = PageService()

        page_data = {
            'page_number': 1,
            'page_image': Image.new('RGB', (800, 1000), color='white'),
            'marked_image': Image.new('RGB', (800, 1000), color='green'),
            'rectangle_data': {
                'green_rectangles': [{'x': 100, 'y': 200, 'width': 300, 'height': 50}],
                'orange_rectangles': [{'x': 500, 'y': 600, 'width': 100, 'height': 80}]
            }
        }

        success = service.insert_page(book_id=1, page_data=page_data)

        assert success is True
        # Should compress both original and marked images
        assert mock_compress.call_count == 2
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    @patch('src.database.services.page_service.compress_image')
    def test_rectangle_data_storage(self, mock_compress, mock_get_table, mock_session_cls):
        """Test that rectangle data is properly JSON serialized"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'
        mock_compress.side_effect = lambda img: b'compressed'

        # Capture the executed SQL parameters
        executed_params = None
        def capture_execute(sql, params):
            nonlocal executed_params
            executed_params = params
            return Mock()

        mock_db.execute.side_effect = capture_execute

        from src.database.services.page_service import PageService

        service = PageService()

        rectangles = {
            'green_rectangles': [
                {'x': 10, 'y': 20, 'width': 30, 'height': 40, 'knowledge_unit_id': 123}
            ],
            'orange_rectangles': [
                {'x': 50, 'y': 60, 'width': 70, 'height': 80, 'image_id': 'IMG-001-00'}
            ]
        }

        page_data = {
            'page_number': 1,
            'page_image': Image.new('RGB', (100, 100)),
            'marked_image': Image.new('RGB', (100, 100)),
            'rectangle_data': rectangles
        }

        service.insert_page(book_id=1, page_data=page_data)

        # Verify JSON conversion
        assert executed_params is not None
        import json
        assert json.loads(executed_params['green_rectangles']) == rectangles['green_rectangles']
        assert json.loads(executed_params['orange_rectangles']) == rectangles['orange_rectangles']

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    @patch('src.database.services.page_service.compress_image')
    def test_empty_rectangles(self, mock_compress, mock_get_table, mock_session_cls):
        """Test page with empty rectangle lists"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'
        mock_compress.side_effect = lambda img: b'compressed'

        from src.database.services.page_service import PageService

        service = PageService()

        page_data = {
            'page_number': 1,
            'page_image': Image.new('RGB', (100, 100)),
            'marked_image': Image.new('RGB', (100, 100)),
            'rectangle_data': {
                'green_rectangles': [],
                'orange_rectangles': []
            }
        }

        success = service.insert_page(book_id=1, page_data=page_data)
        assert success is True

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    @patch('src.database.services.page_service.decompress_image')
    def test_get_page_with_images(self, mock_decompress, mock_get_table, mock_session_cls):
        """Test retrieving page with images"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        # Mock database row
        import json
        mock_row = Mock()
        mock_row.page_number = 1
        mock_row.original_image_data = b'compressed_original'
        mock_row.marked_image_data = b'compressed_marked'
        mock_row.green_rectangles = json.dumps([{'x': 10, 'y': 20}])
        mock_row.orange_rectangles = json.dumps([{'x': 50, 'y': 60}])
        mock_row.marker_generated = True
        mock_row.marker_generated_at = None

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Mock decompression
        original_img = Image.new('RGB', (800, 1000), color='white')
        marked_img = Image.new('RGB', (800, 1000), color='green')
        mock_decompress.side_effect = [original_img, marked_img]

        from src.database.services.page_service import PageService

        service = PageService()
        page_data = service.get_page(book_id=1, page_number=1, include_images=True)

        assert page_data['page_number'] == 1
        assert len(page_data['green_rectangles']) == 1
        assert len(page_data['orange_rectangles']) == 1
        assert page_data['original_image'] == original_img
        assert page_data['marked_image'] == marked_img
        assert mock_decompress.call_count == 2

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    def test_get_page_without_images(self, mock_get_table, mock_session_cls):
        """Test retrieving page metadata without images"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        import json
        mock_row = Mock()
        mock_row.page_number = 1
        mock_row.green_rectangles = json.dumps([])
        mock_row.orange_rectangles = json.dumps([])
        mock_row.marker_generated = True
        mock_row.marker_generated_at = None

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        from src.database.services.page_service import PageService

        service = PageService()
        page_data = service.get_page(book_id=1, page_number=1, include_images=False)

        assert page_data['page_number'] == 1
        assert 'original_image' not in page_data
        assert 'marked_image' not in page_data

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    def test_get_page_not_found(self, mock_get_table, mock_session_cls):
        """Test retrieving non-existent page"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        from src.database.services.page_service import PageService

        service = PageService()

        with pytest.raises(ValueError, match="Page 999 not found"):
            service.get_page(book_id=1, page_number=999)

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    def test_get_page_count(self, mock_get_table, mock_session_cls):
        """Test getting total page count"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        from src.database.services.page_service import PageService

        service = PageService()
        count = service.get_page_count(book_id=1)

        assert count == 42

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    def test_delete_page(self, mock_get_table, mock_session_cls):
        """Test deleting a page"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        from src.database.services.page_service import PageService

        service = PageService()
        success = service.delete_page(book_id=1, page_number=5)

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    def test_delete_page_not_found(self, mock_get_table, mock_session_cls):
        """Test deleting non-existent page"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'

        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        from src.database.services.page_service import PageService

        service = PageService()
        success = service.delete_page(book_id=1, page_number=999)

        assert success is False

    @patch('src.database.services.page_service.SessionLocal')
    @patch('src.database.services.page_service.get_table_name')
    @patch('src.database.services.page_service.compress_image')
    def test_insert_rollback_on_error(self, mock_compress, mock_get_table, mock_session_cls):
        """Test that insert rolls back on error"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_pages'
        mock_compress.side_effect = lambda img: b'compressed'

        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.page_service import PageService

        service = PageService()
        page_data = {
            'page_number': 1,
            'page_image': Image.new('RGB', (100, 100)),
            'marked_image': Image.new('RGB', (100, 100)),
            'rectangle_data': {'green_rectangles': [], 'orange_rectangles': []}
        }

        with pytest.raises(Exception, match="Database error"):
            service.insert_page(book_id=1, page_data=page_data)

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
