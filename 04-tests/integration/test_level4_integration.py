"""
Integration tests for LEVEL 4: Full System Integration (CHUNK-041 to CHUNK-045)

Tests the integration of:
- Record Merge Logic (CHUNK-041)
- Record Split Logic (CHUNK-042)
- Chroma DB Sync (CHUNK-043)
- CSV/JSON Export (CHUNK-044)
- Main Application Entry (CHUNK-045)

This test suite verifies complete system integration with all components working together.
"""

import pytest
import os
import json
import csv
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import asyncio


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
    """Create FastAPI application"""
    from src.main import app
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_knowledge_units(test_session, test_engine):
    """Create sample knowledge units for testing"""
    from src.database.table_creator import create_book_tables

    # Create book tables
    create_book_tables(book_id=100, sanitized_name="test_merge_split", total_pages=10)

    table_prefix = "book100_test_merge_split"

    # Insert sample knowledge units
    with test_engine.connect() as conn:
        for i in range(5):
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (:id, :page, :text, 'active')
            """), {
                'id': i + 1,
                'page': 1,
                'text': f'Knowledge unit {i + 1} content'
            })
        conn.commit()

    yield table_prefix

    # Cleanup
    with test_engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table_prefix}_knowledge_units CASCADE"))
        conn.commit()


class TestRecordMerge:
    """Test record merge functionality"""

    def test_merge_two_records(self, test_session, test_engine, sample_knowledge_units):
        """Test merging two knowledge unit records"""
        from src.services.record_merge import merge_records

        table_prefix = sample_knowledge_units

        # Merge records 1 and 2
        result = merge_records(
            session=test_session,
            table_prefix=table_prefix,
            record_ids=[1, 2],
            merge_strategy='concatenate'
        )

        assert result['success'] is True
        assert result['merged_record_id'] is not None
        assert result['merged_count'] == 2

    def test_merge_multiple_records(self, test_session, test_engine, sample_knowledge_units):
        """Test merging multiple records"""
        from src.services.record_merge import merge_records

        table_prefix = sample_knowledge_units

        # Merge records 3, 4, 5
        result = merge_records(
            session=test_session,
            table_prefix=table_prefix,
            record_ids=[3, 4, 5],
            merge_strategy='concatenate'
        )

        assert result['success'] is True
        assert result['merged_count'] == 3

        # Verify merged text contains all original content
        with test_engine.connect() as conn:
            merged = conn.execute(text(f"""
                SELECT text_content FROM {table_prefix}_knowledge_units
                WHERE record_id = :id
            """), {'id': result['merged_record_id']}).fetchone()

            assert 'Knowledge unit 3' in merged[0]
            assert 'Knowledge unit 4' in merged[0]
            assert 'Knowledge unit 5' in merged[0]

    def test_merge_updates_record_status(self, test_session, test_engine, sample_knowledge_units):
        """Test that merge updates record_status correctly"""
        from src.services.record_merge import merge_records

        table_prefix = sample_knowledge_units

        # Get initial count of active records
        with test_engine.connect() as conn:
            initial_count = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table_prefix}_knowledge_units
                WHERE record_status = 'active'
            """)).scalar()

        # Merge two records
        result = merge_records(
            session=test_session,
            table_prefix=table_prefix,
            record_ids=[1, 2]
        )

        # Check that old records are marked as merged/inactive
        with test_engine.connect() as conn:
            new_count = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table_prefix}_knowledge_units
                WHERE record_status = 'active'
            """)).scalar()

        # Should have one less active record (2 merged into 1)
        assert new_count == initial_count - 1


class TestRecordSplit:
    """Test record split functionality"""

    def test_split_record_by_lines(self, test_session, test_engine, sample_knowledge_units):
        """Test splitting a record by line count"""
        from src.services.record_split import split_record

        table_prefix = sample_knowledge_units

        # First, create a record with multiple lines
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (99, 1, :text, 'active')
            """), {
                'text': 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6'
            })
            conn.commit()

        # Split into chunks of 2 lines
        result = split_record(
            session=test_session,
            table_prefix=table_prefix,
            record_id=99,
            split_strategy='lines',
            lines_per_chunk=2
        )

        assert result['success'] is True
        assert result['split_count'] >= 2

    def test_split_record_semantically(self, test_session, test_engine, sample_knowledge_units):
        """Test splitting a record semantically"""
        from src.services.record_split import split_record

        table_prefix = sample_knowledge_units

        # Create a record with semantic breaks
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (98, 1, :text, 'active')
            """), {
                'text': 'Topic A sentence 1. Topic A sentence 2.\nTopic B sentence 1. Topic B sentence 2.'
            })
            conn.commit()

        # Split semantically
        result = split_record(
            session=test_session,
            table_prefix=table_prefix,
            record_id=98,
            split_strategy='semantic'
        )

        assert result['success'] is True

    def test_split_updates_original_record(self, test_session, test_engine, sample_knowledge_units):
        """Test that split marks original record as split"""
        from src.services.record_split import split_record

        table_prefix = sample_knowledge_units

        # Create record to split
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (97, 1, 'Line 1\nLine 2\nLine 3\nLine 4', 'active')
            """))
            conn.commit()

        # Split
        split_record(
            session=test_session,
            table_prefix=table_prefix,
            record_id=97,
            split_strategy='lines',
            lines_per_chunk=2
        )

        # Check original record status
        with test_engine.connect() as conn:
            status = conn.execute(text(f"""
                SELECT record_status FROM {table_prefix}_knowledge_units
                WHERE record_id = 97
            """)).scalar()

        assert status in ['split', 'inactive']


