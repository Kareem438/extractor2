"""
CHUNK-003: Books Metadata Model

SQLAlchemy model for books_metadata table.
This table stores metadata for all books in the system.
"""

from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, func, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BooksMetadata(Base):
    """
    Books metadata table model.

    Stores high-level information about each book uploaded to the system.
    Each book gets a unique book_id and sanitized table prefix for its data tables.
    """
    __tablename__ = "books_metadata"

    # Core identification fields
    book_id = Column(Integer, primary_key=True, autoincrement=True)
    book_name = Column(String(255), nullable=False)
    sanitized_name = Column(String(100), nullable=False, unique=True)
    table_prefix = Column(String(100), nullable=False, unique=True)

    # Upload metadata
    upload_date = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # File information
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    total_pages = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=True)  # Path to uploaded file

    # Processing status
    processing_status = Column(
        String(50),
        nullable=False,
        default="uploaded",
        server_default="uploaded"
    )

    # Extraction method (v1, v2, or both)
    extraction_method = Column(
        String(10),
        nullable=False,
        default="v2",
        server_default="v2"
    )

    def __repr__(self):
        return f"<BooksMetadata(book_id={self.book_id}, book_name='{self.book_name}', status='{self.processing_status}')>"
