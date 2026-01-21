"""
Unit tests for CHUNK-025: Database Service - Images CRUD

Tests database service - images crud functionality.

Test Coverage:
- Image insertion
- Compression
- Thumbnail generation
- Retrieval
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk025DatabaseServiceImagesCRUD:
    """Test suite for CHUNK-025: Database Service - Images CRUD"""

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.compress_image')
    def test_happy_path_image_insertion(self, mock_compress, mock_get_table, mock_session_cls):
        """Test image insertion with compression"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock compression to return bytes
        mock_compress.side_effect = lambda img: b'compressed_data'

        from src.database.services.image_service import ImageService

        service = ImageService()

        test_image = Image.new('RGB', (400, 300), color='white')
        images = [
            {
                'image_id': 'IMG-001-00',
                'page_number': 1,
                'image_data': test_image,
                'ai_description': 'A white image',
                'confidence_score': 85.0,
                'image_type': 'diagram'
            }
        ]

        count = service.insert_images(book_id=1, images=images)

        assert count == 1
        # Should compress both full image and thumbnail
        assert mock_compress.call_count == 2
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.compress_image')
    def test_empty_images_list(self, mock_compress, mock_get_table, mock_session_cls):
        """Test insertion with empty list"""
        from src.database.services.image_service import ImageService

        service = ImageService()
        count = service.insert_images(book_id=1, images=[])

        assert count == 0
        # Should not call database
        mock_session_cls.assert_not_called()

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.compress_image')
    def test_multiple_images_insertion(self, mock_compress, mock_get_table, mock_session_cls):
        """Test inserting multiple images"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'
        mock_compress.side_effect = lambda img: b'compressed'

        from src.database.services.image_service import ImageService

        service = ImageService()

        images = [
            {'image_id': 'IMG-001-00', 'page_number': 1, 'image_data': Image.new('RGB', (100, 100))},
            {'image_id': 'IMG-001-01', 'page_number': 1, 'image_data': Image.new('RGB', (200, 200))},
            {'image_id': 'IMG-002-00', 'page_number': 2, 'image_data': Image.new('RGB', (150, 150))}
        ]

        count = service.insert_images(book_id=1, images=images)

        assert count == 3
        # 3 images * 2 compressions each (full + thumbnail) = 6
        assert mock_compress.call_count == 6
        # Should execute 3 inserts
        assert mock_db.execute.call_count == 3

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.compress_image')
    def test_thumbnail_generation(self, mock_compress, mock_get_table, mock_session_cls):
        """Test that thumbnails are generated at 200x200"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Track images passed to compress_image
        compressed_images = []
        def capture_compress(img):
            compressed_images.append(img)
            return b'compressed'

        mock_compress.side_effect = capture_compress

        from src.database.services.image_service import ImageService

        service = ImageService()

        # Large image that will be thumbnailed
        large_image = Image.new('RGB', (800, 600), color='blue')
        images = [
            {'image_id': 'IMG-001-00', 'page_number': 1, 'image_data': large_image}
        ]

        service.insert_images(book_id=1, images=images)

        # Should have compressed 2 images: full and thumbnail
        assert len(compressed_images) == 2
        full_img = compressed_images[0]
        thumb_img = compressed_images[1]

        # Full image should be original size
        assert full_img.size == (800, 600)

        # Thumbnail should be scaled to fit 200x200 (maintaining aspect ratio)
        # 800x600 -> 200x150 (width constrained)
        assert thumb_img.size[0] <= 200
        assert thumb_img.size[1] <= 200

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.decompress_image')
    def test_get_image(self, mock_decompress, mock_get_table, mock_session_cls):
        """Test retrieving and decompressing image"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock database result
        mock_row = (b'compressed_image_data',)
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Mock decompression
        decompressed_img = Image.new('RGB', (400, 300), color='red')
        mock_decompress.return_value = decompressed_img

        from src.database.services.image_service import ImageService

        service = ImageService()
        image = service.get_image(book_id=1, image_id='IMG-001-00')

        assert image == decompressed_img
        mock_decompress.assert_called_once_with(b'compressed_image_data')
        mock_db.close.assert_called_once()

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.decompress_image')
    def test_get_thumbnail(self, mock_decompress, mock_get_table, mock_session_cls):
        """Test retrieving thumbnail instead of full image"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        mock_row = (b'compressed_thumbnail_data',)
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        thumb_img = Image.new('RGB', (200, 200), color='green')
        mock_decompress.return_value = thumb_img

        from src.database.services.image_service import ImageService

        service = ImageService()
        thumbnail = service.get_image(book_id=1, image_id='IMG-001-00', thumbnail=True)

        assert thumbnail == thumb_img
        mock_decompress.assert_called_once_with(b'compressed_thumbnail_data')

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    def test_get_image_not_found(self, mock_get_table, mock_session_cls):
        """Test retrieving non-existent image"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock no result
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        from src.database.services.image_service import ImageService

        service = ImageService()

        with pytest.raises(ValueError, match="Image IMG-999-99 not found"):
            service.get_image(book_id=1, image_id='IMG-999-99')

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    def test_get_images_by_page(self, mock_get_table, mock_session_cls):
        """Test retrieving all images for a page"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock database results
        mock_result = Mock()
        mock_result.__iter__ = lambda self: iter([
            Mock(_mapping={'image_id': 'IMG-005-00', 'page_number': 5, 'ai_description': 'Diagram'}),
            Mock(_mapping={'image_id': 'IMG-005-01', 'page_number': 5, 'ai_description': 'Chart'})
        ])
        mock_db.execute.return_value = mock_result

        from src.database.services.image_service import ImageService

        service = ImageService()
        images = service.get_images_by_page(book_id=1, page_number=5)

        assert len(images) == 2
        assert images[0]['image_id'] == 'IMG-005-00'
        assert images[1]['image_id'] == 'IMG-005-01'
        mock_db.close.assert_called_once()

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    def test_delete_image(self, mock_get_table, mock_session_cls):
        """Test deleting an image"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock successful delete
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        from src.database.services.image_service import ImageService

        service = ImageService()
        success = service.delete_image(book_id=1, image_id='IMG-001-00')

        assert success is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    def test_delete_image_not_found(self, mock_get_table, mock_session_cls):
        """Test deleting non-existent image"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'

        # Mock no rows deleted
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        from src.database.services.image_service import ImageService

        service = ImageService()
        success = service.delete_image(book_id=1, image_id='IMG-999-99')

        assert success is False

    @patch('src.database.services.image_service.SessionLocal')
    @patch('src.database.services.image_service.get_table_name')
    @patch('src.database.services.image_service.compress_image')
    def test_insert_rollback_on_error(self, mock_compress, mock_get_table, mock_session_cls):
        """Test that insert rolls back on error"""
        mock_db = Mock()
        mock_session_cls.return_value = mock_db
        mock_get_table.return_value = 'book1_test_images'
        mock_compress.side_effect = lambda img: b'compressed'

        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")

        from src.database.services.image_service import ImageService

        service = ImageService()
        images = [
            {'image_id': 'IMG-001-00', 'page_number': 1, 'image_data': Image.new('RGB', (100, 100))}
        ]

        with pytest.raises(Exception, match="Database error"):
            service.insert_images(book_id=1, images=images)

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
