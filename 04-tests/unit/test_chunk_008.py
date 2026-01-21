"""
Unit tests for CHUNK-008: Error Classes

Tests custom exception classes for the system.

Test Coverage:
- Exception class definitions
- Exception inheritance
- Error message handling
- Exception raising scenarios
"""

import pytest


class TestChunk008ErrorClasses:
    """Test suite for CHUNK-008: Error Classes"""

    def test_happy_path_extraction_error_base(self):
        """Test creating and raising ExtractionError"""
        from src.utils.exceptions import ExtractionError

        with pytest.raises(ExtractionError) as exc_info:
            raise ExtractionError("Test extraction error")

        assert str(exc_info.value) == "Test extraction error"
        assert isinstance(exc_info.value, Exception)

    def test_ocr_error_inheritance(self):
        """Test that OCRError inherits from ExtractionError"""
        from src.utils.exceptions import OCRError, ExtractionError

        error = OCRError("OCR failed")

        assert isinstance(error, OCRError)
        assert isinstance(error, ExtractionError)
        assert isinstance(error, Exception)

    def test_ocr_error_with_message(self):
        """Test OCRError with custom message"""
        from src.utils.exceptions import OCRError

        with pytest.raises(OCRError) as exc_info:
            raise OCRError("Tesseract failed to process image")

        assert "Tesseract" in str(exc_info.value)

    def test_pdf_error_inheritance(self):
        """Test that PDFError inherits from ExtractionError"""
        from src.utils.exceptions import PDFError, ExtractionError

        error = PDFError("PDF processing failed")

        assert isinstance(error, PDFError)
        assert isinstance(error, ExtractionError)

    def test_pdf_error_with_message(self):
        """Test PDFError with custom message"""
        from src.utils.exceptions import PDFError

        with pytest.raises(PDFError) as exc_info:
            raise PDFError("Cannot open PDF file")

        assert "Cannot open PDF file" == str(exc_info.value)

    def test_database_error_base_exception(self):
        """Test DatabaseError as base Exception"""
        from src.utils.exceptions import DatabaseError

        error = DatabaseError("Connection failed")

        assert isinstance(error, DatabaseError)
        assert isinstance(error, Exception)
        # Should NOT inherit from ExtractionError
        from src.utils.exceptions import ExtractionError
        assert not isinstance(error, ExtractionError)

    def test_database_error_with_message(self):
        """Test DatabaseError with custom message"""
        from src.utils.exceptions import DatabaseError

        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("Table does not exist")

        assert "Table does not exist" == str(exc_info.value)

    def test_processing_error_base_exception(self):
        """Test ProcessingError as base Exception"""
        from src.utils.exceptions import ProcessingError

        error = ProcessingError("Processing interrupted")

        assert isinstance(error, ProcessingError)
        assert isinstance(error, Exception)

    def test_processing_error_with_message(self):
        """Test ProcessingError with custom message"""
        from src.utils.exceptions import ProcessingError

        with pytest.raises(ProcessingError) as exc_info:
            raise ProcessingError("Background task failed")

        assert "Background task failed" == str(exc_info.value)

    def test_error_catching_specific_exception(self):
        """Test catching specific exception type"""
        from src.utils.exceptions import OCRError

        try:
            raise OCRError("Test OCR error")
        except OCRError as e:
            assert "Test OCR error" in str(e)
        else:
            pytest.fail("Exception was not caught")

    def test_error_catching_base_exception(self):
        """Test catching derived exception with base class"""
        from src.utils.exceptions import OCRError, ExtractionError

        try:
            raise OCRError("Test OCR error")
        except ExtractionError as e:
            # Should catch OCRError as ExtractionError
            assert isinstance(e, OCRError)
            assert isinstance(e, ExtractionError)
        else:
            pytest.fail("Exception was not caught")

    def test_edge_case_empty_error_message(self):
        """Test exceptions with empty message"""
        from src.utils.exceptions import ExtractionError

        error = ExtractionError()

        assert isinstance(error, ExtractionError)
        # Empty message should be handled gracefully

    def test_edge_case_multiple_inheritance_levels(self):
        """Test exception inheritance chain"""
        from src.utils.exceptions import OCRError, ExtractionError

        try:
            raise OCRError("Test error")
        except Exception as e:
            # Should be catchable as base Exception
            assert isinstance(e, Exception)
            assert isinstance(e, ExtractionError)
            assert isinstance(e, OCRError)

    def test_all_exception_classes_defined(self):
        """Test that all expected exception classes are defined"""
        from src.utils import exceptions

        required_exceptions = [
            'ExtractionError',
            'OCRError',
            'PDFError',
            'DatabaseError',
            'ProcessingError'
        ]

        for exc_name in required_exceptions:
            assert hasattr(exceptions, exc_name), f"{exc_name} not defined"
