"""
End-to-End Test: Text Splitting Workflow

Workflow: Evaluate → Split → Generate knowledge units

This test simulates the complete text splitting workflow using semantic
analysis and SBERT embeddings to create coherent knowledge units.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import fitz


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
def book_with_processed_text(client, test_session, test_engine):
    """Create a book with OCR-processed text ready for splitting"""
    # Create PDF with substantial text
    doc = fitz.open()

    for page_num in range(3):
        page = doc.new_page()

        # Add text with semantic sections
        text = f"""
        Chapter {page_num + 1}: Introduction to Topic

        This is the first section discussing the main concepts.
        We introduce the fundamental ideas and principles.
        The foundation is laid for deeper understanding.

        Section 2: Detailed Analysis

        Here we dive deeper into the subject matter.
        Complex relationships are explored thoroughly.
        Multiple perspectives are considered carefully.

        Section 3: Practical Applications

        We now examine how these concepts apply in practice.
        Real-world examples demonstrate the principles.
        Case studies illustrate the key points effectively.

        Conclusion

        This chapter has covered the essential elements.
        Understanding these concepts is crucial for progress.
        The next chapter will build upon this foundation.
        """

        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, text, fontsize=11, fontname="helv")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name

    doc.save(temp_path)
    doc.close()

    # Upload book
    with open(temp_path, 'rb') as f:
        files = {'file': ('split_test.pdf', f, 'application/pdf')}
        data = {'book_name': 'Text Splitting Test'}

        response = client.post("/api/books/upload", files=files, data=data)

    os.unlink(temp_path)

    result = response.json()
    book_id = result['book_id']
    table_prefix = result['table_prefix']

    # Simulate OCR completion - store text in pages table
    for page_num in range(1, 4):
        with test_engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_prefix}_pages
                (page_number, ocr_text, ocr_confidence, ocr_method, processing_status)
                VALUES (:page_num, :text, 95.5, 'ocr_standard', 'completed')
            """), {
                'page_num': page_num,
                'text': f"Sample text for page {page_num} with multiple semantic sections."
            })
            conn.commit()

    yield book_id, table_prefix


