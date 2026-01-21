"""
End-to-End Test: Book Upload Workflow

Workflow: Upload PDF → Extract metadata → Create tables

This test simulates a complete user workflow from uploading a PDF book
through the web interface to having all database tables and metadata created.
"""

import pytest
import os
import tempfile
import time
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import fitz  # PyMuPDF


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


@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client():
    """Create test client"""
    from src.main import app
    return TestClient(app)


@pytest.fixture
def sample_pdf_book():
    """Create a realistic sample PDF book for testing"""
    doc = fitz.open()

    # Create 5 pages with content
    for page_num in range(5):
        page = doc.new_page(width=595, height=842)  # A4 size

        # Add title
        title = f"Chapter {page_num + 1}: Test Content"
        rect = fitz.Rect(50, 50, 545, 100)
        page.insert_textbox(rect, title, fontsize=16, fontname="helv")

        # Add body text
        body = f"This is page {page_num + 1} of the test book.\n"
        body += "It contains sample text for testing the upload workflow.\n"
        body += "The system should extract this text and create appropriate tables.\n"
        body += "Each page represents a chapter or section of the book.\n"

        rect = fitz.Rect(50, 120, 545, 700)
        page.insert_textbox(rect, body, fontsize=12, fontname="helv")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name

    doc.save(temp_path)
    doc.close()

    yield temp_path
    os.unlink(temp_path)


class TestUploadWorkflow:
    """End-to-end tests for book upload workflow"""

    def test_complete_upload_workflow(self, client, test_session, test_engine, sample_pdf_book):
        """
        Test complete upload workflow:
        1. User navigates to upload page
        2. User selects PDF file
        3. User fills in upload form
        4. System uploads and processes file
        5. System creates metadata record
        6. System creates all book-specific tables
        7. User is redirected to book detail page
        """
        # Step 1: Navigate to upload page
        response = client.get("/upload")
        assert response.status_code == 200

        # Step 2 & 3: Upload form with file
        file_size = os.path.getsize(sample_pdf_book)

        with open(sample_pdf_book, 'rb') as f:
            files = {'file': ('Sample_Book.pdf', f, 'application/pdf')}
            data = {
                'book_name': 'Sample Test Book',
                'language_setting': 'english',
                'extraction_sensitivity': 'balanced',
                'image_processing': 'all',
                'ocr_quality': 'balanced',
                'hierarchy_detection': 'auto',
                'partial_processing_enabled': 'false'
            }

            # Step 4: Submit upload
            response = client.post("/api/books/upload", files=files, data=data)

        # Verify upload succeeded
        assert response.status_code in [200, 201]
        result = response.json()

        assert 'book_id' in result
        assert 'sanitized_name' in result
        assert 'table_prefix' in result

        book_id = result['book_id']
        sanitized_name = result['sanitized_name']
        table_prefix = result['table_prefix']

        # Step 5: Verify metadata record created
        from src.database.models.books_metadata import BooksMetadata

        book = test_session.query(BooksMetadata).filter_by(book_id=book_id).first()

        assert book is not None
        assert book.book_name == 'Sample Test Book'
        assert book.sanitized_name == sanitized_name
        assert book.file_type == 'PDF'
        assert book.total_pages == 5
        assert book.processing_status == 'uploaded'

        # Step 6: Verify all tables created
        inspector = inspect(test_engine)
        existing_tables = inspector.get_table_names()

        expected_tables = [
            f"{table_prefix}_knowledge_units",
            f"{table_prefix}_images",
            f"{table_prefix}_pages",
            f"{table_prefix}_processing_state",
            f"{table_prefix}_settings",
            f"{table_prefix}_attribute_keys",
            f"{table_prefix}_raw_pages"
        ]

        for table in expected_tables:
            assert table in existing_tables, f"Table {table} was not created"

        # Step 7: Verify can navigate to book detail page
        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200

    def test_upload_with_special_characters_in_name(self, client, test_session, sample_pdf_book):
        """Test uploading book with special characters in name"""
        with open(sample_pdf_book, 'rb') as f:
            files = {'file': ('My Book (2024) - Edition #2.pdf', f, 'application/pdf')}
            data = {
                'book_name': 'My Book (2024) - Edition #2',
                'language_setting': 'english'
            }

            response = client.post("/api/books/upload", files=files, data=data)

        assert response.status_code in [200, 201]
        result = response.json()

        # Sanitized name should remove special characters
        assert 'book_id' in result
        assert 'sanitized_name' in result

        # Verify sanitization worked
        sanitized = result['sanitized_name']
        assert not any(char in sanitized for char in ['(', ')', '#', '-'])

    def test_upload_with_arabic_text(self, client, test_session):
        """Test uploading book with Arabic filename and settings"""
        # Create PDF with Arabic text
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "كتاب تجريبي")  # "Test Book" in Arabic

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        doc.save(temp_path)
        doc.close()

        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('كتاب_اختبار.pdf', f, 'application/pdf')}
                data = {
                    'book_name': 'Arabic Test Book',
                    'language_setting': 'arabic'
                }

                response = client.post("/api/books/upload", files=files, data=data)

            assert response.status_code in [200, 201]
            result = response.json()
            assert result['language_setting'] == 'arabic'

        finally:
            os.unlink(temp_path)

    def test_upload_large_pdf(self, client, test_session):
        """Test uploading a larger PDF with many pages"""
        # Create PDF with 50 pages
        doc = fitz.open()
        for i in range(50):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i + 1} content")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        doc.save(temp_path)
        doc.close()

        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('large_book.pdf', f, 'application/pdf')}
                data = {
                    'book_name': 'Large Test Book',
                    'language_setting': 'english'
                }

                response = client.post("/api/books/upload", files=files, data=data)

            assert response.status_code in [200, 201]
            result = response.json()

            # Verify page count
            from src.database.models.books_metadata import BooksMetadata
            book = test_session.query(BooksMetadata).filter_by(
                book_id=result['book_id']
            ).first()

            assert book.total_pages == 50

        finally:
            os.unlink(temp_path)

    def test_upload_validation_errors(self, client):
        """Test upload with validation errors"""
        # Test 1: Missing file
        response = client.post("/api/books/upload", data={
            'book_name': 'Test Book'
        })
        assert response.status_code in [400, 422]

        # Test 2: Invalid file type
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Not a PDF")
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                data = {'book_name': 'Test Book'}

                response = client.post("/api/books/upload", files=files, data=data)

            assert response.status_code in [400, 422]

        finally:
            os.unlink(temp_path)

    def test_duplicate_book_name_handling(self, client, test_session, sample_pdf_book):
        """Test uploading books with duplicate names"""
        # Upload first book
        with open(sample_pdf_book, 'rb') as f:
            files = {'file': ('duplicate.pdf', f, 'application/pdf')}
            data = {'book_name': 'Duplicate Test'}

            response1 = client.post("/api/books/upload", files=files, data=data)

        assert response1.status_code in [200, 201]

        # Upload second book with same name
        with open(sample_pdf_book, 'rb') as f:
            files = {'file': ('duplicate.pdf', f, 'application/pdf')}
            data = {'book_name': 'Duplicate Test'}

            response2 = client.post("/api/books/upload", files=files, data=data)

        # System should handle duplicate (either error or auto-rename)
        assert response2.status_code in [200, 201, 400, 409]

        if response2.status_code in [200, 201]:
            result1 = response1.json()
            result2 = response2.json()

            # Should have different sanitized names or IDs
            assert result1['book_id'] != result2['book_id'] or \
                   result1['sanitized_name'] != result2['sanitized_name']
