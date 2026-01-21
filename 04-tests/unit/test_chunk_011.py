"""
Unit tests for CHUNK-011: OCR Retry Logic

Tests 3-attempt OCR retry with zoom enhancement.

Test Coverage:
- 3-attempt retry strategy
- Zoom enhancement on retry
- Region segmentation fallback
- Confidence-based success criteria
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestChunk011OCRRetryLogic:
    """Test suite for CHUNK-011: OCR Retry Logic"""

    @patch('src.utils.ocr_retry.ocr_image')
    def test_happy_path_first_attempt_succeeds(self, mock_ocr):
        """Test successful OCR on first attempt"""
        mock_ocr.return_value = ("Extracted text", 75.0)

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        text, confidence, method = ocr_with_retry(test_image, language='eng')

        assert text == "Extracted text"
        assert confidence == 75.0
        assert method == 'ocr_standard'
        assert mock_ocr.call_count == 1  # Only one attempt

    @patch('src.utils.ocr_retry.ocr_image')
    def test_retry_on_low_confidence(self, mock_ocr):
        """Test retry when first attempt has low confidence"""
        # First attempt: low confidence (60%)
        # Second attempt: good confidence (75%)
        mock_ocr.side_effect = [
            ("Low quality text", 60.0),
            ("Better quality text", 75.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        text, confidence, method = ocr_with_retry(test_image)

        assert text == "Better quality text"
        assert confidence == 75.0
        assert method == 'ocr_retry_zoom'
        assert mock_ocr.call_count == 2

    @patch('src.utils.ocr_retry.ocr_image')
    @patch('src.utils.ocr_retry.logger')
    def test_logging_on_retry(self, mock_logger, mock_ocr):
        """Test that retries are logged"""
        mock_ocr.side_effect = [
            ("Text", 65.0),  # Below 70, triggers retry
            ("Text", 75.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        ocr_with_retry(test_image)

        # Verify warning was logged
        assert mock_logger.warning.called

    @patch('src.utils.ocr_retry.ocr_image')
    def test_zoom_enhancement_on_second_attempt(self, mock_ocr):
        """Test that image is zoomed 200% on second attempt"""
        mock_ocr.side_effect = [
            ("Text", 65.0),
            ("Zoomed text", 75.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        mock_zoomed = Mock(spec=Image.Image)
        test_image.resize = Mock(return_value=mock_zoomed)

        text, confidence, method = ocr_with_retry(test_image)

        # Verify resize was called with 200% zoom
        test_image.resize.assert_called_once()
        call_args = test_image.resize.call_args[0][0]
        assert call_args == (1600, 1200)  # 200% of 800x600

    @patch('src.utils.ocr_retry.ocr_image')
    def test_high_quality_on_retry_attempts(self, mock_ocr):
        """Test that high quality is used on retry attempts"""
        mock_ocr.side_effect = [
            ("Text", 65.0),
            ("Better text", 75.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        ocr_with_retry(test_image)

        # Second call should use 'high' quality
        second_call_args = mock_ocr.call_args_list[1]
        assert second_call_args[1]['quality'] == 'high' or second_call_args[0][2] == 'high'

    @patch('src.utils.ocr_retry.ocr_image')
    def test_third_attempt_with_segmentation(self, mock_ocr):
        """Test third attempt uses region segmentation"""
        mock_ocr.side_effect = [
            ("Text", 65.0),
            ("Text", 55.0),
            ("Segmented text", 70.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        text, confidence, method = ocr_with_retry(test_image)

        assert method == 'ocr_retry_segment'
        assert mock_ocr.call_count == 3

    @patch('src.utils.ocr_retry.ocr_image')
    def test_edge_case_all_attempts_fail(self, mock_ocr):
        """Test when all 3 attempts have low confidence"""
        mock_ocr.side_effect = [
            ("Text", 50.0),
            ("Text", 45.0),
            ("Text", 55.0)
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        text, confidence, method = ocr_with_retry(test_image)

        # Should return result from third attempt even if low
        assert confidence == 55.0
        assert method == 'ocr_retry_segment'

    @patch('src.utils.ocr_retry.ocr_image')
    def test_confidence_thresholds(self, mock_ocr):
        """Test different confidence thresholds for each attempt"""
        # Attempt 1 threshold: 70%
        # Attempt 2 threshold: 60%
        mock_ocr.side_effect = [
            ("Text", 65.0),  # Below 70, retry
            ("Text", 62.0)   # Above 60, accept
        ]

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        text, confidence, method = ocr_with_retry(test_image)

        assert confidence == 62.0
        assert method == 'ocr_retry_zoom'
        assert mock_ocr.call_count == 2

    @patch('src.utils.ocr_retry.ocr_image')
    def test_max_attempts_parameter(self, mock_ocr):
        """Test custom max_attempts parameter"""
        mock_ocr.return_value = ("Text", 50.0)

        from src.utils.ocr_retry import ocr_with_retry

        test_image = Mock(spec=Image.Image)
        test_image.width = 800
        test_image.height = 600
        test_image.resize = Mock(return_value=test_image)

        ocr_with_retry(test_image, max_attempts=3)

        assert mock_ocr.call_count == 3