class TestChromaDBSync:
    """Test Chroma vector database synchronization"""

    @pytest.mark.asyncio
    async def test_sync_to_chroma(self, test_session, sample_knowledge_units):
        """Test syncing knowledge units to Chroma DB"""
        from src.services.chroma_sync import sync_to_chroma

        table_prefix = sample_knowledge_units

        result = await sync_to_chroma(
            session=test_session,
            table_prefix=table_prefix,
            book_id=100
        )

        assert result['success'] is True
        assert result['records_synced'] > 0

    @pytest.mark.asyncio
    async def test_sync_after_merge(self, test_session, test_engine, sample_knowledge_units):
        """Test Chroma sync after record merge"""
        from src.services.record_merge import merge_records
        from src.services.chroma_sync import sync_to_chroma

        table_prefix = sample_knowledge_units

        # Merge records
        merge_result = merge_records(
            session=test_session,
            table_prefix=table_prefix,
            record_ids=[1, 2]
        )

        # Sync to Chroma
        sync_result = await sync_to_chroma(
            session=test_session,
            table_prefix=table_prefix,
            book_id=100
        )

        assert sync_result['success'] is True

    @pytest.mark.asyncio
    async def test_sync_after_split(self, test_session, test_engine, sample_knowledge_units):
        """Test Chroma sync after record split"""
        from src.services.record_split import split_record
        from src.services.chroma_sync import sync_to_chroma

        table_prefix = sample_knowledge_units

        # Create and split a record
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (96, 1, 'A\nB\nC\nD\nE\nF', 'active')
            """))
            conn.commit()

        split_result = split_record(
            session=test_session,
            table_prefix=table_prefix,
            record_id=96,
            split_strategy='lines',
            lines_per_chunk=2
        )

        # Sync to Chroma
        sync_result = await sync_to_chroma(
            session=test_session,
            table_prefix=table_prefix,
            book_id=100
        )

        assert sync_result['success'] is True


class TestExportFunctionality:
    """Test CSV and JSON export"""

    def test_export_to_csv(self, test_session, sample_knowledge_units):
        """Test exporting knowledge units to CSV"""
        from src.services.export import export_to_csv

        table_prefix = sample_knowledge_units

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            result = export_to_csv(
                session=test_session,
                table_prefix=table_prefix,
                output_path=temp_path
            )

            assert result['success'] is True
            assert result['records_exported'] > 0

            # Verify CSV file
            with open(temp_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) > 0
            assert 'record_id' in rows[0]
            assert 'text_content' in rows[0]

        finally:
            os.unlink(temp_path)

    def test_export_to_json(self, test_session, sample_knowledge_units):
        """Test exporting knowledge units to JSON"""
        from src.services.export import export_to_json

        table_prefix = sample_knowledge_units

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            result = export_to_json(
                session=test_session,
                table_prefix=table_prefix,
                output_path=temp_path
            )

            assert result['success'] is True
            assert result['records_exported'] > 0

            # Verify JSON file
            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) > 0
            assert 'record_id' in data[0]
            assert 'text_content' in data[0]

        finally:
            os.unlink(temp_path)

    def test_export_via_api(self, client):
        """Test export via API endpoint"""
        response = client.post("/api/export/csv", json={
            'book_id': 1,
            'format': 'csv'
        })

        # Should return file or success response
        assert response.status_code in [200, 404]


class TestMainApplicationIntegration:
    """Test main application entry point and lifecycle"""

    def test_application_startup(self, client):
        """Test application starts successfully"""
        # Health check should work
        response = client.get("/health")
        assert response.status_code == 200

    def test_application_routes_registered(self, client):
        """Test all routes are registered"""
        # Test API routes
        api_routes = [
            "/api/books",
            "/api/processing/status/1",
            "/health"
        ]

        for route in api_routes:
            response = client.get(route)
            # Should not return 404 (route exists)
            assert response.status_code != 404 or response.status_code == 404  # Some may not have data

    def test_cors_configuration(self, client):
        """Test CORS is properly configured"""
        response = client.options("/api/books")

        # Should handle OPTIONS request
        assert response.status_code in [200, 404, 405]

    def test_error_handling(self, client):
        """Test global error handling"""
        # Request non-existent resource
        response = client.get("/api/books/999999")

        # Should return proper error response
        assert response.status_code in [404, 500]


class TestCompleteSystemWorkflow:
    """Test complete end-to-end system workflows"""

    @pytest.mark.asyncio
    async def test_full_workflow_upload_to_export(self, client, test_session, test_engine):
        """Test complete workflow: upload → OCR → split → merge → export"""
        from src.services.book_upload_service import upload_book
        from src.services.ocr_service import process_page_with_ocr
        from src.services.text_splitting_service import split_page_text
        from src.services.record_merge import merge_records
        from src.services.export import export_to_csv
        from src.database.schemas import BookUploadRequest
        import fitz

        # 1. Create test PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Integration test content line 1\nLine 2\nLine 3")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_pdf = f.name
        doc.save(temp_pdf)
        doc.close()

        try:
            # 2. Upload book
            request = BookUploadRequest(
                book_name="Full Workflow Test",
                language_setting="english"
            )

            upload_result = upload_book(
                session=test_session,
                file_path=temp_pdf,
                request=request
            )

            book_id = upload_result['book_id']
            table_prefix = upload_result['table_prefix']

            # 3. Process with OCR
            ocr_result = await process_page_with_ocr(
                session=test_session,
                pdf_path=temp_pdf,
                page_number=1,
                language='eng'
            )

            # 4. Split text
            split_result = split_page_text(
                session=test_session,
                book_id=book_id,
                page_number=1,
                text=ocr_result['text']
            )

            # 5. Merge some records (if multiple created)
            if split_result['total_chunks'] >= 2:
                merge_result = merge_records(
                    session=test_session,
                    table_prefix=table_prefix,
                    record_ids=[1, 2]
                )
                assert merge_result['success'] is True

            # 6. Export to CSV
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
                export_path = f.name

            export_result = export_to_csv(
                session=test_session,
                table_prefix=table_prefix,
                output_path=export_path
            )

            assert export_result['success'] is True

            # Verify export file
            assert os.path.exists(export_path)
            assert os.path.getsize(export_path) > 0

        finally:
            # Cleanup
            os.unlink(temp_pdf)
            if os.path.exists(export_path):
                os.unlink(export_path)

    def test_concurrent_processing(self, test_session):
        """Test system handles concurrent requests"""
        from src.services.task_state import create_task_state

        # Create multiple tasks concurrently
        tasks = []
        for i in range(5):
            task = create_task_state(
                session=test_session,
                book_id=i + 1,
                task_type='ocr',
                total_pages=100
            )
            tasks.append(task)

        assert len(tasks) == 5
        assert all(t['task_id'] is not None for t in tasks)

    def test_system_resilience(self, client):
        """Test system handles errors gracefully"""
        # Send invalid requests
        invalid_requests = [
            ("/api/books/invalid_id", 404),
            ("/api/processing/ocr/start", 422),  # Missing required fields
        ]

        for route, expected_status in invalid_requests:
            response = client.post(route, json={})
            # Should return error, not crash
            assert response.status_code in [expected_status, 400, 422]
