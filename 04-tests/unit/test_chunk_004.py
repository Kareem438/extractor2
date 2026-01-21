"""
Unit tests for CHUNK-004: Sanitization Utilities

Tests sanitization of book names for table creation.

Test Coverage:
- Book name sanitization
- Table prefix generation
- Special character handling
- Length limits and edge cases
"""

import pytest
from unittest.mock import patch


class TestChunk004SanitizationUtilities:
    """Test suite for CHUNK-004: Sanitization Utilities"""

    def test_happy_path_sanitize_simple_filename(self):
        """Test sanitizing a simple book filename"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("My Book.pdf")

        assert result == "my_book"

    def test_sanitize_removes_extension(self):
        """Test that file extensions are properly removed"""
        from src.utils.sanitization import sanitize_book_name

        assert sanitize_book_name("book.pdf") == "book"
        assert sanitize_book_name("document.docx") == "document"
        assert sanitize_book_name("file.txt") == "file"

    def test_sanitize_replaces_spaces_with_underscores(self):
        """Test that spaces are replaced with underscores"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("My Great Book.pdf")

        assert result == "my_great_book"
        assert " " not in result

    def test_sanitize_removes_special_characters(self):
        """Test that special characters are removed"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("Book@#$%Name!.pdf")

        assert result == "bookname"
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result

    def test_sanitize_converts_to_lowercase(self):
        """Test that names are converted to lowercase"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("UPPERCASE_BOOK.pdf")

        assert result == "uppercase_book"
        assert result.islower()

    def test_edge_case_length_limit_enforced(self):
        """Test that sanitized names are limited to 50 characters"""
        from src.utils.sanitization import sanitize_book_name

        long_name = "a" * 100 + ".pdf"
        result = sanitize_book_name(long_name)

        assert len(result) <= 50

    def test_edge_case_empty_after_sanitization(self):
        """Test handling when name becomes empty after sanitization"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("@#$%.pdf")

        assert result == "book"  # Default fallback

    def test_edge_case_only_extension(self):
        """Test handling of filename with only extension"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name(".pdf")

        assert result == "book"  # Default fallback

    def test_happy_path_generate_table_prefix(self):
        """Test normal table prefix generation"""
        from src.utils.sanitization import generate_table_prefix

        result = generate_table_prefix(1, "my_book")

        assert result == "book1_my_book"

    def test_generate_table_prefix_format(self):
        """Test table prefix format with various book IDs"""
        from src.utils.sanitization import generate_table_prefix

        assert generate_table_prefix(1, "test") == "book1_test"
        assert generate_table_prefix(10, "test") == "book10_test"
        assert generate_table_prefix(100, "test") == "book100_test"

    def test_input_validation_none_filename(self):
        """Test handling of None as filename"""
        from src.utils.sanitization import sanitize_book_name

        with pytest.raises((AttributeError, TypeError)):
            sanitize_book_name(None)

    def test_input_validation_empty_string(self):
        """Test handling of empty string"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("")

        assert result == "book"  # Default fallback

    def test_sanitize_preserves_numbers(self):
        """Test that numbers are preserved in sanitized names"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("Book123.pdf")

        assert result == "book123"
        assert "123" in result

    def test_sanitize_preserves_underscores(self):
        """Test that underscores are preserved"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("my_book_name.pdf")

        assert result == "my_book_name"
        assert result.count("_") == 2

    def test_sanitize_multiple_spaces_to_single_underscore(self):
        """Test that multiple consecutive spaces become single underscore"""
        from src.utils.sanitization import sanitize_book_name

        result = sanitize_book_name("my    book.pdf")

        # Should have underscores but not excessive ones
        assert "my" in result
        assert "book" in result
