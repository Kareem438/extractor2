"""
Unit tests for CHUNK-013: PDF to Image Conversion

Tests converting PDF pages to PNG images.

Test Coverage:
- PDF page to image conversion
- DPI settings
- Image dimensions
- Multiple format support
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk013PDFToImageConversion:
    """Test suite for CHUNK-013: PDF to Image Conversion"""

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    @patch('src.agents.reader.pdf_to_image.Image.frombytes')
    def test_happy_path_pdf_to_image(self, mock_frombytes, mock_fitz_open):
        """Test converting PDF page to image"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()

        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 800
        mock_pix.height = 600
        mock_pix.samples = b'\x00' * (800 * 600 * 3)
        
        mock_image = Mock(spec=Image.Image)
        mock_frombytes.return_value = mock_image

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        result = pdf_page_to_image('/path/to/file.pdf', 1, dpi=150)

        assert result == mock_image
        mock_page.get_pixmap.assert_called_once()

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    def test_dpi_scaling(self, mock_fitz_open):
        """Test DPI scaling calculation"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()
        
        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 1200
        mock_pix.height = 900
        mock_pix.samples = b''

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        with patch('src.agents.reader.pdf_to_image.Image.frombytes'):
            pdf_page_to_image('/path/to/file.pdf', 1, dpi=150)

        # DPI 150 / 72 = 2.083 zoom factor
        call_args = mock_page.get_pixmap.call_args
        assert call_args is not None

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    @patch('src.agents.reader.pdf_to_image.Image.frombytes')
    def test_different_dpi_settings(self, mock_frombytes, mock_fitz_open):
        """Test conversion with different DPI settings"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()
        
        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 1600
        mock_pix.height = 1200
        mock_pix.samples = b''
        
        mock_image = Mock(spec=Image.Image)
        mock_frombytes.return_value = mock_image

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        # Test with DPI 300
        result = pdf_page_to_image('/path/to/file.pdf', 1, dpi=300)
        assert result is not None

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    def test_page_number_conversion(self, mock_fitz_open):
        """Test that page number is converted to 0-based index"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()
        
        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 800
        mock_pix.height = 600
        mock_pix.samples = b''

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        with patch('src.agents.reader.pdf_to_image.Image.frombytes'):
            pdf_page_to_image('/path/to/file.pdf', 3)

        # Page 3 should be index 2
        mock_doc.__getitem__.assert_called_with(2)

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    def test_error_handling_invalid_pdf(self, mock_fitz_open):
        """Test error handling with invalid PDF"""
        mock_fitz_open.side_effect = Exception("Cannot open PDF")

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        with pytest.raises(Exception):
            pdf_page_to_image('/invalid/path.pdf', 1)

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    def test_rgb_color_mode(self, mock_fitz_open):
        """Test that images are in RGB color mode"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()
        
        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 800
        mock_pix.height = 600
        mock_pix.samples = b'\x00' * (800 * 600 * 3)

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        with patch('src.agents.reader.pdf_to_image.Image.frombytes') as mock_frombytes:
            pdf_page_to_image('/path/to/file.pdf', 1)
            
            # Verify RGB mode
            call_args = mock_frombytes.call_args[0]
            assert call_args[0] == "RGB"

    @patch('src.agents.reader.pdf_to_image.fitz.open')
    @patch('src.agents.reader.pdf_to_image.Image.frombytes')
    def test_image_dimensions_match_pixmap(self, mock_frombytes, mock_fitz_open):
        """Test that image dimensions match pixmap size"""
        mock_doc = MagicMock()
        mock_page = Mock()
        mock_pix = Mock()
        
        mock_fitz_open.return_value = mock_doc
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.width = 1024
        mock_pix.height = 768
        mock_pix.samples = b''

        from src.agents.reader.pdf_to_image import pdf_page_to_image

        pdf_page_to_image('/path/to/file.pdf', 1)
        
        # Check dimensions passed to frombytes
        call_args = mock_frombytes.call_args[0]
        assert call_args[1] == [1024, 768]
