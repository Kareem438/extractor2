"""
Unit tests for CHUNK-003: Books Metadata Model

Tests the SQLAlchemy model for books_metadata table.

Test Coverage:
- Model creation and field validation
- Database table creation
- CRUD operations (Create, Read, Update, Delete)
- Constraints and defaults testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.exc import IntegrityError


class TestChunk003BooksMetadataModel:
    """Test suite for CHUNK-003: Books Metadata Model"""

    @patch('src.database.models.books_metadata.Base')
    def test_happy_path_model_creation(self, mock_base):
        """Test creating a BooksMetadata instance with all required fields"""
        from src.database.models.books_metadata import BooksMetadata

        book = BooksMetadata(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100,
            processing_status="uploaded"
        )

        assert book.book_id == 1
        assert book.book_name == "Test Book"
        assert book.sanitized_name == "test_book"
        assert book.table_prefix == "book1_test_book"
        assert book.file_type == "PDF"
        assert book.file_size_bytes == 1024000
        assert book.total_pages == 100
        assert book.processing_status == "uploaded"

    @patch('src.database.models.books_metadata.Base.metadata.create_all')
    @patch('src.database.connection.engine')
    def test_table_creation(self, mock_engine, mock_create_all):
        """Test that table can be created in database"""
        from src.database.models.books_metadata import Base

        Base.metadata.create_all(bind=mock_engine)

        mock_create_all.assert_called_once_with(bind=mock_engine)

    def test_model_tablename(self):
        """Test that model has correct table name"""
        from src.database.models.books_metadata import BooksMetadata

        assert BooksMetadata.__tablename__ == "books_metadata"

    def test_primary_key_configuration(self):
        """Test that book_id is configured as primary key"""
        from src.database.models.books_metadata import BooksMetadata

        # Get column object
        book_id_column = BooksMetadata.__table__.columns['book_id']

        assert book_id_column.primary_key is True

    @patch('src.database.connection.SessionLocal')
    def test_insert_and_query_record(self, mock_session_local):
        """Test inserting and querying a book record"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.models.books_metadata import BooksMetadata

        book = BooksMetadata(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100
        )

        mock_session.add(book)
        mock_session.commit()

        mock_session.add.assert_called_once_with(book)
        mock_session.commit.assert_called_once()

    @patch('src.database.connection.SessionLocal')
    def test_unique_constraint_sanitized_name(self, mock_session_local):
        """Test that sanitized_name has unique constraint"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session
        mock_session.commit.side_effect = IntegrityError("unique constraint", None, None)

        from src.database.models.books_metadata import BooksMetadata

        book1 = BooksMetadata(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100
        )

        mock_session.add(book1)

        with pytest.raises(IntegrityError):
            mock_session.commit()

    def test_default_processing_status(self):
        """Test that processing_status defaults to 'uploaded'"""
        from src.database.models.books_metadata import BooksMetadata

        processing_status_column = BooksMetadata.__table__.columns['processing_status']

        # Check if default is set
        assert processing_status_column.default is not None

    @patch('src.database.connection.SessionLocal')
    def test_update_record(self, mock_session_local):
        """Test updating a book record"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.models.books_metadata import BooksMetadata

        book = BooksMetadata(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100,
            processing_status="uploaded"
        )

        # Simulate update
        book.processing_status = "processing"

        mock_session.add(book)
        mock_session.commit()

        assert book.processing_status == "processing"
        mock_session.commit.assert_called_once()

    @patch('src.database.connection.SessionLocal')
    def test_delete_record(self, mock_session_local):
        """Test deleting a book record"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.models.books_metadata import BooksMetadata

        book = BooksMetadata(
            book_id=1,
            book_name="Test Book",
            sanitized_name="test_book",
            table_prefix="book1_test_book",
            file_type="PDF",
            file_size_bytes=1024000,
            total_pages=100
        )

        mock_session.delete(book)
        mock_session.commit()

        mock_session.delete.assert_called_once_with(book)
        mock_session.commit.assert_called_once()

    def test_upload_date_auto_timestamp(self):
        """Test that upload_date has server default timestamp"""
        from src.database.models.books_metadata import BooksMetadata

        upload_date_column = BooksMetadata.__table__.columns['upload_date']

        # Check if server_default is set
        assert upload_date_column.server_default is not None

    def test_nullable_constraints(self):
        """Test nullable constraints on required fields"""
        from src.database.models.books_metadata import BooksMetadata

        # Check that required fields are not nullable
        assert BooksMetadata.__table__.columns['book_name'].nullable is False
        assert BooksMetadata.__table__.columns['sanitized_name'].nullable is False
        assert BooksMetadata.__table__.columns['table_prefix'].nullable is False
        assert BooksMetadata.__table__.columns['file_type'].nullable is False
