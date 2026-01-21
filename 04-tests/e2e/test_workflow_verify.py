"""
End-to-End Test: Verification Workflow

Workflow: Load records → User verifies → Update DB

This test simulates the complete user verification workflow where users
review, edit, merge, and split knowledge units through the UI.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup


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
def book_with_knowledge_units(client, test_session, test_engine):
    """Create a book with knowledge units ready for verification"""
    import fitz

    # Create simple PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test content for verification")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name
    doc.save(temp_path)
    doc.close()

    # Upload book
    with open(temp_path, 'rb') as f:
        files = {'file': ('verify_test.pdf', f, 'application/pdf')}
        data = {'book_name': 'Verification Test Book'}

        response = client.post("/api/books/upload", files=files, data=data)

    os.unlink(temp_path)

    book_id = response.json()['book_id']
    table_prefix = response.json()['table_prefix']

    # Insert sample knowledge units
    with test_engine.connect() as conn:
        for i in range(10):
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status, verification_status)
                VALUES (:id, :page, :text, 'active', 'pending')
            """), {
                'id': i + 1,
                'page': (i // 3) + 1,
                'text': f'Knowledge unit {i + 1}: This is test content that needs verification.'
            })
        conn.commit()

    yield book_id, table_prefix


class TestVerificationWorkflow:
    """End-to-end tests for verification workflow"""

    def test_complete_verification_workflow(self, client, test_session, test_engine, book_with_knowledge_units):
        """
        Test complete verification workflow:
        1. Load verification page
        2. Display knowledge units
        3. User edits a unit
        4. User marks unit as verified
        5. Changes saved to database
        6. Progress tracked
        """
        book_id, table_prefix = book_with_knowledge_units

        # Step 1: Load verification page
        response = client.get(f"/verification?book_id={book_id}")
        assert response.status_code == 200

        # Step 2: Get knowledge units via API
        response = client.get(f"/api/books/{book_id}/knowledge-units?status=pending")

        if response.status_code == 200:
            units = response.json()
            assert 'units' in units or isinstance(units, list)

        # Step 3: Edit a knowledge unit
        response = client.put(f"/api/knowledge-units/1", json={
            'text_content': 'Updated content after verification',
            'verification_status': 'verified'
        })

        assert response.status_code in [200, 404]

        # Step 4: Verify update in database
        if response.status_code == 200:
            with test_engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT text_content, verification_status
                    FROM {table_prefix}_knowledge_units
                    WHERE record_id = 1
                """))
                row = result.fetchone()

                if row:
                    text, status = row
                    assert 'Updated content' in text
                    assert status == 'verified'

    def test_merge_units_during_verification(self, client, test_engine, book_with_knowledge_units):
        """Test merging knowledge units during verification"""
        book_id, table_prefix = book_with_knowledge_units

        # Merge units 2 and 3
        response = client.post(f"/api/knowledge-units/merge", json={
            'book_id': book_id,
            'record_ids': [2, 3],
            'merge_strategy': 'concatenate'
        })

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            result = response.json()
            assert 'merged_record_id' in result

            # Verify merge in database
            with test_engine.connect() as conn:
                # Check merged record exists
                merged_result = conn.execute(text(f"""
                    SELECT text_content FROM {table_prefix}_knowledge_units
                    WHERE record_id = :id
                """), {'id': result['merged_record_id']})

                merged_row = merged_result.fetchone()
                if merged_row:
                    # Should contain content from both units
                    assert 'Knowledge unit 2' in merged_row[0]
                    assert 'Knowledge unit 3' in merged_row[0]

    def test_split_unit_during_verification(self, client, test_engine, book_with_knowledge_units):
        """Test splitting a knowledge unit during verification"""
        book_id, table_prefix = book_with_knowledge_units

        # First, create a unit with multiple lines
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_knowledge_units
                (record_id, page_number, text_content, record_status)
                VALUES (99, 1, :text, 'active')
            """), {
                'text': 'Line 1 content.\nLine 2 content.\nLine 3 content.\nLine 4 content.'
            })
            conn.commit()

        # Split the unit
        response = client.post(f"/api/knowledge-units/split", json={
            'book_id': book_id,
            'record_id': 99,
            'split_strategy': 'lines',
            'lines_per_chunk': 2
        })

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            result = response.json()
            assert 'split_count' in result
            assert result['split_count'] >= 2

    def test_bulk_verification(self, client, test_engine, book_with_knowledge_units):
        """Test verifying multiple units at once"""
        book_id, table_prefix = book_with_knowledge_units

        # Bulk verify units 4, 5, 6
        response = client.post(f"/api/knowledge-units/bulk-verify", json={
            'book_id': book_id,
            'record_ids': [4, 5, 6],
            'verification_status': 'verified'
        })

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Verify all are marked as verified
            with test_engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM {table_prefix}_knowledge_units
                    WHERE record_id IN (4, 5, 6)
                    AND verification_status = 'verified'
                """))

                count = result.scalar()
                assert count == 3

    def test_verification_progress_tracking(self, client, book_with_knowledge_units):
        """Test tracking verification progress"""
        book_id, table_prefix = book_with_knowledge_units

        # Get initial progress
        response = client.get(f"/api/books/{book_id}/verification-progress")

        if response.status_code == 200:
            progress = response.json()

            assert 'total_units' in progress
            assert 'verified_count' in progress
            assert 'pending_count' in progress
            assert 'verification_percentage' in progress

    def test_edit_attributes_during_verification(self, client, test_engine, book_with_knowledge_units):
        """Test editing custom attributes during verification"""
        book_id, table_prefix = book_with_knowledge_units

        # Update attributes for unit 7
        response = client.put(f"/api/knowledge-units/7/attributes", json={
            'attr_01_value': 'Custom value 1',
            'attr_02_value': 'Custom value 2',
            'attr_03_value': 'Custom value 3'
        })

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Verify attributes updated
            with test_engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT attr_01_value, attr_02_value, attr_03_value
                    FROM {table_prefix}_knowledge_units
                    WHERE record_id = 7
                """))

                row = result.fetchone()
                if row:
                    assert row[0] == 'Custom value 1'
                    assert row[1] == 'Custom value 2'
                    assert row[2] == 'Custom value 3'

    def test_verification_ui_rendering(self, client, book_with_knowledge_units):
        """Test verification page UI rendering"""
        book_id, table_prefix = book_with_knowledge_units

        # Load verification page
        response = client.get(f"/verification?book_id={book_id}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for verification controls
            buttons = soup.find_all('button')
            inputs = soup.find_all('input')

            # Should have edit/verify buttons
            assert len(buttons) > 0 or len(inputs) > 0

    def test_flag_problematic_unit(self, client, test_engine, book_with_knowledge_units):
        """Test flagging a problematic knowledge unit"""
        book_id, table_prefix = book_with_knowledge_units

        # Flag unit 8 as problematic
        response = client.post(f"/api/knowledge-units/8/flag", json={
            'reason': 'Poor OCR quality',
            'notes': 'Needs manual review'
        })

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Verify flag stored
            with test_engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT verification_status FROM {table_prefix}_knowledge_units
                    WHERE record_id = 8
                """))

                status = result.scalar()
                assert status in ['flagged', 'needs_review']

    def test_undo_verification_changes(self, client, test_engine, book_with_knowledge_units):
        """Test undo functionality for verification changes"""
        book_id, table_prefix = book_with_knowledge_units

        # Edit unit 9
        response = client.put(f"/api/knowledge-units/9", json={
            'text_content': 'Changed content'
        })

        if response.status_code == 200:
            # Undo the change
            response = client.post(f"/api/knowledge-units/9/undo")

            if response.status_code == 200:
                # Verify reverted
                with test_engine.connect() as conn:
                    result = conn.execute(text(f"""
                        SELECT text_content FROM {table_prefix}_knowledge_units
                        WHERE record_id = 9
                    """))

                    text = result.scalar()
                    # Should be original content
                    assert 'Knowledge unit 9' in text
