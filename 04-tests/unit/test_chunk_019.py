"""
Unit tests for CHUNK-019: Reader Agent - Main Logic

Tests reader agent - main logic functionality.

Test Coverage:
- Page reading
- Native text extraction
- OCR fallback
- Language detection
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestChunk019ReaderAgentMainLogic:
    """Test suite for CHUNK-019: Reader Agent - Main Logic"""

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_native_text_extraction(self, mock_detect_lang, mock_extract):
        """Test native text extraction when PDF has text"""
        # Mock native text extraction
        mock_extract.return_value = {
            'text': 'Sample text from PDF',
            'blocks': [{'text': 'Sample', 'bbox': (0, 0, 100, 100)}],
            'has_text': True
        }
        mock_detect_lang.return_value = 'english'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        result = agent.read_page('/path/to/file.pdf', 1)

        assert result['text'] == 'Sample text from PDF'
        assert result['extraction_method'] == 'native_text'
        assert result['confidence'] == 100.0
        assert result['language'] == 'english'
        assert len(result['blocks']) > 0

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.pdf_page_to_image')
    @patch('src.agents.reader.reader_agent.ocr_with_retry')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_ocr_fallback(self, mock_detect_lang, mock_ocr, mock_pdf_to_img, mock_extract):
        """Test OCR fallback when PDF has no text"""
        # Mock no native text
        mock_extract.return_value = {
            'text': '',
            'blocks': [],
            'has_text': False
        }

        # Mock PDF to image conversion
        mock_image = Mock()
        mock_pdf_to_img.return_value = mock_image

        # Mock OCR
        mock_ocr.return_value = ('OCR extracted text', 85.0, 'ocr_standard')
        mock_detect_lang.return_value = 'english'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        result = agent.read_page('/path/to/scanned.pdf', 1)

        assert result['text'] == 'OCR extracted text'
        assert result['extraction_method'] == 'ocr_standard'
        assert result['confidence'] == 85.0
        assert result['language'] == 'english'
        assert result['blocks'] == []  # OCR doesn't provide blocks

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_language_detection(self, mock_detect_lang, mock_extract):
        """Test that language is detected from extracted text"""
        mock_extract.return_value = {
            'text': 'Sample text',
            'blocks': [],
            'has_text': True
        }
        mock_detect_lang.return_value = 'arabic'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        result = agent.read_page('/path/to/file.pdf', 1)

        assert result['language'] == 'arabic'
        mock_detect_lang.assert_called_once_with('Sample text')

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.pdf_page_to_image')
    @patch('src.agents.reader.reader_agent.ocr_with_retry')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_language_setting_english(self, mock_detect_lang, mock_ocr, mock_pdf_to_img, mock_extract):
        """Test that language setting is passed to OCR"""
        mock_extract.return_value = {'text': '', 'blocks': [], 'has_text': False}
        mock_pdf_to_img.return_value = Mock()
        mock_ocr.return_value = ('Text', 80.0, 'ocr_standard')
        mock_detect_lang.return_value = 'english'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        agent.read_page('/path/to/file.pdf', 1, language_setting='english')

        # Verify OCR was called with 'eng'
        call_kwargs = mock_ocr.call_args[1]
        assert call_kwargs['language'] == 'eng'

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.pdf_page_to_image')
    @patch('src.agents.reader.reader_agent.ocr_with_retry')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_language_setting_arabic(self, mock_detect_lang, mock_ocr, mock_pdf_to_img, mock_extract):
        """Test that Arabic language setting is passed to OCR"""
        mock_extract.return_value = {'text': '', 'blocks': [], 'has_text': False}
        mock_pdf_to_img.return_value = Mock()
        mock_ocr.return_value = ('Text', 80.0, 'ocr_standard')
        mock_detect_lang.return_value = 'arabic'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        agent.read_page('/path/to/file.pdf', 1, language_setting='arabic')

        # Verify OCR was called with 'ara'
        call_kwargs = mock_ocr.call_args[1]
        assert call_kwargs['language'] == 'ara'

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_confidence_score_native_text(self, mock_detect_lang, mock_extract):
        """Test that native text has 100% confidence"""
        mock_extract.return_value = {'text': 'Text', 'blocks': [], 'has_text': True}
        mock_detect_lang.return_value = 'english'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        result = agent.read_page('/path/to/file.pdf', 1)

        assert result['confidence'] == 100.0

    @patch('src.agents.reader.reader_agent.extract_text_from_pdf_page')
    @patch('src.agents.reader.reader_agent.pdf_page_to_image')
    @patch('src.agents.reader.reader_agent.ocr_with_retry')
    @patch('src.agents.reader.reader_agent.detect_language')
    def test_ocr_retry_methods(self, mock_detect_lang, mock_ocr, mock_pdf_to_img, mock_extract):
        """Test that OCR retry methods are preserved"""
        mock_extract.return_value = {'text': '', 'blocks': [], 'has_text': False}
        mock_pdf_to_img.return_value = Mock()
        mock_ocr.return_value = ('Text', 75.0, 'ocr_retry_zoom')
        mock_detect_lang.return_value = 'english'

        from src.agents.reader.reader_agent import ReaderAgent

        agent = ReaderAgent()
        result = agent.read_page('/path/to/file.pdf', 1)

        assert result['extraction_method'] == 'ocr_retry_zoom'
        assert result['confidence'] == 75.0
