"""
Database utility functions for table operations.

Helper functions for working with book-specific tables.
"""

from sqlalchemy import text
from src.database.connection import SessionLocal


def get_table_prefix(book_id: int) -> str:
    """
    Get table prefix for a book_id from books_metadata.

    Args:
        book_id: Book ID to lookup

    Returns:
        str: Table prefix (e.g., 'book1_my_book')

    Raises:
        ValueError: If book_id not found in books_metadata
    """
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        )
        row = result.fetchone()

        if not row:
            raise ValueError(f"Book ID {book_id} not found in books_metadata")

        return row[0]
    finally:
        db.close()


def get_table_name(book_id: int, table_type: str) -> str:
    """
    Get full table name for a book and table type.

    Args:
        book_id: Book ID
        table_type: Type of table (e.g., 'knowledge_units', 'pages', 'images')

    Returns:
        str: Full table name (e.g., 'book1_my_book_knowledge_units')
    """
    prefix = get_table_prefix(book_id)
    return f"{prefix}_{table_type}"
