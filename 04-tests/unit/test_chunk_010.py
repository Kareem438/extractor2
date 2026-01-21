"""
Unit tests for CHUNK-010: OCR Utility (Tesseract)

Tests OCR text extraction with Tesseract.

Test Coverage:
- OCR text extraction from images
- Confidence score calculation
- Language support
- Quality settings
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import numpy as np


class TestChunk010OCRUtility:
    """Test suite for CHUNK-010: OCR Utility (Tesseract)"""

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_happy_path_ocr_extraction(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test normal OCR text extraction"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "Sample extracted text"
        mock_image_to_data.return_value = {
            'conf': ['95', '90', '88', '92']
        }

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        text, confidence = ocr_image(test_image, language='eng', quality='balanced')

        assert text == "Sample extracted text"
        assert 85 <= confidence <= 95  # Average of mock confidences
        mock_image_to_string.assert_called_once()

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_confidence_score_calculation(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test confidence score calculation from OCR data"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {
            'conf': ['100', '80', '60', '-1', '90']  # -1 should be ignored
        }

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        text, confidence = ocr_image(test_image)

        # Average should be (100 + 80 + 60 + 90) / 4 = 82.5
        assert 82 <= confidence <= 83

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_language_parameter(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test OCR with different language settings"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "نص عربي"
        mock_image_to_data.return_value = {'conf': ['90']}

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        text, confidence = ocr_image(test_image, language='ara')

        # Verify Arabic language was passed
        call_kwargs = mock_image_to_string.call_args[1]
        assert call_kwargs['lang'] == 'ara'

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_quality_settings_fast(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test OCR with 'fast' quality setting"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {'conf': ['85']}

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        ocr_image(test_image, quality='fast')

        call_kwargs = mock_image_to_string.call_args[1]
        assert 'config' in call_kwargs
        assert '--psm 3' in call_kwargs['config']

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_quality_settings_high(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test OCR with 'high' quality setting"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "Text"
        mock_image_to_data.return_value = {'conf': ['95']}

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        ocr_image(test_image, quality='high')

        call_kwargs = mock_image_to_string.call_args[1]
        config = call_kwargs['config']
        assert '--dpi 300' in config or 'oem 3' in config

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_error_handling_tesseract_not_found(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test error when Tesseract is not installed"""
        from src.utils.ocr import ocr_image
        from src.utils.exceptions import OCRError

        mock_settings.TESSERACT_PATH = '/invalid/path'
        mock_image_to_string.side_effect = Exception("Tesseract not found")

        test_image = Mock(spec=Image.Image)

        with pytest.raises(Exception):
            ocr_image(test_image)

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_edge_case_empty_image(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test OCR on empty/blank image"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = ""
        mock_image_to_data.return_value = {'conf': []}

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        text, confidence = ocr_image(test_image)

        assert text == ""
        assert confidence == 0  # No confidence data

    @patch('src.utils.ocr.pytesseract.image_to_string')
    @patch('src.utils.ocr.pytesseract.image_to_data')
    @patch('src.utils.ocr.settings')
    def test_text_stripping(self, mock_settings, mock_image_to_data, mock_image_to_string):
        """Test that extracted text is properly stripped"""
        mock_settings.TESSERACT_PATH = '/usr/bin/tesseract'
        mock_image_to_string.return_value = "  Text with whitespace  \n\n"
        mock_image_to_data.return_value = {'conf': ['90']}

        from src.utils.ocr import ocr_image

        test_image = Mock(spec=Image.Image)
        text, confidence = ocr_image(test_image)

        assert text == "Text with whitespace"
