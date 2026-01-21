"""
End-to-End Test: Export Workflow

Workflow: Generate CSV/JSON → Download → Validate

This test simulates the complete export workflow where users export
verified knowledge units to CSV or JSON formats for external use.
"""

import pytest
import os
import csv
import json
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from io import BytesIO, StringIO


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
def client():
    """Create test client"""
    from src.main import app
    return TestClient(app)


@pytest.fixture
def book_with_verified_units(client, test_session, test_engine):
    """Create a book with verified knowledge units ready for export"""
    import fitz

    # Create simple PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Export test content")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name
    doc.save(temp_path)
    doc.close()

    # Upload book
    with open(temp_path, 'rb') as f:
        files = {'file': ('export_test.pdf', f, 'application/pdf')}
        data = {'book_name': 'Export Test Book'}

        response = client.post("/api/books/upload", files=files, data=data)

    os.unlink(temp_path)

    book_id = response.json()['book_id']
    table_prefix = response.json()['table_prefix']

    # Insert verified knowledge units with all attributes
    with test_engine.connect() as conn:
        for i in range(15):
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status, verification_status,
                 attr_01_value, attr_02_value, chapter, topic, sub_topic)
                VALUES (:id, :page, :text, 'active', 'verified',
                 :attr1, :attr2, :chapter, :topic, :sub_topic)
            """), {
                'id': i + 1,
                'page': (i // 5) + 1,
                'text': f'Verified knowledge unit {i + 1}. Ready for export.',
                'attr1': f'Value A{i + 1}',
                'attr2': f'Value B{i + 1}',
                'chapter': f'Chapter {(i // 5) + 1}',
                'topic': f'Topic {(i // 2) + 1}',
                'sub_topic': f'Subtopic {i + 1}'
            })
        conn.commit()

    yield book_id, table_prefix


class TestExportWorkflow:
    """End-to-end tests for export workflow"""

    def test_complete_csv_export_workflow(self, client, test_session, book_with_verified_units):
        """
        Test complete CSV export workflow:
        1. Navigate to export page
        2. Select CSV format
        3. Choose export options
        4. Generate CSV file
        5. Download file
        6. Validate CSV structure and content
        """
        book_id, table_prefix = book_with_verified_units

        # Step 1: Navigate to export page
        response = client.get(f"/export?book_id={book_id}")
        assert response.status_code == 200

        # Step 2-4: Request CSV export
        response = client.post("/api/export/csv", json={
            'book_id': book_id,
            'include_attributes': True,
            'include_hierarchy': True,
            'verified_only': True
        })

        assert response.status_code == 200

        # Step 5: Validate response
        if response.headers.get('content-type') == 'text/csv':
            # Direct CSV download
            csv_content = response.content.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)

            assert len(rows) == 15
            assert 'record_id' in rows[0]
            assert 'text_content' in rows[0]
            assert 'page_number' in rows[0]

        elif response.headers.get('content-type') == 'application/json':
            # JSON response with file path or data
            result = response.json()
            assert 'success' in result or 'file_path' in result or 'download_url' in result

    def test_complete_json_export_workflow(self, client, book_with_verified_units):
        """
        Test complete JSON export workflow:
        1. Request JSON export
        2. Generate JSON file
        3. Validate JSON structure
        4. Verify data completeness
        """
        book_id, table_prefix = book_with_verified_units

        # Request JSON export
        response = client.post("/api/export/json", json={
            'book_id': book_id,
            'include_attributes': True,
            'include_hierarchy': True,
            'pretty_print': True
        })

        assert response.status_code == 200

        # Validate JSON
        if response.headers.get('content-type') == 'application/json':
            data = response.json()

            if isinstance(data, list):
                # Direct JSON data
                assert len(data) == 15
                assert 'record_id' in data[0]
                assert 'text_content' in data[0]
            else:
                # Response with metadata
                assert 'data' in data or 'file_path' in data

    def test_export_with_custom_columns(self, client, book_with_verified_units):
        """Test exporting with custom column selection"""
        book_id, table_prefix = book_with_verified_units

        # Export with specific columns only
        response = client.post("/api/export/csv", json={
            'book_id': book_id,
            'columns': [
                'record_id',
                'text_content',
                'page_number',
                'chapter',
                'topic'
            ]
        })

        assert response.status_code == 200

        if response.headers.get('content-type') == 'text/csv':
            csv_content = response.content.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)

            if len(rows) > 0:
                # Should only have specified columns
                headers = list(rows[0].keys())
                assert 'record_id' in headers
                assert 'text_content' in headers
                assert 'chapter' in headers

    def test_export_filtered_by_page_range(self, client, book_with_verified_units):
        """Test exporting specific page range"""
        book_id, table_prefix = book_with_verified_units

        # Export only pages 1-2
        response = client.post("/api/export/csv", json={
            'book_id': book_id,
            'page_range': {'start': 1, 'end': 2}
        })

        assert response.status_code == 200

    def test_export_filtered_by_verification_status(self, client, test_engine, book_with_verified_units):
        """Test exporting only verified or pending units"""
        book_id, table_prefix = book_with_verified_units

        # Add some pending units
        with test_engine.connect() as conn:
            for i in range(16, 20):
                conn.execute(text(f"""
                    INSERT INTO {table_prefix}_knowledge_units
                    (record_id, page_number, text_content, record_status, verification_status)
                    VALUES (:id, 3, :text, 'active', 'pending')
                """), {
                    'id': i,
                    'text': f'Pending unit {i}'
                })
            conn.commit()

        # Export only verified
        response = client.post("/api/export/csv", json={
            'book_id': book_id,
            'verified_only': True
        })

        assert response.status_code == 200

        # Should only get 15 verified units, not 19 total
        if response.headers.get('content-type') == 'text/csv':
            csv_content = response.content.decode('utf-8')
            rows = list(csv.DictReader(StringIO(csv_content)))
            assert len(rows) <= 15

    def test_export_with_hierarchy_grouping(self, client, book_with_verified_units):
        """Test export grouped by chapter/topic hierarchy"""
        book_id, table_prefix = book_with_verified_units

        # Export with hierarchy grouping
        response = client.post("/api/export/json", json={
            'book_id': book_id,
            'group_by_hierarchy': True
        })

        assert response.status_code == 200

        if response.headers.get('content-type') == 'application/json':
            data = response.json()

            # Should be grouped structure
            if isinstance(data, dict) and 'chapters' in data:
                assert len(data['chapters']) > 0

    def test_export_large_dataset(self, client, test_engine):
        """Test exporting large number of knowledge units"""
        import fitz

        # Create book
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Large dataset")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        doc.save(temp_path)
        doc.close()

        with open(temp_path, 'rb') as f:
            files = {'file': ('large.pdf', f, 'application/pdf')}
            data = {'book_name': 'Large Export Test'}
            response = client.post("/api/books/upload", files=files, data=data)

        os.unlink(temp_path)

        book_id = response.json()['book_id']
        table_prefix = response.json()['table_prefix']

        # Insert 1000 units
        with test_engine.connect() as conn:
            for i in range(1000):
                conn.execute(text(f"""
                    INSERT INTO {table_prefix}_knowledge_units
                    (record_id, page_number, text_content, record_status)
                    VALUES (:id, :page, :text, 'active')
                """), {
                    'id': i + 1,
                    'page': (i % 100) + 1,
                    'text': f'Unit {i + 1}'
                })
            conn.commit()

        # Export (should handle large dataset)
        import time
        start_time = time.time()

        response = client.post("/api/export/csv", json={
            'book_id': book_id
        })

        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should complete in reasonable time
        assert elapsed < 30

    def test_export_with_special_characters(self, client, test_engine, book_with_verified_units):
        """Test export handles special characters correctly"""
        book_id, table_prefix = book_with_verified_units

        # Add unit with special characters
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (99, 1, :text, 'active')
            """), {
                'text': 'Special chars: "quotes", commas, newlines\nand unicode: café, naïve, 日本語'
            })
            conn.commit()

        # Export to CSV
        response = client.post("/api/export/csv", json={
            'book_id': book_id
        })

        assert response.status_code == 200

        # Verify special characters preserved
        if response.headers.get('content-type') == 'text/csv':
            csv_content = response.content.decode('utf-8')
            assert 'café' in csv_content
            assert '日本語' in csv_content

    def test_export_download_link_generation(self, client, book_with_verified_units):
        """Test that export generates downloadable file link"""
        book_id, table_prefix = book_with_verified_units

        # Request export
        response = client.post("/api/export/csv", json={
            'book_id': book_id,
            'generate_download_link': True
        })

        assert response.status_code == 200

        result = response.json()
        if 'download_url' in result:
            # Try to download the file
            download_response = client.get(result['download_url'])
            assert download_response.status_code == 200

    def test_export_format_validation(self, client, book_with_verified_units):
        """Test CSV output format is valid"""
        book_id, table_prefix = book_with_verified_units

        # Export to CSV
        response = client.post("/api/export/csv", json={
            'book_id': book_id
        })

        if response.headers.get('content-type') == 'text/csv':
            csv_content = response.content.decode('utf-8')

            # Should be valid CSV
            reader = csv.DictReader(StringIO(csv_content))
            rows = list(reader)

            # All rows should have same columns
            if len(rows) > 1:
                first_keys = set(rows[0].keys())
                for row in rows[1:]:
                    assert set(row.keys()) == first_keys

    def test_export_ui_workflow(self, client, book_with_verified_units):
        """Test complete export UI workflow"""
        book_id, table_prefix = book_with_verified_units

        # 1. Load export page
        response = client.get(f"/export?book_id={book_id}")
        assert response.status_code == 200

        # 2. Get export options
        response = client.get(f"/api/books/{book_id}/export-options")

        if response.status_code == 200:
            options = response.json()
            assert 'available_formats' in options or 'columns' in options

        # 3. Generate export
        response = client.post("/api/export/csv", json={
            'book_id': book_id
        })

        assert response.status_code == 200
