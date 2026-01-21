"""
Unit tests for CHUNK-005: File Type Detection

Tests file type detection using python-magic.

Test Coverage:
- PDF file detection
- DOCX file detection
- Image file detection (PNG, JPEG)
- Unknown file type handling
"""

import pytest
from unittest.mock import patch, Mock, mock_open


class TestChunk005FileTypeDetection:
    """Test suite for CHUNK-005: File Type Detection"""

    @patch('src.utils.file_detection.magic.from_file')
    def test_happy_path_detect_pdf(self, mock_magic):
        """Test detecting a PDF file"""
        mock_magic.return_value = 'application/pdf'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/file.pdf')

        assert result == 'PDF'
        mock_magic.assert_called_once_with('/path/to/file.pdf', mime=True)

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_docx_file(self, mock_magic):
        """Test detecting a DOCX file"""
        mock_magic.return_value = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/document.docx')

        assert result == 'DOCX'

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_text_file(self, mock_magic):
        """Test detecting a TXT file"""
        mock_magic.return_value = 'text/plain'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/file.txt')

        assert result == 'TXT'

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_html_file(self, mock_magic):
        """Test detecting an HTML file"""
        mock_magic.return_value = 'text/html'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/page.html')

        assert result == 'HTML'

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_epub_file(self, mock_magic):
        """Test detecting an EPUB file"""
        mock_magic.return_value = 'application/epub+zip'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/book.epub')

        assert result == 'EPUB'

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_png_image(self, mock_magic):
        """Test detecting a PNG image"""
        mock_magic.return_value = 'image/png'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/image.png')

        assert result == 'PNG'

    @patch('src.utils.file_detection.magic.from_file')
    def test_detect_jpeg_image(self, mock_magic):
        """Test detecting a JPEG image"""
        mock_magic.return_value = 'image/jpeg'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/photo.jpg')

        assert result == 'JPEG'

    @patch('src.utils.file_detection.magic.from_file')
    def test_error_handling_unknown_file_type(self, mock_magic):
        """Test handling of unknown MIME type"""
        mock_magic.return_value = 'application/unknown'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/unknown.xyz')

        assert result == 'UNKNOWN'

    @patch('src.utils.file_detection.magic.from_file')
    def test_error_handling_magic_exception(self, mock_magic):
        """Test handling when magic raises exception"""
        mock_magic.side_effect = Exception("Cannot read file")

        from src.utils.file_detection import detect_file_type

        with pytest.raises(Exception):
            detect_file_type('/path/to/nonexistent.file')

    def test_input_validation_empty_path(self):
        """Test handling of empty file path"""
        from src.utils.file_detection import detect_file_type

        with pytest.raises((ValueError, Exception)):
            detect_file_type('')

    def test_input_validation_none_path(self):
        """Test handling of None as file path"""
        from src.utils.file_detection import detect_file_type

        with pytest.raises((TypeError, Exception)):
            detect_file_type(None)

    @patch('src.utils.file_detection.magic.from_file')
    def test_edge_case_file_without_extension(self, mock_magic):
        """Test detecting file type without extension"""
        mock_magic.return_value = 'application/pdf'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/document')

        # Should detect by content, not extension
        assert result == 'PDF'

    @patch('src.utils.file_detection.magic.from_file')
    def test_edge_case_misleading_extension(self, mock_magic):
        """Test file with wrong extension (content doesn't match)"""
        # File named .txt but actually a PDF
        mock_magic.return_value = 'application/pdf'

        from src.utils.file_detection import detect_file_type

        result = detect_file_type('/path/to/fake.txt')

        # Should detect actual type (PDF), not extension type
        assert result == 'PDF'
