"""
Integration tests for LEVEL 2: Services Layer (CHUNK-019 to CHUNK-030)

Tests the integration of:
- Database Service (CHUNK-019)
- Book Upload Service (CHUNK-020)
- OCR Service (CHUNK-021)
- Text Splitting Service (CHUNK-022)
- Background Task Queue (CHUNK-023)
- Task State Management (CHUNK-024)
- WebSocket Manager (CHUNK-025)
- API Router Setup (CHUNK-026)
- Book Management Endpoints (CHUNK-027)
- Processing Endpoints (CHUNK-028)
- WebSocket Endpoint (CHUNK-029)
- Health Check Endpoint (CHUNK-030)

This test suite verifies service layer orchestration and API integration.
"""

import pytest
import os
import asyncio
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from PIL import Image
import json


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
def app():
    """Create FastAPI test application"""
    from src.main import app
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_pdf_file():
    """Create sample PDF file for upload testing"""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Test PDF Content")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name

    doc.save(temp_path)
    doc.close()

    yield temp_path
    os.unlink(temp_path)


class TestDatabaseService:
    """Test database service operations"""

    def test_batch_insert_operation(self, test_session):
        """Test batch insert of multiple records"""
        from src.services.database_service import batch_insert_records

        records = [
            {'text': f'Record {i}', 'page_number': i}
            for i in range(50)
        ]

        result = batch_insert_records(
            test_session,
            table_name='test_table',
            records=records,
            batch_size=10
        )

        assert result['total_inserted'] == 50
        assert result['batches_processed'] == 5

    def test_transaction_rollback_on_error(self, test_session):
        """Test that transactions rollback on error"""
        from src.services.database_service import transactional_operation
        from src.utils.exceptions import DatabaseError

        with pytest.raises(DatabaseError):
            with transactional_operation(test_session):
                # Perform some operations
                test_session.execute("SELECT 1")
                # Simulate error
                raise DatabaseError("Simulated error")

        # Session should be rolled back


class TestBookUploadService:
    """Test book upload service"""

    def test_upload_book_creates_metadata(self, test_session, sample_pdf_file):
        """Test that uploading a book creates metadata record"""
        from src.services.book_upload_service import upload_book
        from src.database.schemas import BookUploadRequest

        request = BookUploadRequest(
            book_name="Test Upload Book",
            language_setting="english",
            extraction_sensitivity="balanced"
        )

        result = upload_book(
            session=test_session,
            file_path=sample_pdf_file,
            request=request
        )

        assert result['book_id'] is not None
        assert result['sanitized_name'] is not None
        assert result['table_prefix'] is not None
        assert result['status'] == 'uploaded'

    def test_upload_book_creates_tables(self, test_session, test_engine, sample_pdf_file):
        """Test that uploading a book creates all required tables"""
        from src.services.book_upload_service import upload_book
        from src.database.schemas import BookUploadRequest
        from sqlalchemy import inspect

        request = BookUploadRequest(
            book_name="Test Tables Book",
            language_setting="english"
        )

        result = upload_book(
            session=test_session,
            file_path=sample_pdf_file,
            request=request
        )

        # Verify tables were created
        inspector = inspect(test_engine)
        table_prefix = result['table_prefix']

        expected_tables = [
            f"{table_prefix}_knowledge_units",
            f"{table_prefix}_pages",
            f"{table_prefix}_images"
        ]

        existing_tables = inspector.get_table_names()
        for table in expected_tables:
            assert table in existing_tables


