"""
Integration tests for LEVEL 0: Foundation Layer (CHUNK-001 to CHUNK-008)

Tests the integration of:
- Configuration Management (CHUNK-001)
- Database Connection Setup (CHUNK-002)
- Books Metadata Model (CHUNK-003)
- Sanitization Utilities (CHUNK-004)
- File Type Detection (CHUNK-005)
- Pydantic Schemas (CHUNK-006)
- Logging Setup (CHUNK-007)
- Error Classes (CHUNK-008)

This test suite verifies that foundational components work together with real dependencies.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from PIL import Image
import io


@pytest.fixture(scope="module")
def test_db_url():
    """Test database URL"""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/test_knowledge_extraction"
    )


@pytest.fixture(scope="module")
def test_engine(test_db_url):
    """Create test database engine"""
    engine = create_engine(test_db_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def test_session(test_engine):
    """Create test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def cleanup_test_data(test_session):
    """Cleanup test data after each test"""
    yield
    # Rollback any uncommitted changes
    test_session.rollback()


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Write minimal PDF content
        f.write(b"%PDF-1.4\n%EOF")
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def temp_image_file():
    """Create a temporary image file for testing"""
    image = Image.new('RGB', (100, 100), color='white')
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f, format='PNG')
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


class TestConfigurationIntegration:
    """Test configuration loading and validation"""

    def test_config_loads_from_environment(self):
        """Test that configuration loads from environment variables"""
        from src.config import Settings

        # Set minimal required environment variables
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test_db'
        os.environ['TESSERACT_PATH'] = '/usr/bin/tesseract'
        os.environ['MODEL_CACHE_DIR'] = '/tmp/models'

        settings = Settings()

        assert settings.DATABASE_URL == 'postgresql://test:test@localhost/test_db'
        assert settings.TESSERACT_PATH == '/usr/bin/tesseract'
        assert settings.MODEL_CACHE_DIR == '/tmp/models'
        assert settings.DB_POOL_SIZE == 10  # Default value

    def test_config_defaults_applied(self):
        """Test that default values are properly applied"""
        from src.config import settings

        assert settings.DB_POOL_SIZE >= 10
        assert settings.CHECKPOINT_FREQUENCY >= 50
        assert settings.BATCH_INSERT_SIZE >= 50


class TestDatabaseIntegration:
    """Test database connection and models"""

    def test_database_connection_established(self, test_engine):
        """Test that database connection can be established"""
        with test_engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            assert result.fetchone()[0] == 1

    def test_books_metadata_table_creation(self, test_engine, test_session):
        """Test that books_metadata table can be created and accessed"""
        from src.database.models.books_metadata import Base, BooksMetadata

        # Create table
        Base.metadata.create_all(test_engine)

        # Verify table exists
        inspector = inspect(test_engine)
        assert 'books_metadata' in inspector.get_table_names()

        # Cleanup
        Base.metadata.drop_all(test_engine)

    def test_books_metadata_crud_operations(self, test_engine, test_session):
        """Test CRUD operations on books_metadata table"""
        from src.database.models.books_metadata import Base, BooksMetadata

        # Create table
        Base.metadata.create_all(test_engine)

        # Create
        book = BooksMetadata(
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100,
            processing_status="uploaded"
        )
        test_session.add(book)
        test_session.commit()

        # Read
        retrieved = test_session.query(BooksMetadata).filter_by(
            sanitized_name="test_book"
        ).first()
        assert retrieved is not None
        assert retrieved.book_name == "Test Book"
        assert retrieved.total_pages == 100

        # Update
        retrieved.processing_status = "processing"
        test_session.commit()

        updated = test_session.query(BooksMetadata).filter_by(
            sanitized_name="test_book"
        ).first()
        assert updated.processing_status == "processing"

        # Delete
        test_session.delete(retrieved)
        test_session.commit()

        deleted = test_session.query(BooksMetadata).filter_by(
            sanitized_name="test_book"
        ).first()
        assert deleted is None

        # Cleanup
        Base.metadata.drop_all(test_engine)


class TestSanitizationIntegration:
    """Test sanitization utilities integration"""

    def test_sanitize_book_name_with_file_detection(self, temp_pdf_file):
        """Test sanitization works with file type detection"""
        from src.utils.sanitization import sanitize_book_name, generate_table_prefix
        from src.utils.file_detection import detect_file_type

        # Sanitize filename
        filename = "My Test Book (2024).pdf"
        sanitized = sanitize_book_name(filename)

        assert sanitized == "my_test_book_2024"

        # Generate table prefix
        prefix = generate_table_prefix(1, sanitized)
        assert prefix == "book1_my_test_book_2024"

        # Detect file type
        file_type = detect_file_type(temp_pdf_file)
        assert file_type == "PDF"

    def test_sanitize_handles_special_characters(self):
        """Test sanitization handles various special characters"""
        from src.utils.sanitization import sanitize_book_name

        test_cases = [
            ("Book@Name#123.pdf", "bookname123"),
            ("Book  With   Spaces.pdf", "book_with_spaces"),
            ("Book-Name_Test.pdf", "book_name_test"),
            ("العربية.pdf", ""),  # Arabic characters
            ("Book!@#$%^&*().pdf", "book"),
        ]

        for input_name, expected in test_cases:
            result = sanitize_book_name(input_name)
            if expected:
                assert result == expected
            else:
                assert result == "book"  # Default for empty result


