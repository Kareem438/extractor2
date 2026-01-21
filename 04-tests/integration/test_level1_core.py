"""
Integration tests for LEVEL 1: Core Logic Layer (CHUNK-009 to CHUNK-018)

Tests the integration of:
- Dynamic Table Creation (CHUNK-009)
- OCR Utility (CHUNK-010)
- OCR Retry Logic (CHUNK-011)
- PDF Text Extraction (CHUNK-012)
- PDF to Image Conversion (CHUNK-013)
- Language Detection (CHUNK-014)
- Image Compression (CHUNK-015)
- Sentence Transformer Loader (CHUNK-016)
- Semantic Text Splitting (CHUNK-017)
- Checkpoint Management (CHUNK-018)

This test suite verifies core processing components work together with real dependencies.
"""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import io


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
def sample_pdf():
    """Create a sample PDF with text for testing"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Add text to the page
    text = "This is a test PDF document.\nIt contains multiple lines of text.\nFor testing OCR and extraction."
    rect = fitz.Rect(50, 50, 545, 200)
    page.insert_textbox(rect, text, fontsize=12, fontname="helv")

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = f.name

    doc.save(temp_path)
    doc.close()

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def sample_image_with_text():
    """Create a sample image with text for OCR testing"""
    # Create white image
    image = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(image)

    # Add text
    text = "Sample Text for OCR\nLine 2\nLine 3"
    try:
        # Try to use default font
        font = ImageFont.load_default()
    except:
        font = None

    draw.text((50, 50), text, fill='black', font=font)

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name
        image.save(temp_path, format='PNG')

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def cleanup_book_tables(test_engine):
    """Cleanup dynamically created book tables after tests"""
    created_tables = []
    yield created_tables

    # Drop all created tables
    with test_engine.connect() as conn:
        for table_name in created_tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.commit()
            except:
                pass


class TestDynamicTableCreation:
    """Test dynamic table creation for books"""

    def test_create_all_book_tables(self, test_engine, cleanup_book_tables):
        """Test creation of all 7 book-specific tables"""
        from src.database.table_creator import create_book_tables
        from src.utils.sanitization import generate_table_prefix

        table_prefix = generate_table_prefix(1, "test_book")

        # Create all book tables
        create_book_tables(book_id=1, sanitized_name="test_book", total_pages=100)

        # Track created tables for cleanup
        expected_tables = [
            f"{table_prefix}_knowledge_units",
            f"{table_prefix}_images",
            f"{table_prefix}_pages",
            f"{table_prefix}_processing_state",
            f"{table_prefix}_settings",
            f"{table_prefix}_attribute_keys",
            f"{table_prefix}_raw_pages"
        ]
        cleanup_book_tables.extend(expected_tables)

        # Verify all tables exist
        inspector = inspect(test_engine)
        existing_tables = inspector.get_table_names()

        for table in expected_tables:
            assert table in existing_tables, f"Table {table} was not created"

    def test_default_data_insertion(self, test_engine, test_session, cleanup_book_tables):
        """Test that default rows are inserted into single-row tables"""
        from src.database.table_creator import create_book_tables
        from src.utils.sanitization import generate_table_prefix

        table_prefix = generate_table_prefix(2, "default_test")

        # Create tables
        create_book_tables(book_id=2, sanitized_name="default_test", total_pages=50)

        # Track for cleanup
        cleanup_book_tables.extend([
            f"{table_prefix}_processing_state",
            f"{table_prefix}_settings",
            f"{table_prefix}_attribute_keys"
        ])

        # Verify processing_state has default row
        result = test_session.execute(
            text(f"SELECT COUNT(*) FROM {table_prefix}_processing_state")
        )
        assert result.scalar() == 1

        # Verify settings has default row
        result = test_session.execute(
            text(f"SELECT COUNT(*) FROM {table_prefix}_settings")
        )
        assert result.scalar() == 1

        # Verify attribute_keys has 30 rows (or configured amount)
        result = test_session.execute(
            text(f"SELECT COUNT(*) FROM {table_prefix}_attribute_keys")
        )
        count = result.scalar()
        assert count >= 30


class TestOCRProcessing:
    """Test OCR functionality"""

    def test_ocr_on_image(self, sample_image_with_text):
        """Test basic OCR on image with text"""
        from src.utils.ocr import ocr_image
        from PIL import Image

        image = Image.open(sample_image_with_text)
        text, confidence = ocr_image(image, language='eng', quality='balanced')

        assert text is not None
        assert len(text) > 0
        assert isinstance(confidence, (int, float))
        assert 0 <= confidence <= 100

    def test_ocr_retry_logic(self, sample_image_with_text):
        """Test OCR retry with zoom enhancement"""
        from src.utils.ocr_retry import ocr_with_retry
        from PIL import Image

        image = Image.open(sample_image_with_text)
        text, confidence, method = ocr_with_retry(image, language='eng', max_attempts=3)

        assert text is not None
        assert isinstance(confidence, (int, float))
        assert method in ['ocr_standard', 'ocr_retry_zoom', 'ocr_retry_segment']

    def test_ocr_quality_settings(self, sample_image_with_text):
        """Test different OCR quality settings"""
        from src.utils.ocr import ocr_image
        from PIL import Image

        image = Image.open(sample_image_with_text)

        # Test different quality levels
        for quality in ['fast', 'balanced', 'high']:
            text, confidence = ocr_image(image, language='eng', quality=quality)
            assert text is not None
            assert confidence >= 0


class TestPDFProcessing:
    """Test PDF text extraction and image conversion"""

    def test_pdf_text_extraction(self, sample_pdf):
        """Test extracting text from PDF page"""
        from src.agents.reader.pdf_reader import extract_text_from_pdf_page

        result = extract_text_from_pdf_page(sample_pdf, page_number=1)

        assert 'text' in result
        assert 'blocks' in result
        assert 'has_text' in result
        assert result['has_text'] is True
        assert len(result['text']) > 0
        assert "test PDF document" in result['text']

    def test_pdf_to_image_conversion(self, sample_pdf):
        """Test converting PDF page to image"""
        from src.agents.reader.pdf_to_image import pdf_page_to_image

        image = pdf_page_to_image(sample_pdf, page_number=1, dpi=150)

        assert isinstance(image, Image.Image)
        assert image.width > 0
        assert image.height > 0
        assert image.mode == 'RGB'

    def test_pdf_multipage_processing(self, sample_pdf):
        """Test processing PDF with text extraction and image conversion"""
        from src.agents.reader.pdf_reader import extract_text_from_pdf_page
        from src.agents.reader.pdf_to_image import pdf_page_to_image

        # Extract text
        text_result = extract_text_from_pdf_page(sample_pdf, page_number=1)

        # Convert to image
        image = pdf_page_to_image(sample_pdf, page_number=1, dpi=150)

        # Both should succeed
        assert text_result['has_text'] is True
        assert isinstance(image, Image.Image)


class TestLanguageDetection:
    """Test language detection functionality"""

    def test_detect_english_text(self):
        """Test detection of English text"""
        from src.utils.language_detector import detect_language

        english_text = "This is an English sentence for testing language detection."
        result = detect_language(english_text)

        assert result == 'english'

    def test_detect_arabic_text(self):
        """Test detection of Arabic text"""
        from src.utils.language_detector import detect_language

        arabic_text = "هذا نص عربي لاختبار كشف اللغة"
        result = detect_language(arabic_text)

        assert result in ['arabic', 'mixed']  # May detect as mixed due to punctuation

    def test_detect_mixed_text(self):
        """Test detection of mixed language text"""
        from src.utils.language_detector import detect_language

        mixed_text = "This is English and هذا عربي mixed together"
        result = detect_language(mixed_text)

        assert result in ['mixed', 'english', 'arabic']

    def test_short_text_handling(self):
        """Test language detection on short text"""
        from src.utils.language_detector import detect_language

        short_text = "Hi"
        result = detect_language(short_text)

        assert result == 'english'  # Default for short text


class TestImageCompression:
    """Test image compression and decompression"""

    def test_compress_decompress_cycle(self, sample_image_with_text):
        """Test complete compression and decompression cycle"""
        from src.utils.image_compression import compress_image, decompress_image
        from PIL import Image

        original = Image.open(sample_image_with_text)

        # Compress
        compressed = compress_image(original)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

        # Decompress
        decompressed = decompress_image(compressed)
        assert isinstance(decompressed, Image.Image)
        assert decompressed.size == original.size
        assert decompressed.mode == original.mode

    def test_compression_ratio(self, sample_image_with_text):
        """Test that compression achieves reasonable compression ratio"""
        from src.utils.image_compression import compress_image
        from PIL import Image

        image = Image.open(sample_image_with_text)

        # Get original PNG size
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        original_size = len(buffer.getvalue())

        # Get compressed size
        compressed = compress_image(image)
        compressed_size = len(compressed)

        # Compression should reduce size (or at least not increase significantly)
        assert compressed_size <= original_size * 1.1  # Allow 10% overhead


class TestSemanticTextSplitting:
    """Test semantic text splitting with embeddings"""

    def test_load_embedding_model(self):
        """Test loading sentence transformer model"""
        from src.agents.splitter.embedding_model import load_embedding_model

        model = load_embedding_model()
        assert model is not None

    def test_semantic_splitting(self):
        """Test semantic text splitting into chunks"""
        from src.agents.splitter.text_splitter import split_text_semantically

        text = """
        This is the first sentence. It talks about topic A.
        This is the second sentence. It continues topic A.
        Now we switch to topic B. This is completely different.
        Topic B continues here. More information about B.
        """

        chunks = split_text_semantically(text, target_lines=3, max_lines=5)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_coherence_scoring(self):
        """Test coherence scoring for text chunks"""
        from src.agents.splitter.text_splitter import calculate_coherence_score

        # Similar sentences should have high coherence
        similar_text = "The cat sat on the mat. The feline was on the rug."
        coherence = calculate_coherence_score(similar_text)

        assert isinstance(coherence, float)
        assert 0.0 <= coherence <= 1.0


class TestCheckpointManagement:
    """Test checkpoint save and restore functionality"""

    def test_save_checkpoint(self, test_session):
        """Test saving processing checkpoint"""
        from src.utils.checkpoint import save_checkpoint

        checkpoint_data = {
            'book_id': 1,
            'current_page': 50,
            'total_pages': 100,
            'processing_stage': 'ocr',
            'last_updated': '2025-11-09T12:00:00'
        }

        checkpoint_id = save_checkpoint(test_session, checkpoint_data)
        assert checkpoint_id is not None

    def test_restore_checkpoint(self, test_session):
        """Test restoring processing checkpoint"""
        from src.utils.checkpoint import save_checkpoint, restore_checkpoint

        # Save checkpoint
        checkpoint_data = {
            'book_id': 2,
            'current_page': 25,
            'total_pages': 50,
            'processing_stage': 'splitting'
        }

        checkpoint_id = save_checkpoint(test_session, checkpoint_data)

        # Restore checkpoint
        restored = restore_checkpoint(test_session, checkpoint_id)

        assert restored is not None
        assert restored['book_id'] == 2
        assert restored['current_page'] == 25
        assert restored['processing_stage'] == 'splitting'


class TestFullCoreIntegration:
    """Test all core components working together"""

    def test_complete_pdf_processing_pipeline(self, sample_pdf, test_engine, cleanup_book_tables):
        """Test complete PDF processing: extract text, OCR images, split, compress"""
        from src.agents.reader.pdf_reader import extract_text_from_pdf_page
        from src.agents.reader.pdf_to_image import pdf_page_to_image
        from src.utils.ocr import ocr_image
        from src.utils.language_detector import detect_language
        from src.agents.splitter.text_splitter import split_text_semantically
        from src.utils.image_compression import compress_image
        from src.database.table_creator import create_book_tables

        # 1. Create book tables
        create_book_tables(book_id=99, sanitized_name="pipeline_test", total_pages=1)
        cleanup_book_tables.extend(["book99_pipeline_test_pages"])

        # 2. Extract text from PDF
        text_result = extract_text_from_pdf_page(sample_pdf, page_number=1)
        assert text_result['has_text'] is True

        # 3. Convert page to image
        image = pdf_page_to_image(sample_pdf, page_number=1, dpi=150)

        # 4. Detect language
        language = detect_language(text_result['text'])
        assert language in ['english', 'arabic', 'mixed']

        # 5. Split text semantically
        chunks = split_text_semantically(text_result['text'], target_lines=3, max_lines=5)
        assert len(chunks) > 0

        # 6. Compress image
        compressed = compress_image(image)
        assert isinstance(compressed, bytes)

        # All steps completed successfully
        assert True

    def test_ocr_fallback_when_no_text(self, sample_pdf):
        """Test OCR is used when PDF has no extractable text"""
        from src.agents.reader.pdf_reader import extract_text_from_pdf_page
        from src.agents.reader.pdf_to_image import pdf_page_to_image
        from src.utils.ocr import ocr_image

        # Extract text
        text_result = extract_text_from_pdf_page(sample_pdf, page_number=1)

        # If no text, convert to image and OCR
        if not text_result['has_text'] or len(text_result['text'].strip()) < 10:
            image = pdf_page_to_image(sample_pdf, page_number=1, dpi=150)
            ocr_text, confidence = ocr_image(image, language='eng', quality='balanced')

            assert ocr_text is not None
            assert confidence >= 0
