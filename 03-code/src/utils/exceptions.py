"""
CHUNK-008: Error Classes

Custom exception classes for the Knowledge Extraction System.
Provides specific error types for different failure scenarios.
"""


class ExtractionError(Exception):
    """
    Base exception for extraction-related errors.

    This is the parent class for all errors that occur during
    the text extraction process (OCR, PDF processing, etc.).
    """
    pass


class OCRError(ExtractionError):
    """
    OCR-related errors.

    Raised when OCR engines (Tesseract, PaddleOCR, Surya) fail
    to process images or extract text.

    Example:
        raise OCRError("Tesseract failed to process image")
    """
    pass


class PDFError(ExtractionError):
    """
    PDF processing errors.

    Raised when PDF files cannot be opened, read, or processed.

    Example:
        raise PDFError("Cannot open corrupted PDF file")
    """
    pass


class DatabaseError(Exception):
    """
    Database-related errors.

    Raised when database operations fail (connection issues,
    table creation errors, query failures, etc.).

    Example:
        raise DatabaseError("Failed to create book-specific table")
    """
    pass


class ProcessingError(Exception):
    """
    General processing errors.

    Raised when background processing tasks fail or when
    general workflow errors occur.

    Example:
        raise ProcessingError("Background task interrupted")
    """
    pass