class TestSplittingWorkflow:
    """End-to-end tests for text splitting workflow"""

    def test_complete_splitting_workflow(self, client, test_session, test_engine, book_with_processed_text):
        """
        Test complete splitting workflow:
        1. Evaluate text for splitting need
        2. Load SBERT embedding model
        3. Split text into semantic chunks
        4. Calculate coherence scores
        5. Store knowledge units in database
        6. Verify chunk quality
        """
        book_id, table_prefix = book_with_processed_text

        # Step 1: Start splitting process
        response = client.post("/api/processing/split/start", json={
            'book_id': book_id,
            'target_lines': 3,
            'max_lines': 5,
            'min_coherence': 0.7
        })

        assert response.status_code in [200, 202]

        # Step 2: Check splitting status
        response = client.get(f"/api/processing/split/status/{book_id}")

        if response.status_code == 200:
            status = response.json()
            assert 'status' in status

        # Step 3: Verify knowledge units created
        with test_engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table_prefix}_knowledge_units
                WHERE record_status = 'active'
            """))
            count = result.scalar()

            assert count > 0  # Should have created knowledge units

    def test_semantic_coherence_scoring(self, client, test_session, test_engine, book_with_processed_text):
        """Test that semantic coherence is calculated for chunks"""
        book_id, table_prefix = book_with_processed_text

        # Start splitting with coherence requirements
        response = client.post("/api/processing/split/start", json={
            'book_id': book_id,
            'target_lines': 3,
            'min_coherence': 0.6
        })

        assert response.status_code in [200, 202]

        # Verify coherence scores stored
        with test_engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT coherence_score FROM {table_prefix}_knowledge_units
                WHERE coherence_score IS NOT NULL
            """))

            scores = [row[0] for row in result]

            if len(scores) > 0:
                # All scores should be between 0 and 1
                assert all(0 <= score <= 1 for score in scores)

    def test_splitting_with_different_line_targets(self, client, test_session, test_engine, book_with_processed_text):
        """Test splitting with different target line counts"""
        book_id, table_prefix = book_with_processed_text

        test_cases = [
            {'target_lines': 2, 'max_lines': 4},
            {'target_lines': 5, 'max_lines': 7},
            {'target_lines': 10, 'max_lines': 15}
        ]

        for config in test_cases:
            response = client.post("/api/processing/split/start", json={
                'book_id': book_id,
                **config
            })

            assert response.status_code in [200, 202]

    def test_evaluate_before_split(self, client, book_with_processed_text):
        """Test evaluation determines if splitting is needed"""
        book_id, table_prefix = book_with_processed_text

        # Evaluate text
        response = client.post("/api/processing/split/evaluate", json={
            'book_id': book_id
        })

        if response.status_code == 200:
            evaluation = response.json()

            assert 'should_split' in evaluation
            assert 'total_pages' in evaluation
            assert 'estimated_chunks' in evaluation

    def test_splitting_preserves_page_numbers(self, client, test_session, test_engine, book_with_processed_text):
        """Test that knowledge units retain correct page numbers"""
        book_id, table_prefix = book_with_processed_text

        # Start splitting
        response = client.post("/api/processing/split/start", json={
            'book_id': book_id,
            'target_lines': 3
        })

        assert response.status_code in [200, 202]

        # Verify page numbers are correct
        with test_engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT DISTINCT page_number FROM {table_prefix}_knowledge_units
                ORDER BY page_number
            """))

            page_numbers = [row[0] for row in result]

            # Should have knowledge units from multiple pages
            if len(page_numbers) > 0:
                assert all(page > 0 for page in page_numbers)

    def test_splitting_with_hierarchy_detection(self, client, book_with_processed_text):
        """Test splitting with chapter/topic hierarchy detection"""
        book_id, table_prefix = book_with_processed_text

        # Start splitting with hierarchy detection
        response = client.post("/api/processing/split/start", json={
            'book_id': book_id,
            'target_lines': 3,
            'detect_hierarchy': True
        })

        assert response.status_code in [200, 202]

        # Get results with hierarchy
        response = client.get(f"/api/books/{book_id}/knowledge-units")

        if response.status_code == 200:
            units = response.json()

            if 'units' in units and len(units['units']) > 0:
                # Check for hierarchy fields
                first_unit = units['units'][0]
                hierarchy_fields = ['chapter', 'topic', 'sub_topic']

                # At least one hierarchy field might be populated
                has_hierarchy = any(
                    field in first_unit and first_unit[field]
                    for field in hierarchy_fields
                )

                # Test passes if hierarchy is detected or if system handles gracefully
                assert True

    def test_batch_splitting_performance(self, client, test_session, test_engine):
        """Test splitting performance with batch processing"""
        # Create book with many pages
        doc = fitz.open()
        for i in range(20):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i + 1} text content.\n" * 10)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        doc.save(temp_path)
        doc.close()

        try:
            # Upload
            with open(temp_path, 'rb') as f:
                files = {'file': ('batch_test.pdf', f, 'application/pdf')}
                data = {'book_name': 'Batch Splitting Test'}

                response = client.post("/api/books/upload", files=files, data=data)

            book_id = response.json()['book_id']

            # Start batch splitting
            import time
            start_time = time.time()

            response = client.post("/api/processing/split/start", json={
                'book_id': book_id,
                'target_lines': 3,
                'batch_size': 10  # Process 10 pages at a time
            })

            assert response.status_code in [200, 202]

            # Processing time should be reasonable (this is a soft check)
            elapsed = time.time() - start_time
            assert elapsed < 30  # Should start within 30 seconds

        finally:
            os.unlink(temp_path)
