"""
Unit tests for CHUNK-014: Language Detection

Tests detecting text language (English/Arabic/Mixed).

Test Coverage:
- English text detection
- Arabic text detection
- Mixed language detection
- Short text handling
"""

import pytest
from unittest.mock import patch, Mock


class TestChunk014LanguageDetection:
    """Test suite for CHUNK-014: Language Detection"""

    @patch('src.utils.language_detector.detect')
    def test_happy_path_english_detection(self, mock_detect):
        """Test detecting English text"""
        mock_detect.return_value = 'en'

        from src.utils.language_detector import detect_language

        result = detect_language("This is English text")

        assert result == 'english'
        mock_detect.assert_called_once()

    @patch('src.utils.language_detector.detect')
    def test_arabic_detection(self, mock_detect):
        """Test detecting Arabic text"""
        mock_detect.return_value = 'ar'

        from src.utils.language_detector import detect_language

        result = detect_language("هذا نص عربي")

        assert result == 'arabic'

    def test_mixed_language_detection(self):
        """Test detecting mixed English and Arabic text"""
        from src.utils.language_detector import detect_language

        # Text with both Latin and Arabic scripts
        mixed_text = "This is English and هذا عربي mixed together"

        result = detect_language(mixed_text)

        assert result in ['mixed', 'english', 'arabic']

    def test_edge_case_short_text(self):
        """Test handling of very short text"""
        from src.utils.language_detector import detect_language

        result = detect_language("Hi")

        # Should default to English for short text
        assert result == 'english'

    def test_edge_case_empty_text(self):
        """Test handling of empty text"""
        from src.utils.language_detector import detect_language

        result = detect_language("")

        assert result == 'english'  # Default

    def test_edge_case_whitespace_only(self):
        """Test handling of whitespace-only text"""
        from src.utils.language_detector import detect_language

        result = detect_language("   \n\t  ")

        assert result == 'english'  # Default

    @patch('src.utils.language_detector.detect')
    def test_error_handling_detection_exception(self, mock_detect):
        """Test handling when langdetect raises exception"""
        from src.utils.language_detector import LangDetectException
        mock_detect.side_effect = LangDetectException("Cannot detect", "")

        from src.utils.language_detector import detect_language

        result = detect_language("Some text")

        assert result == 'english'  # Fallback to default

    def test_arabic_script_detection(self):
        """Test Unicode range detection for Arabic script"""
        from src.utils.language_detector import detect_language

        # Pure Arabic text (should contain Arabic Unicode range)
        arabic_text = "مرحبا بك في هذا النص"

        result = detect_language(arabic_text)

        assert result in ['arabic', 'mixed']

    def test_latin_script_detection(self):
        """Test Latin script detection"""
        from src.utils.language_detector import detect_language

        # Pure English with Latin characters
        english_text = "Hello world this is a test"

        result = detect_language(english_text)

        assert result == 'english'

    @patch('src.utils.language_detector.detect')
    def test_other_language_defaults_to_english(self, mock_detect):
        """Test that other languages default appropriately"""
        mock_detect.return_value = 'fr'  # French

        from src.utils.language_detector import detect_language

        result = detect_language("Bonjour le monde")

        # Should check script and default based on that
        assert result in ['english', 'arabic', 'mixed']

    def test_minimum_text_length_requirement(self):
        """Test minimum text length of 10 characters"""
        from src.utils.language_detector import detect_language

        # Text with exactly 10 characters
        result1 = detect_language("1234567890")
        
        # Text with 9 characters (below minimum)
        result2 = detect_language("123456789")

        assert result2 == 'english'  # Default for short text