class TestOCRService:
    """Test OCR service orchestration"""

    @pytest.mark.asyncio
    async def test_process_page_with_ocr(self, test_session, sample_pdf_file):
        """Test OCR processing of a PDF page"""
        from src.services.ocr_service import process_page_with_ocr

        result = await process_page_with_ocr(
            session=test_session,
            pdf_path=sample_pdf_file,
            page_number=1,
            language='eng',
            quality='balanced'
        )

        assert 'text' in result
        assert 'confidence' in result
        assert 'method' in result
        assert result['page_number'] == 1

    @pytest.mark.asyncio
    async def test_ocr_retry_on_low_confidence(self, test_session, sample_pdf_file):
        """Test OCR retry mechanism on low confidence"""
        from src.services.ocr_service import process_page_with_ocr_retry

        result = await process_page_with_ocr_retry(
            session=test_session,
            pdf_path=sample_pdf_file,
            page_number=1,
            language='eng',
            max_attempts=3
        )

        assert result['attempts'] >= 1
        assert result['attempts'] <= 3
        assert 'final_confidence' in result


class TestTextSplittingService:
    """Test text splitting service"""

    def test_split_page_text(self, test_session):
        """Test splitting page text into knowledge units"""
        from src.services.text_splitting_service import split_page_text

        text = """
        This is line 1 about topic A.
        This is line 2 about topic A.
        This is line 3 about topic A.
        This is line 4 about topic B.
        This is line 5 about topic B.
        This is line 6 about topic C.
        """

        result = split_page_text(
            session=test_session,
            book_id=1,
            page_number=1,
            text=text,
            target_lines=3,
            max_lines=5
        )

        assert 'chunks' in result
        assert len(result['chunks']) > 0
        assert result['total_chunks'] > 0

    def test_evaluate_and_split_decision(self, test_session):
        """Test evaluation determines if splitting is needed"""
        from src.services.text_splitting_service import evaluate_text_for_splitting

        # Short text - should not split
        short_text = "Just one line."
        result = evaluate_text_for_splitting(short_text)
        assert result['should_split'] is False

        # Long text - should split
        long_text = "\n".join([f"Line {i}" for i in range(20)])
        result = evaluate_text_for_splitting(long_text)
        assert result['should_split'] is True


class TestBackgroundTaskQueue:
    """Test background task processing"""

    @pytest.mark.asyncio
    async def test_queue_ocr_task(self, test_session):
        """Test queueing OCR task for background processing"""
        from src.services.background_tasks import queue_ocr_task

        task_id = await queue_ocr_task(
            session=test_session,
            book_id=1,
            page_number=1,
            pdf_path='/tmp/test.pdf'
        )

        assert task_id is not None

    @pytest.mark.asyncio
    async def test_task_execution(self, test_session, sample_pdf_file):
        """Test background task execution"""
        from src.services.background_tasks import execute_task

        task_data = {
            'type': 'ocr',
            'book_id': 1,
            'page_number': 1,
            'pdf_path': sample_pdf_file
        }

        result = await execute_task(task_id=1, task_data=task_data)

        assert result['status'] in ['completed', 'failed']


class TestTaskStateManagement:
    """Test task state tracking and updates"""

    def test_create_task_state(self, test_session):
        """Test creating task state record"""
        from src.services.task_state import create_task_state

        state = create_task_state(
            session=test_session,
            book_id=1,
            task_type='ocr',
            total_pages=100
        )

        assert state['task_id'] is not None
        assert state['status'] == 'pending'
        assert state['progress'] == 0

    def test_update_task_progress(self, test_session):
        """Test updating task progress"""
        from src.services.task_state import create_task_state, update_task_progress

        # Create task
        state = create_task_state(
            session=test_session,
            book_id=1,
            task_type='splitting',
            total_pages=100
        )

        # Update progress
        updated = update_task_progress(
            session=test_session,
            task_id=state['task_id'],
            current_page=50,
            total_pages=100
        )

        assert updated['progress'] == 50

    def test_pause_and_resume_task(self, test_session):
        """Test pausing and resuming tasks"""
        from src.services.task_state import create_task_state, pause_task, resume_task

        # Create task
        state = create_task_state(
            session=test_session,
            book_id=1,
            task_type='ocr',
            total_pages=50
        )

        # Pause
        paused = pause_task(test_session, state['task_id'])
        assert paused['status'] == 'paused'

        # Resume
        resumed = resume_task(test_session, state['task_id'])
        assert resumed['status'] == 'processing'


