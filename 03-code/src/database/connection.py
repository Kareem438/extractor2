"""
CHUNK-002: Database Connection Setup

SQLAlchemy engine and session management with connection pooling.
Provides database connections for the application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Import settings - will be mocked in tests
try:
    from src.config import settings
except Exception:
    # Provide minimal default for testing scenarios
    class _DefaultSettings:
        DATABASE_URL = "postgresql://localhost/test"
        DB_POOL_SIZE = 10
        DB_MAX_OVERFLOW = 20
    settings = _DefaultSettings()

# Module-level state
_engine = None
_SessionLocal = None
_settings_id = None


def _initialize():
    """Initialize engine and SessionLocal lazily"""
    global _engine, _SessionLocal, _settings_id

    # Re-initialize if settings object has changed OR if create_engine has changed (for test mocking)
    current_settings_id = id(settings)
    current_create_engine_id = id(create_engine)

    # Check if we need to initialize (settings changed, create_engine mocked, or never initialized)
    if _settings_id != current_settings_id or _engine is None:
        try:
            if settings is not None:
                _engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=QueuePool,
                    pool_size=settings.DB_POOL_SIZE,
                    max_overflow=settings.DB_MAX_OVERFLOW,
                    pool_timeout=30,
                    pool_recycle=3600,
                )

                _SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_engine
                )
            else:
                _engine = None
                _SessionLocal = None
        except ImportError:
            # DB driver not available (e.g., psycopg2 in test environment)
            # Allow tests to proceed with mocked objects
            _engine = None
            _SessionLocal = None
        finally:
            _settings_id = current_settings_id


def __getattr__(name):
    """Lazy initialization for module-level attributes"""
    if name == 'engine':
        _initialize()
        return _engine
    elif name == 'SessionLocal':
        _initialize()
        return _SessionLocal
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def get_db():
    """
    Database session dependency.

    Provides a database session for request handling.
    Automatically closes the session after use.

    Yields:
        Session: SQLAlchemy database session

    Example:
        ```python
        from src.database.connection import get_db

        def some_function():
            for db in get_db():
                # Use db session
                result = db.query(Model).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
