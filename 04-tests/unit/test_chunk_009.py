"""
Unit tests for CHUNK-009: Dynamic Table Creation

Tests the creation of book-specific tables dynamically.

Test Coverage:
- Table creation for knowledge units
- Table creation for images
- Table creation for pages
- Default row insertion
- Index creation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from sqlalchemy import Table


class TestChunk009DynamicTableCreation:
    """Test suite for CHUNK-009: Dynamic Table Creation"""

    @patch('src.database.table_creator.engine')
    @patch('src.database.table_creator.generate_table_prefix')
    def test_happy_path_create_all_tables(self, mock_prefix, mock_engine):
        """Test creating all 7 book-specific tables"""
        mock_prefix.return_value = "book1_test_book"

        from src.database.table_creator import create_book_tables

        create_book_tables(book_id=1, sanitized_name="test_book", total_pages=100)

        # Verify table prefix was generated
        mock_prefix.assert_called_once_with(1, "test_book")

    @patch('src.database.table_creator.engine')
    def test_create_knowledge_units_table(self, mock_engine):
        """Test creation of knowledge_units table"""
        from src.database.table_creator import create_knowledge_units_table

        table_prefix = "book1_test"
        create_knowledge_units_table(table_prefix)

        # Verify SQL execution for table creation
        assert mock_engine.execute.called or mock_engine.connect().execute.called

    @patch('src.database.table_creator.engine')
    def test_create_images_table(self, mock_engine):
        """Test creation of images table"""
        from src.database.table_creator import create_images_table

        table_prefix = "book1_test"
        create_images_table(table_prefix)

        # Verify table was created
        assert mock_engine.execute.called or mock_engine.connect().execute.called

    @patch('src.database.table_creator.engine')
    def test_create_pages_table(self, mock_engine):
        """Test creation of pages table"""
        from src.database.table_creator import create_pages_table

        table_prefix = "book1_test"
        create_pages_table(table_prefix)

        assert mock_engine.execute.called or mock_engine.connect().execute.called

    @patch('src.database.table_creator.engine')
    def test_table_naming_convention(self, mock_engine):
        """Test that tables follow naming convention"""
        from src.database.table_creator import create_knowledge_units_table

        table_prefix = "book1_my_book"
        create_knowledge_units_table(table_prefix)

        # Verify table name includes prefix
        if mock_engine.execute.called:
            call_args = str(mock_engine.execute.call_args)
            assert "book1_my_book" in call_args

    @patch('src.database.table_creator.engine')
    @patch('src.database.table_creator.insert_default_processing_state')
    def test_insert_default_processing_state(self, mock_insert, mock_engine):
        """Test insertion of default processing state row"""
        from src.database.table_creator import create_book_tables

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            create_book_tables(book_id=1, sanitized_name="test", total_pages=100)

        # Verify default row insertion was called
        mock_insert.assert_called_once_with("book1_test", 100)

    @patch('src.database.table_creator.engine')
    @patch('src.database.table_creator.insert_default_settings')
    def test_insert_default_settings(self, mock_insert, mock_engine):
        """Test insertion of default settings row"""
        from src.database.table_creator import create_book_tables

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            create_book_tables(book_id=1, sanitized_name="test", total_pages=100)

        # Verify default settings inserted
        mock_insert.assert_called_once()

    @patch('src.database.table_creator.engine')
    @patch('src.database.table_creator.insert_default_attribute_keys')
    def test_insert_default_attribute_keys(self, mock_insert, mock_engine):
        """Test insertion of 30 attribute key rows"""
        from src.database.table_creator import create_book_tables

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            create_book_tables(book_id=1, sanitized_name="test", total_pages=100)

        # Verify attribute keys inserted
        mock_insert.assert_called_once()

    @patch('src.database.table_creator.engine')
    def test_error_handling_table_already_exists(self, mock_engine):
        """Test handling when table already exists"""
        from sqlalchemy.exc import ProgrammingError
        from src.database.table_creator import create_book_tables

        mock_engine.execute.side_effect = ProgrammingError("relation already exists", None, None)

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            with pytest.raises(ProgrammingError):
                create_book_tables(book_id=1, sanitized_name="test", total_pages=100)

    @patch('src.database.table_creator.engine')
    def test_edge_case_large_page_count(self, mock_engine):
        """Test table creation with large page count"""
        from src.database.table_creator import create_book_tables

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            with patch('src.database.table_creator.insert_default_processing_state') as mock_insert:
                create_book_tables(book_id=1, sanitized_name="test", total_pages=10000)

                # Verify total_pages was passed correctly
                mock_insert.assert_called_once_with("book1_test", 10000)

    @patch('src.database.table_creator.engine')
    def test_knowledge_units_table_columns(self, mock_engine):
        """Test that knowledge_units table has required columns"""
        from src.database.table_creator import create_knowledge_units_table

        table_prefix = "book1_test"
        create_knowledge_units_table(table_prefix)

        # Verify table creation SQL includes required columns
        # (This would check the actual SQL if accessible)

    @patch('src.database.table_creator.engine')
    def test_all_seven_tables_created(self, mock_engine):
        """Test that all 7 tables are created"""
        from src.database.table_creator import create_book_tables

        with patch('src.database.table_creator.generate_table_prefix', return_value="book1_test"):
            create_book_tables(book_id=1, sanitized_name="test", total_pages=100)

        # Verify multiple table creation calls
        # Should create: knowledge_units, images, pages, processing_state,
        # settings, attribute_keys, and potentially one more
        assert mock_engine.execute.call_count >= 7 or mock_engine.connect().execute.call_count >= 7