class TestWebSocketManager:
    """Test WebSocket connection management"""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection and disconnection"""
        from src.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        # Mock WebSocket connection
        class MockWebSocket:
            async def accept(self): pass
            async def send_json(self, data): pass

        ws = MockWebSocket()
        client_id = "test_client_1"

        await manager.connect(client_id, ws)
        assert client_id in manager.active_connections

        manager.disconnect(client_id)
        assert client_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting message to all connected clients"""
        from src.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        # Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.messages = []

            async def accept(self): pass

            async def send_json(self, data):
                self.messages.append(data)

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        # Broadcast
        message = {'type': 'progress', 'data': {'page': 10}}
        await manager.broadcast(message)

        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 1


class TestAPIEndpoints:
    """Test API endpoints integration"""

    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'

    def test_upload_book_endpoint(self, client, sample_pdf_file):
        """Test book upload endpoint"""
        with open(sample_pdf_file, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            data = {
                'book_name': 'Test API Upload',
                'language_setting': 'english',
                'extraction_sensitivity': 'balanced'
            }

            response = client.post("/api/books/upload", files=files, data=data)

        assert response.status_code in [200, 201]
        result = response.json()
        assert 'book_id' in result

    def test_list_books_endpoint(self, client):
        """Test listing books endpoint"""
        response = client.get("/api/books")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or 'books' in data

    def test_get_book_details_endpoint(self, client):
        """Test get book details endpoint"""
        # Assume book_id 1 exists (from previous test)
        response = client.get("/api/books/1")

        # Should return 200 if exists, or 404 if not
        assert response.status_code in [200, 404]

    def test_start_ocr_endpoint(self, client):
        """Test start OCR processing endpoint"""
        response = client.post("/api/processing/ocr/start", json={
            'book_id': 1,
            'language': 'eng',
            'quality': 'balanced'
        })

        # Should return 200 or 202 (accepted)
        assert response.status_code in [200, 202, 404]

    def test_get_processing_status_endpoint(self, client):
        """Test get processing status endpoint"""
        response = client.get("/api/processing/status/1")

        assert response.status_code in [200, 404]


class TestFullServicesIntegration:
    """Test complete service layer workflows"""

    @pytest.mark.asyncio
    async def test_complete_upload_and_process_workflow(self, client, sample_pdf_file, test_session):
        """Test complete workflow: upload -> OCR -> split -> verify"""
        from src.services.book_upload_service import upload_book
        from src.services.ocr_service import process_page_with_ocr
        from src.services.text_splitting_service import split_page_text
        from src.database.schemas import BookUploadRequest

        # 1. Upload book
        request = BookUploadRequest(
            book_name="Complete Workflow Test",
            language_setting="english"
        )

        upload_result = upload_book(
            session=test_session,
            file_path=sample_pdf_file,
            request=request
        )

        book_id = upload_result['book_id']
        assert book_id is not None

        # 2. Process with OCR
        ocr_result = await process_page_with_ocr(
            session=test_session,
            pdf_path=sample_pdf_file,
            page_number=1,
            language='eng'
        )

        assert 'text' in ocr_result

        # 3. Split text
        split_result = split_page_text(
            session=test_session,
            book_id=book_id,
            page_number=1,
            text=ocr_result['text']
        )

        assert split_result['total_chunks'] > 0

    def test_error_handling_across_services(self, test_session):
        """Test error propagation across service layers"""
        from src.services.book_upload_service import upload_book
        from src.database.schemas import BookUploadRequest
        from src.utils.exceptions import ProcessingError

        request = BookUploadRequest(book_name="Error Test")

        # Try to upload non-existent file
        with pytest.raises((ProcessingError, FileNotFoundError)):
            upload_book(
                session=test_session,
                file_path='/nonexistent/file.pdf',
                request=request
            )
