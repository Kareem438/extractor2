"""
CHUNK-004: Sanitization Utilities

Functions for sanitizing book names and generating table prefixes.
Ensures safe naming for database tables and file systems.
"""

import re


def sanitize_book_name(filename: str) -> str:
    """
    Sanitize book name for table naming.

    Converts a filename into a safe database table name component by:
    - Removing file extension
    - Converting to lowercase
    - Replacing spaces with underscores
    - Removing special characters (keeping only a-z, 0-9, _)
    - Limiting to 50 characters
    - Providing default "book" for empty results

    Args:
        filename: Original filename (e.g., "My Book.pdf")

    Returns:
        Sanitized name safe for database table naming (e.g., "my_book")

    Examples:
        >>> sanitize_book_name("My Book.pdf")
        'my_book'
        >>> sanitize_book_name("Book@#$Name!.pdf")
        'bookname'
        >>> sanitize_book_name("@#$%.pdf")
        'book'
    """
    # Remove extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename

    # Convert to lowercase
    name = name.lower()

    # Replace spaces with underscores
    name = name.replace(' ', '_')

    # Remove special characters (keep only a-z, 0-9, _)
    name = re.sub(r'[^a-z0-9_]', '', name)

    # Limit to 50 characters
    name = name[:50]

    # Ensure not empty - provide default fallback
    if not name:
        name = "book"

    return name


def generate_table_prefix(book_id: int, sanitized_name: str) -> str:
    """
    Generate table prefix for book-specific tables.

    Creates a unique prefix in the format: book{N}_{name}
    This prefix is used for all per-book tables (raw_data, processed_data, etc.)

    Args:
        book_id: Unique book identifier (e.g., 1, 2, 3, ...)
        sanitized_name: Pre-sanitized book name (e.g., "my_book")

    Returns:
        Table prefix string (e.g., "book1_my_book")

    Examples:
        >>> generate_table_prefix(1, "my_book")
        'book1_my_book'
        >>> generate_table_prefix(42, "test")
        'book42_test'
    """
    return f"book{book_id}_{sanitized_name}"


def get_table_prefix_from_book_id(book_id: int) -> str:
    """
    Get the table prefix for a book by querying the books_metadata table.

    Args:
        book_id: The book ID

    Returns:
        Table prefix string (e.g., "book1_my_book")

    Raises:
        ValueError: If book_id is not found in database
    """
    from sqlalchemy import text
    from src.database.connection import engine

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT table_prefix FROM books_metadata WHERE book_id = :book_id"),
            {"book_id": book_id}
        )
        row = result.fetchone()

        if not row:
            raise ValueError(f"Book with ID {book_id} not found")

        return row[0]
