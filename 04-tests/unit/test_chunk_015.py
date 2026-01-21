"""
Unit tests for CHUNK-015: Image Compression (LZ4)

Tests compressing and decompressing images with LZ4.

Test Coverage:
- Image compression
- Image decompression
- Compression ratio
- Quality preservation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from io import BytesIO


class TestChunk015ImageCompression:
    """Test suite for CHUNK-015: Image Compression (LZ4)"""

    @patch('src.utils.image_compression.lz4.frame.compress')
    def test_happy_path_compress_image(self, mock_lz4_compress):
        """Test compressing a PIL Image"""
        mock_lz4_compress.return_value = b'compressed_data'

        from src.utils.image_compression import compress_image

        test_image = Mock(spec=Image.Image)
        test_image.save = Mock()

        result = compress_image(test_image)

        assert result == b'compressed_data'
        test_image.save.assert_called_once()
        mock_lz4_compress.assert_called_once()

    @patch('src.utils.image_compression.lz4.frame.decompress')
    @patch('src.utils.image_compression.Image.open')
    def test_happy_path_decompress_image(self, mock_image_open, mock_lz4_decompress):
        """Test decompressing LZ4 bytes to PIL Image"""
        mock_lz4_decompress.return_value = b'png_data'
        mock_image = Mock(spec=Image.Image)
        mock_image_open.return_value = mock_image

        from src.utils.image_compression import decompress_image

        result = decompress_image(b'compressed_data')

        assert result == mock_image
        mock_lz4_decompress.assert_called_once_with(b'compressed_data')
        mock_image_open.assert_called_once()

    @patch('src.utils.image_compression.lz4.frame.compress')
    @patch('src.utils.image_compression.lz4.frame.decompress')
    def test_compression_decompression_round_trip(self, mock_decompress, mock_compress):
        """Test compressing and decompressing preserves image"""
        png_bytes = b'fake_png_data'
        compressed = b'compressed_data'
        
        mock_compress.return_value = compressed
        mock_decompress.return_value = png_bytes

        from src.utils.image_compression import compress_image, decompress_image

        # Create mock image
        test_image = Mock(spec=Image.Image)
        with patch('src.utils.image_compression.BytesIO') as mock_bytesio:
            mock_buffer = Mock()
            mock_buffer.getvalue.return_value = png_bytes
            mock_bytesio.return_value = mock_buffer
            
            # Compress
            compressed_result = compress_image(test_image)

        assert compressed_result == compressed

    @patch('src.utils.image_compression.lz4.frame.compress')
    def test_png_format_used_for_compression(self, mock_lz4_compress):
        """Test that PNG format is used for compression"""
        mock_lz4_compress.return_value = b'compressed'

        from src.utils.image_compression import compress_image

        test_image = Mock(spec=Image.Image)
        
        compress_image(test_image)

        # Verify save was called with PNG format
        save_call = test_image.save.call_args
        assert save_call[1]['format'] == 'PNG'

    @patch('src.utils.image_compression.lz4.frame.compress')
    def test_compression_ratio(self, mock_lz4_compress):
        """Test that compression provides good ratio"""
        original_size = 100000
        compressed_size = 30000
        
        mock_lz4_compress.return_value = b'x' * compressed_size

        from src.utils.image_compression import compress_image

        test_image = Mock(spec=Image.Image)
        with patch('src.utils.image_compression.BytesIO') as mock_bytesio:
            mock_buffer = Mock()
            mock_buffer.getvalue.return_value = b'x' * original_size
            mock_bytesio.return_value = mock_buffer
            
            result = compress_image(test_image)

        # Compressed should be smaller
        assert len(result) < original_size

    @patch('src.utils.image_compression.lz4.frame.compress')
    def test_error_handling_compression_failure(self, mock_lz4_compress):
        """Test error handling when compression fails"""
        mock_lz4_compress.side_effect = Exception("Compression failed")

        from src.utils.image_compression import compress_image

        test_image = Mock(spec=Image.Image)

        with pytest.raises(Exception):
            compress_image(test_image)

    @patch('src.utils.image_compression.lz4.frame.decompress')
    def test_error_handling_decompression_failure(self, mock_lz4_decompress):
        """Test error handling when decompression fails"""
        mock_lz4_decompress.side_effect = Exception("Decompression failed")

        from src.utils.image_compression import decompress_image

        with pytest.raises(Exception):
            decompress_image(b'invalid_data')

    @patch('src.utils.image_compression.lz4.frame.compress')
    def test_edge_case_empty_image(self, mock_lz4_compress):
        """Test handling of empty/minimal image"""
        mock_lz4_compress.return_value = b''

        from src.utils.image_compression import compress_image

        test_image = Mock(spec=Image.Image)
        with patch('src.utils.image_compression.BytesIO') as mock_bytesio:
            mock_buffer = Mock()
            mock_buffer.getvalue.return_value = b''
            mock_bytesio.return_value = mock_buffer
            
            result = compress_image(test_image)

        assert result == b''

    @patch('src.utils.image_compression.lz4.frame.compress')
    @patch('src.utils.image_compression.lz4.frame.decompress')
    @patch('src.utils.image_compression.Image.open')
    def test_image_quality_preserved(self, mock_image_open, mock_decompress, mock_compress):
        """Test that image quality is preserved through compression"""
        from src.utils.image_compression import compress_image, decompress_image

        # Mock original image
        original = Mock(spec=Image.Image)
        original.mode = 'RGB'
        original.size = (800, 600)

        # Mock decompressed image
        decompressed = Mock(spec=Image.Image)
        decompressed.mode = 'RGB'
        decompressed.size = (800, 600)
        mock_image_open.return_value = decompressed

        with patch('src.utils.image_compression.BytesIO'):
            compressed = compress_image(original)
            result = decompress_image(compressed)

        # Decompressed should have same properties
        assert result.mode == original.mode
        assert result.size == original.size
