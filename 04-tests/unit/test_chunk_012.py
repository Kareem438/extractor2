"""
Unit tests for CHUNK-012: PDF Text Extraction (PyMuPDF)

Tests extracting text from PDF using PyMuPDF.

Test Coverage:
- Native text extraction from PDF pages
- Text block extraction with coordinates
- Font and size information
- Scanned PDF handling (no text)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestChunk012PDFTextExtraction:
    """Test suite for CHUNK-012: PDF Text Extraction (PyMuPDF)"""

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_happy_path_extract_text_with_content(self, mock_fitz_open):
        """Test extracting text from PDF page with native text"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {
                    'blocks': [
                        {
                            'type': 0,
                            'lines': [{
                                'spans': [{
                                    'text': 'Sample text',
                                    'bbox': (100, 100, 200, 120),
                                    'font': 'Arial',
                                    'size': 12
                                }]
                            }]
                        }
                    ]
                }
            else:
                return "Sample text from PDF"

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page('/path/to/file.pdf', 1)

        assert 'text' in result
        assert 'blocks' in result
        assert 'has_text' in result
        assert result['has_text'] is True

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_extract_text_blocks_with_coordinates(self, mock_fitz_open):
        """Test extraction of text blocks with bounding boxes"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {
                    'blocks': [
                        {
                            'type': 0,
                            'lines': [{
                                'spans': [{
                                    'text': 'Block 1',
                                    'bbox': (50, 50, 150, 70),
                                    'font': 'Times',
                                    'size': 14
                                }]
                            }]
                        }
                    ]
                }
            else:
                return "Block 1"

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page('/path/to/file.pdf', 1)

        assert len(result['blocks']) > 0
        block = result['blocks'][0]
        assert 'bbox' in block
        assert 'font' in block
        assert 'size' in block

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_scanned_pdf_no_text(self, mock_fitz_open):
        """Test handling of scanned PDF with no native text"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {'blocks': []}
            else:
                return ""

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page('/path/to/scanned.pdf', 1)

        assert result['has_text'] is False
        assert result['text'].strip() == ""

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_page_indexing_zero_based(self, mock_fitz_open):
        """Test that page numbers are converted to 0-based index"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {'blocks': []}
            else:
                return "Text"

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        extract_text_from_pdf_page('/path/to/file.pdf', 5)

        # Should access page 4 (5 - 1)
        mock_doc.load_page.assert_called_with(4)

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_error_handling_invalid_pdf(self, mock_fitz_open):
        """Test error handling with invalid PDF file"""
        mock_fitz_open.side_effect = Exception("Cannot open PDF")

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        with pytest.raises(Exception):
            extract_text_from_pdf_page('/path/to/invalid.pdf', 1)

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_error_handling_page_out_of_range(self, mock_fitz_open):
        """Test error handling when page number exceeds total pages"""
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(side_effect=IndexError("Page out of range"))

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        with pytest.raises(IndexError):
            extract_text_from_pdf_page('/path/to/file.pdf', 999)

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_multi_column_layout_detection(self, mock_fitz_open):
        """Test extraction from multi-column layout"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {
                    'blocks': [
                        {
                            'type': 0,
                            'lines': [{'spans': [{'text': 'Column 1', 'bbox': (50, 50, 250, 70), 'font': 'Arial', 'size': 12}]}]
                        },
                        {
                            'type': 0,
                            'lines': [{'spans': [{'text': 'Column 2', 'bbox': (300, 50, 500, 70), 'font': 'Arial', 'size': 12}]}]
                        }
                    ]
                }
            else:
                return "Column 1\nColumn 2"

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page('/path/to/file.pdf', 1)

        assert len(result['blocks']) >= 2

    @patch('src.agents.reader.pdf_reader.fitz.open')
    def test_edge_case_empty_page(self, mock_fitz_open):
        """Test handling of empty PDF page"""
        mock_doc = Mock()
        mock_page = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.load_page = Mock(return_value=mock_page)

        # Configure get_text to return different values based on argument
        def get_text_side_effect(format=None):
            if format == "dict":
                return {'blocks': []}
            else:
                return ""

        mock_page.get_text.side_effect = get_text_side_effect

        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page('/path/to/file.pdf', 1)

        assert result['has_text'] is False
        assert len(result['blocks']) == 0