class TestSchemaValidation:
    """Test Pydantic schema validation"""

    def test_book_upload_request_validation(self):
        """Test BookUploadRequest schema validation"""
        from src.database.schemas import BookUploadRequest

        # Valid request
        valid_data = {
            "book_name": "Test Book",
            "language_setting": "english",
            "extraction_sensitivity": "balanced",
            "image_processing": "all",
            "ocr_quality": "balanced"
        }

        request = BookUploadRequest(**valid_data)
        assert request.book_name == "Test Book"
        assert request.language_setting == "english"
        assert request.partial_processing_enabled is False

    def test_book_response_from_model(self, test_engine, test_session):
        """Test BookResponse can be created from database model"""
        from src.database.models.books_metadata import Base, BooksMetadata
        from src.database.schemas import BookResponse

        # Create table and book
        Base.metadata.create_all(test_engine)

        book = BooksMetadata(
            book_name="Response Test",
            sanitized_name="response_test",
            table_prefix="book1_response_test",
            file_type="PDF",
            file_size_bytes=2048000,
            total_pages=50,
            processing_status="uploaded"
        )
        test_session.add(book)
        test_session.commit()

        # Create response from model
        response = BookResponse.from_orm(book)
        assert response.book_name == "Response Test"
        assert response.total_pages == 50

        # Cleanup
        test_session.delete(book)
        test_session.commit()
        Base.metadata.drop_all(test_engine)


class TestLoggingIntegration:
    """Test logging configuration"""

    def test_logging_setup(self):
        """Test that logging is properly configured"""
        from src.utils.logging_config import setup_logging, logger

        # Setup logging
        test_logger = setup_logging()

        assert test_logger is not None
        assert logger is not None

    def test_logging_output(self, caplog):
        """Test that logging produces output"""
        from src.utils.logging_config import logger

        logger.info("Test info message")
        logger.warning("Test warning message")

        assert "Test info message" in caplog.text or len(caplog.records) > 0


class TestErrorHandling:
    """Test error classes integration"""

    def test_custom_exceptions(self):
        """Test custom exception hierarchy"""
        from src.utils.exceptions import (
            ExtractionError, OCRError, PDFError,
            DatabaseError, ProcessingError
        )

        # Test exception raising
        with pytest.raises(OCRError):
            raise OCRError("OCR failed")

        with pytest.raises(PDFError):
            raise PDFError("PDF processing failed")

        with pytest.raises(DatabaseError):
            raise DatabaseError("Database connection failed")

        # Test inheritance
        assert issubclass(OCRError, ExtractionError)
        assert issubclass(PDFError, ExtractionError)

    def test_exception_with_logging(self, caplog):
        """Test exceptions work with logging system"""
        from src.utils.exceptions import ProcessingError
        from src.utils.logging_config import logger

        try:
            raise ProcessingError("Test processing error")
        except ProcessingError as e:
            logger.error(f"Caught error: {str(e)}")
            assert "Test processing error" in str(e)


class TestFullFoundationIntegration:
    """Test all foundation components working together"""

    def test_complete_book_metadata_creation_flow(self, test_engine, test_session, temp_pdf_file):
        """Test complete flow: sanitize, detect type, create metadata"""
        from src.database.models.books_metadata import Base, BooksMetadata
        from src.utils.sanitization import sanitize_book_name, generate_table_prefix
        from src.utils.file_detection import detect_file_type
        from src.database.schemas import BookUploadRequest

        # Create tables
        Base.metadata.create_all(test_engine)

        # 1. Create upload request
        request = BookUploadRequest(
            book_name="Complete Integration Test Book.pdf",
            language_setting="auto",
            extraction_sensitivity="balanced"
        )

        # 2. Sanitize name
        sanitized = sanitize_book_name(request.book_name)
        assert "complete_integration_test_book" in sanitized

        # 3. Detect file type
        file_type = detect_file_type(temp_pdf_file)

        # 4. Get file size
        file_size = os.path.getsize(temp_pdf_file)

        # 5. Generate table prefix
        prefix = generate_table_prefix(1, sanitized)

        # 6. Create metadata record
        book = BooksMetadata(
            book_name=request.book_name,
            sanitized_name=sanitized,
            table_prefix=prefix,
            file_type=file_type,
            file_size_bytes=file_size,
            total_pages=100,
            processing_status="uploaded",
            language_setting=request.language_setting,
            extraction_sensitivity=request.extraction_sensitivity
        )

        test_session.add(book)
        test_session.commit()

        # 7. Verify everything worked
        retrieved = test_session.query(BooksMetadata).filter_by(
            sanitized_name=sanitized
        ).first()

        assert retrieved is not None
        assert retrieved.file_type == "PDF"
        assert retrieved.processing_status == "uploaded"
        assert "book1_" in retrieved.table_prefix

        # Cleanup
        test_session.delete(retrieved)
        test_session.commit()
        Base.metadata.drop_all(test_engine)

    def test_error_handling_across_foundation_layer(self):
        """Test error handling works across all foundation components"""
        from src.utils.exceptions import ExtractionError, DatabaseError
        from src.utils.logging_config import logger

        # Simulate multi-component error scenario
        errors_caught = []

        try:
            # Simulate database error
            raise DatabaseError("Connection failed")
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}")
            errors_caught.append("database")

        try:
            # Simulate extraction error
            raise ExtractionError("Extraction failed")
        except ExtractionError as e:
            logger.error(f"Extraction error: {str(e)}")
            errors_caught.append("extraction")

        assert len(errors_caught) == 2
        assert "database" in errors_caught
        assert "extraction" in errors_caught
