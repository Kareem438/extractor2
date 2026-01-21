"""
Unit tests for CHUNK-002: Database Connection Setup

Tests SQLAlchemy engine and session management with connection pooling.

Test Coverage:
- Database connection establishment
- Connection pool configuration
- Session creation and cleanup
- Connection error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.pool import QueuePool


class TestChunk002DatabaseConnection:
    """Test suite for CHUNK-002: Database Connection Setup"""

    @patch('src.database.connection.create_engine')
    @patch('src.database.connection.settings')
    def test_happy_path_engine_creation(self, mock_settings, mock_create_engine):
        """Test normal database engine creation with proper configuration"""
        mock_settings.DATABASE_URL = 'postgresql://user:pass@localhost:5432/test_db'
        mock_settings.DB_POOL_SIZE = 10
        mock_settings.DB_MAX_OVERFLOW = 20

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        from src.database.connection import engine

        # Verify create_engine was called with correct parameters
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args

        assert call_args[0][0] == 'postgresql://user:pass@localhost:5432/test_db'
        assert call_args[1]['poolclass'] == QueuePool
        assert call_args[1]['pool_size'] == 10
        assert call_args[1]['max_overflow'] == 20

    @patch('src.database.connection.SessionLocal')
    def test_happy_path_session_creation(self, mock_session_local):
        """Test database session creation and cleanup"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.connection import get_db

        # Use the generator
        db_gen = get_db()
        db = next(db_gen)

        assert db == mock_session
        mock_session_local.assert_called_once()

    @patch('src.database.connection.SessionLocal')
    def test_session_cleanup_on_success(self, mock_session_local):
        """Test that session is properly closed after successful use"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.connection import get_db

        # Simulate normal usage
        db_gen = get_db()
        db = next(db_gen)

        # Close the generator
        try:
            next(db_gen)
        except StopIteration:
            pass

        # Verify session was closed
        mock_session.close.assert_called_once()

    @patch('src.database.connection.SessionLocal')
    def test_session_cleanup_on_exception(self, mock_session_local):
        """Test that session is closed even when exception occurs"""
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        from src.database.connection import get_db

        db_gen = get_db()
        db = next(db_gen)

        # Simulate exception
        try:
            db_gen.throw(Exception("Test exception"))
        except Exception:
            pass

        # Verify session was still closed
        mock_session.close.assert_called_once()

    @patch('src.database.connection.create_engine')
    def test_error_handling_invalid_connection_string(self, mock_create_engine):
        """Test error handling with invalid database connection string"""
        mock_create_engine.side_effect = OperationalError("Invalid connection", None, None)

        with pytest.raises(OperationalError):
            from src.database.connection import engine

    @patch('src.database.connection.create_engine')
    @patch('src.database.connection.settings')
    def test_connection_pool_timeout_handling(self, mock_settings, mock_create_engine):
        """Test handling of connection pool timeout"""
        mock_settings.DATABASE_URL = 'postgresql://user:pass@localhost:5432/test_db'
        mock_settings.DB_POOL_SIZE = 10
        mock_settings.DB_MAX_OVERFLOW = 20

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        from src.database.connection import engine

        # Verify pool_timeout was set
        call_kwargs = mock_create_engine.call_args[1]
        assert 'pool_timeout' in call_kwargs
        assert call_kwargs['pool_timeout'] == 30

    @patch('src.database.connection.create_engine')
    @patch('src.database.connection.settings')
    def test_connection_pool_recycle_configuration(self, mock_settings, mock_create_engine):
        """Test that connection pool recycle is configured"""
        mock_settings.DATABASE_URL = 'postgresql://user:pass@localhost:5432/test_db'
        mock_settings.DB_POOL_SIZE = 10
        mock_settings.DB_MAX_OVERFLOW = 20

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        from src.database.connection import engine

        # Verify pool_recycle was set (prevents stale connections)
        call_kwargs = mock_create_engine.call_args[1]
        assert 'pool_recycle' in call_kwargs
        assert call_kwargs['pool_recycle'] == 3600

    @patch('src.database.connection.create_engine')
    @patch('src.database.connection.settings')
    def test_edge_case_custom_pool_sizes(self, mock_settings, mock_create_engine):
        """Test custom pool size configuration"""
        mock_settings.DATABASE_URL = 'postgresql://user:pass@localhost:5432/test_db'
        mock_settings.DB_POOL_SIZE = 5
        mock_settings.DB_MAX_OVERFLOW = 10

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        from src.database.connection import engine

        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs['pool_size'] == 5
        assert call_kwargs['max_overflow'] == 10
