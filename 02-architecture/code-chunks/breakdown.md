# Code Chunk Breakdown - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Architect:** Claude (Architect Agent)
**Methodology:** Dependency-Ordered 30-50 LOC Chunks
**Status:** ✅ Breakdown Complete

---

## 📋 Overview

This document breaks down the entire system implementation into **45 code chunks**, each 30-50 lines of code. Chunks are organized by **dependency levels** (Foundation → Core → Services → Presentation → Integration).

**Developer Must:**
1. Implement chunks in dependency order
2. Test each chunk before moving to the next
3. Cannot skip chunks or change order
4. Each chunk is independently testable

**Total Chunks:** 45
**Estimated Total LOC:** ~1,800 lines
**Development Time:** ~120-150 hours (based on chunk estimates)

---

## 🎯 Dependency Levels

```
Level 0: Foundation (no dependencies)           - 8 chunks
Level 1: Core Logic (depends on Level 0)        - 10 chunks
Level 2: Services (depends on Levels 0-1)       - 12 chunks
Level 3: Presentation (depends on Levels 0-2)   - 10 chunks
Level 4: Integration (depends on all)           - 5 chunks
```

---

## 📦 LEVEL 0: FOUNDATION (8 chunks)

### CHUNK-001: Configuration Management
**File:** `src/config.py`
**LOC:** 40-50
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** None

**Purpose:** Centralized configuration loading from environment variables and YAML

**Scope:**
```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Paths
    TESSERACT_PATH: str
    MODEL_CACHE_DIR: str

    # Processing
    CHECKPOINT_FREQUENCY: int = 50
    BATCH_INSERT_SIZE: int = 50

    # Image settings
    IMAGE_MAX_WIDTH: int = 800
    IMAGE_MAX_HEIGHT: int = 600

    class Config:
        env_file = ".env"

settings = Settings()
```

**Tests:**
- Load config from .env file
- Validate required fields
- Test default values

---

### CHUNK-002: Database Connection Setup
**File:** `src/database/connection.py`
**LOC:** 35-45
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** CHUNK-001 (config)

**Purpose:** SQLAlchemy engine and session management with connection pooling

**Scope:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Tests:**
- Connect to PostgreSQL
- Test connection pool
- Test session creation

---

### CHUNK-003: Books Metadata Model
**File:** `src/database/models/books_metadata.py`
**LOC:** 45-50
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** CHUNK-002 (connection)

**Purpose:** SQLAlchemy model for books_metadata table

**Scope:**
```python
from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BooksMetadata(Base):
    __tablename__ = "books_metadata"

    book_id = Column(Integer, primary_key=True)
    book_name = Column(String(255), nullable=False)
    sanitized_name = Column(String(100), nullable=False, unique=True)
    table_prefix = Column(String(100), nullable=False, unique=True)
    upload_date = Column(TIMESTAMP, nullable=False, server_default=func.now())
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    total_pages = Column(Integer, nullable=False)
    processing_status = Column(String(50), nullable=False, default="uploaded")
    # ... (all 22 columns from data-model.md)
```

**Tests:**
- Create table
- Insert/query/update/delete records
- Test constraints and defaults

---

### CHUNK-004: Sanitization Utilities
**File:** `src/utils/sanitization.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Sanitize book names for table creation

**Scope:**
```python
import re

def sanitize_book_name(filename: str) -> str:
    """Sanitize book name for table naming."""
    # Remove extension
    name = filename.rsplit('.', 1)[0]
    # Lowercase
    name = name.lower()
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove special characters
    name = re.sub(r'[^a-z0-9_]', '', name)
    # Limit to 50 characters
    name = name[:50]
    # Ensure not empty
    if not name:
        name = "book"
    return name

def generate_table_prefix(book_id: int, sanitized_name: str) -> str:
    """Generate table prefix: book{N}_{name}"""
    return f"book{book_id}_{sanitized_name}"
```

**Tests:**
- Test various filenames
- Test special characters
- Test length limits
- Test empty/invalid names

---

### CHUNK-005: File Type Detection
**File:** `src/utils/file_detection.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Detect file type using python-magic

**Scope:**
```python
import magic

def detect_file_type(file_path: str) -> str:
    """Detect file type from file content."""
    mime = magic.from_file(file_path, mime=True)

    # Map MIME types to extensions
    mime_to_ext = {
        'application/pdf': 'PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
        'text/plain': 'TXT',
        'text/html': 'HTML',
        'application/epub+zip': 'EPUB',
        'image/png': 'PNG',
        'image/jpeg': 'JPEG'
    }

    return mime_to_ext.get(mime, 'UNKNOWN')
```

**Tests:**
- Test PDF detection
- Test DOCX detection
- Test image detection
- Test unknown files

---

### CHUNK-006: Pydantic Schemas
**File:** `src/database/schemas.py`
**LOC:** 50
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** None

**Purpose:** Pydantic models for API request/response validation

**Scope:**
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class BookUploadRequest(BaseModel):
    book_name: str
    language_setting: str = "auto"
    extraction_sensitivity: str = "balanced"
    image_processing: str = "all"
    ocr_quality: str = "balanced"
    hierarchy_detection: str = "auto"
    partial_processing_enabled: bool = False
    partial_processing_pages: Optional[int] = None
    special_instructions: Optional[str] = ""
    attribute_keys: Dict[str, str] = {}

class BookResponse(BaseModel):
    book_id: int
    book_name: str
    sanitized_name: str
    table_prefix: str
    # ... (all fields)

    class Config:
        from_attributes = True
```

**Tests:**
- Validate request data
- Test default values
- Test optional fields

---

### CHUNK-007: Logging Setup
**File:** `src/utils/logging_config.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** CHUNK-001 (config)

**Purpose:** Centralized logging configuration

**Scope:**
```python
import logging
import sys

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )

    # Set levels for third-party libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    return logging.getLogger(__name__)

logger = setup_logging()
```

**Tests:**
- Test log output
- Test log levels
- Test file logging

---

### CHUNK-008: Error Classes
**File:** `src/utils/exceptions.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Custom exception classes

**Scope:**
```python
class ExtractionError(Exception):
    """Base exception for extraction errors."""
    pass

class OCRError(ExtractionError):
    """OCR-related errors."""
    pass

class PDFError(ExtractionError):
    """PDF processing errors."""
    pass

class DatabaseError(Exception):
    """Database-related errors."""
    pass

class ProcessingError(Exception):
    """General processing errors."""
    pass
```

**Tests:**
- Test exception raising
- Test error messages

---

## 📦 LEVEL 1: CORE LOGIC (10 chunks)

### CHUNK-009: Dynamic Table Creation
**File:** `src/database/table_creator.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3-4 hours)
**Dependencies:** CHUNK-002, CHUNK-003

**Purpose:** Create book-specific tables dynamically

**Scope:**
```python
def create_book_tables(book_id: int, sanitized_name: str, total_pages: int):
    """Create all 7 book-specific tables."""
    table_prefix = generate_table_prefix(book_id, sanitized_name)

    # Create knowledge_units table
    create_knowledge_units_table(table_prefix)

    # Create images table
    create_images_table(table_prefix)

    # Create pages table (similar for all 7 tables)
    # ...

    # Insert default rows for single-row tables
    insert_default_processing_state(table_prefix, total_pages)
    insert_default_settings(table_prefix)
    insert_default_attribute_keys(table_prefix)
```

**Tests:**
- Create tables for test book
- Verify all 7 tables created
- Test indexes created
- Test default data inserted

---

### CHUNK-010: OCR Utility (Tesseract)
**File:** `src/utils/ocr.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-001 (config), CHUNK-008 (exceptions)

**Purpose:** OCR text extraction with retry logic

**Scope:**
```python
import pytesseract
from PIL import Image

def ocr_image(image: Image, language: str = 'eng', quality: str = 'balanced') -> tuple[str, float]:
    """
    Perform OCR on image.
    Returns: (text, confidence_score)
    """
    # Configure Tesseract
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

    # Quality settings
    config_map = {
        'fast': '--psm 3',
        'balanced': '--psm 3 --oem 3',
        'high': '--psm 3 --oem 3 --dpi 300'
    }

    # Perform OCR with confidence
    data = pytesseract.image_to_data(image, lang=language, config=config_map[quality], output_type=Output.DICT)

    # Calculate average confidence
    confidences = [int(conf) for conf in data['conf'] if conf != '-1']
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Extract text
    text = pytesseract.image_to_string(image, lang=language, config=config_map[quality])

    return text.strip(), avg_confidence
```

**Tests:**
- Test OCR on sample images
- Test confidence scoring
- Test language detection
- Test quality settings

---

### CHUNK-011: OCR Retry Logic
**File:** `src/utils/ocr_retry.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-010 (OCR)

**Purpose:** 3-attempt OCR retry with zoom enhancement

**Scope:**
```python
def ocr_with_retry(image: Image, language: str = 'eng', max_attempts: int = 3) -> tuple[str, float, str]:
    """
    OCR with 3-attempt retry logic.
    Returns: (text, confidence, method)
    """
    # Attempt 1: Standard
    text, confidence = ocr_image(image, language, 'balanced')
    if confidence >= 70:
        return text, confidence, 'ocr_standard'

    logger.warning(f"OCR attempt 1 failed (confidence: {confidence}%), retrying...")

    # Attempt 2: Zoom 200% + High Quality
    zoomed = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    text, confidence = ocr_image(zoomed, language, 'high')
    if confidence >= 60:
        return text, confidence, 'ocr_retry_zoom'

    logger.warning(f"OCR attempt 2 failed (confidence: {confidence}%), final attempt...")

    # Attempt 3: Segment regions + High Quality
    # (Implementation of region segmentation)
    # ...

    return text, confidence, 'ocr_retry_segment'
```

**Tests:**
- Test successful attempt 1
- Test retry on low confidence
- Test zoom enhancement
- Test region segmentation

---

### CHUNK-012: PDF Text Extraction (PyMuPDF)
**File:** `src/agents/reader/pdf_reader.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-008 (exceptions)

**Purpose:** Extract text from PDF using PyMuPDF

**Scope:**
```python
import fitz  # PyMuPDF

def extract_text_from_pdf_page(pdf_path: str, page_number: int) -> dict:
    """
    Extract text from PDF page.
    Returns: {
        'text': str,
        'blocks': list of text blocks with coordinates,
        'has_text': bool
    }
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]  # 0-indexed

    # Extract text blocks with coordinates
    blocks = page.get_text("dict")["blocks"]

    text_blocks = []
    for block in blocks:
        if block['type'] == 0:  # Text block
            for line in block['lines']:
                for span in line['spans']:
                    text_blocks.append({
                        'text': span['text'],
                        'bbox': span['bbox'],  # (x0, y0, x1, y1)
                        'font': span['font'],
                        'size': span['size']
                    })

    full_text = page.get_text()

    return {
        'text': full_text,
        'blocks': text_blocks,
        'has_text': len(full_text.strip()) > 0
    }
```

**Tests:**
- Test native text extraction
- Test scanned PDF (no text)
- Test coordinate extraction
- Test multi-column layouts

---

### CHUNK-013: PDF to Image Conversion
**File:** `src/agents/reader/pdf_to_image.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** None

**Purpose:** Convert PDF pages to PNG images

**Scope:**
```python
import fitz

def pdf_page_to_image(pdf_path: str, page_number: int, dpi: int = 150) -> Image:
    """Convert PDF page to PIL Image."""
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]

    # Render page to pixmap
    zoom = dpi / 72  # PDF is 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Convert to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    return img
```

**Tests:**
- Test PDF to image conversion
- Test different DPI settings
- Test image dimensions

---

### CHUNK-014: Language Detection
**File:** `src/utils/language_detector.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** None

**Purpose:** Detect text language (English/Arabic/Mixed)

**Scope:**
```python
from langdetect import detect, LangDetectException

def detect_language(text: str) -> str:
    """
    Detect language of text.
    Returns: 'english', 'arabic', or 'mixed'
    """
    if not text or len(text.strip()) < 10:
        return 'english'  # Default

    try:
        lang = detect(text)

        if lang == 'en':
            return 'english'
        elif lang == 'ar':
            return 'arabic'
        else:
            # Check if mixed (contains both Latin and Arabic scripts)
            has_latin = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in text)
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)

            if has_latin and has_arabic:
                return 'mixed'
            elif has_arabic:
                return 'arabic'
            else:
                return 'english'
    except LangDetectException:
        return 'english'
```

**Tests:**
- Test English text
- Test Arabic text
- Test mixed text
- Test short text

---

### CHUNK-015: Image Compression (LZ4)
**File:** `src/utils/image_compression.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Compress/decompress images with LZ4

**Scope:**
```python
import lz4.frame
from io import BytesIO

def compress_image(image: Image) -> bytes:
    """Compress PIL Image to LZ4-compressed bytes."""
    # Convert to PNG bytes
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    # Compress with LZ4
    compressed = lz4.frame.compress(png_bytes)

    return compressed

def decompress_image(compressed_bytes: bytes) -> Image:
    """Decompress LZ4 bytes to PIL Image."""
    # Decompress
    png_bytes = lz4.frame.decompress(compressed_bytes)

    # Load as PIL Image
    buffer = BytesIO(png_bytes)
    image = Image.open(buffer)

    return image
```

**Tests:**
- Test compression/decompression
- Test compression ratio
- Test image quality preservation

---

### CHUNK-016: Sentence Transformer Loader
**File:** `src/agents/splitter/embedding_model.py`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** CHUNK-001 (config)

**Purpose:** Load and cache SBERT model

**Scope:**
```python
from sentence_transformers import SentenceTransformer

class EmbeddingModel:
    _model = None

    @classmethod
    def get_model(cls):
        """Lazy-load SBERT model (singleton)."""
        if cls._model is None:
            logger.info("Loading SBERT model...")
            cls._model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2',
                cache_folder=settings.MODEL_CACHE_DIR
            )
            logger.info("SBERT model loaded.")
        return cls._model

    @classmethod
    def encode(cls, texts: list[str]) -> np.ndarray:
        """Generate embeddings for texts."""
        model = cls.get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings
```

**Tests:**
- Test model loading
- Test embedding generation
- Test singleton pattern

---

### CHUNK-017: Text Chunking Algorithm
**File:** `src/agents/splitter/text_chunker.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-016 (embedding model)

**Purpose:** Split text into 3-5 line semantic chunks

**Scope:**
```python
def split_text_semantic(text: str) -> list[dict]:
    """
    Split text into semantic chunks (3-5 lines each).
    Returns list of {'text': str, 'confidence': float, 'line_count': int}
    """
    # Split into paragraphs
    paragraphs = text.split('\n\n')

    chunks = []
    for para in paragraphs:
        # Split into sentences
        sentences = split_sentences(para)

        # Generate embeddings
        if len(sentences) > 1:
            embeddings = EmbeddingModel.encode(sentences)

            # Find low-similarity boundaries
            split_points = find_split_points(embeddings, threshold=0.6)
        else:
            split_points = []

        # Create chunks
        current_chunk = []
        for i, sent in enumerate(sentences):
            current_chunk.append(sent)

            # Check if split point or chunk size reached
            if i in split_points or len(current_chunk) >= 5:
                chunk_text = ' '.join(current_chunk)
                line_count = chunk_text.count('\n') + 1

                if 3 <= line_count <= 5:
                    chunks.append({
                        'text': chunk_text,
                        'confidence': calculate_confidence(chunk_text),
                        'line_count': line_count
                    })
                current_chunk = []

        # Add remaining
        if current_chunk:
            # ... similar logic

    return chunks
```

**Tests:**
- Test paragraph splitting
- Test semantic boundary detection
- Test 3-5 line constraint
- Test confidence scoring

---

### CHUNK-018: BLIP Image Captioning
**File:** `src/agents/image_reader/image_captioner.py`
**LOC:** 40-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-001 (config)

**Purpose:** Generate AI descriptions for images using BLIP

**Scope:**
```python
from transformers import BlipProcessor, BlipForConditionalGeneration

class ImageCaptioner:
    _processor = None
    _model = None

    @classmethod
    def get_model(cls):
        """Lazy-load BLIP model (singleton)."""
        if cls._processor is None:
            logger.info("Loading BLIP model...")
            cls._processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                cache_dir=settings.MODEL_CACHE_DIR
            )
            cls._model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                cache_dir=settings.MODEL_CACHE_DIR
            )
            logger.info("BLIP model loaded.")
        return cls._processor, cls._model

    @classmethod
    def generate_caption(cls, image: Image) -> tuple[str, float]:
        """Generate caption and confidence."""
        processor, model = cls.get_model()

        inputs = processor(image, return_tensors="pt")
        outputs = model.generate(**inputs)
        caption = processor.decode(outputs[0], skip_special_tokens=True)

        # Calculate confidence (based on output probabilities)
        confidence = 85.0  # Simplified for now

        return caption, confidence
```

**Tests:**
- Test model loading
- Test caption generation
- Test various image types

---

## 📦 LEVEL 2: SERVICES (12 chunks)

### CHUNK-019: Reader Agent - Main Logic
**File:** `src/agents/reader/reader_agent.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3-4 hours)
**Dependencies:** CHUNK-010, CHUNK-011, CHUNK-012, CHUNK-013, CHUNK-014

**Purpose:** Orchestrate page reading (native text + OCR fallback)

**Scope:**
```python
class ReaderAgent:
    def read_page(self, pdf_path: str, page_number: int, language_setting: str, ocr_quality: str) -> dict:
        """
        Read page and extract text.
        Returns: {
            'text': str,
            'blocks': list of text blocks,
            'language': str,
            'confidence': float,
            'extraction_method': str
        }
        """
        # Try native text extraction first
        result = extract_text_from_pdf_page(pdf_path, page_number)

        if result['has_text']:
            # Native text available
            lang = detect_language(result['text'])
            return {
                'text': result['text'],
                'blocks': result['blocks'],
                'language': lang,
                'confidence': 100.0,
                'extraction_method': 'native_text'
            }
        else:
            # Fallback to OCR
            logger.info(f"No native text on page {page_number}, using OCR...")
            page_image = pdf_page_to_image(pdf_path, page_number)

            # Determine OCR language
            ocr_lang = 'eng' if language_setting == 'english' else 'ara'

            # OCR with retry
            text, confidence, method = ocr_with_retry(page_image, ocr_lang)
            lang = detect_language(text)

            return {
                'text': text,
                'blocks': [],  # OCR doesn't provide block coordinates (simplified)
                'language': lang,
                'confidence': confidence,
                'extraction_method': method
            }
```

**Tests:**
- Test native text extraction
- Test OCR fallback
- Test language detection
- Test confidence scores

---

### CHUNK-020: Splitter Agent - Main Logic
**File:** `src/agents/splitter/splitter_agent.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-017 (text chunker)

**Purpose:** Split text into knowledge units

**Scope:**
```python
class SplitterAgent:
    def split_text(self, text: str, page_number: int) -> list[dict]:
        """
        Split text into knowledge units.
        Returns list of knowledge unit dicts.
        """
        if not text or len(text.strip()) < 10:
            return []

        # Use semantic chunker
        chunks = split_text_semantic(text)

        # Convert to knowledge unit format
        knowledge_units = []
        for chunk in chunks:
            ku = {
                'text_content': chunk['text'],
                'text_length': len(chunk['text']),
                'line_count': chunk['line_count'],
                'page_number': page_number,
                'confidence_score': chunk['confidence'],
                'language': detect_language(chunk['text']),
                # position fields will be added by marker agent
            }
            knowledge_units.append(ku)

        return knowledge_units
```

**Tests:**
- Test text splitting
- Test knowledge unit format
- Test empty text handling

---

### CHUNK-021: Marker Agent - Rectangle Drawing
**File:** `src/agents/marker/marker_agent.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-013 (PDF to image)

**Purpose:** Draw green/orange rectangles on page images

**Scope:**
```python
import cv2
import numpy as np

class MarkerAgent:
    def create_markers(self, page_image: Image, knowledge_units: list, images: list) -> tuple[Image, dict]:
        """
        Draw markers on page image.
        Returns: (marked_image, rectangle_data)
        """
        # Convert PIL to OpenCV format
        img_array = np.array(page_image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        green_rects = []
        orange_rects = []

        # Draw green rectangles for text
        for ku in knowledge_units:
            if 'position_x' in ku and ku['position_x']:
                x1, y1 = ku['position_x'], ku['position_y']
                x2 = x1 + ku['position_width']
                y2 = y1 + ku['position_height']

                cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green
                green_rects.append({
                    'x': x1, 'y': y1,
                    'width': ku['position_width'],
                    'height': ku['position_height'],
                    'text_id': ku['id']
                })

        # Draw orange rectangles for image-linked text
        # (similar logic)

        # Convert back to PIL
        marked_image = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

        return marked_image, {
            'green_rectangles': green_rects,
            'orange_rectangles': orange_rects
        }
```

**Tests:**
- Test rectangle drawing
- Test color accuracy
- Test coordinate handling

---

### CHUNK-022: Image-Reader Agent - Image Extraction
**File:** `src/agents/image_reader/image_extractor.py`
**LOC:** 40-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-018 (BLIP captioner)

**Purpose:** Extract images from PDF and generate descriptions

**Scope:**
```python
class ImageReaderAgent:
    def extract_images(self, pdf_path: str, page_number: int) -> list[dict]:
        """
        Extract all images from page.
        Returns list of image dicts with AI descriptions.
        """
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]

        images = []
        image_list = page.get_images()

        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # Load as PIL Image
            image = Image.open(BytesIO(image_bytes))

            # Generate AI description
            description, confidence = ImageCaptioner.generate_caption(image)

            # Detect image type (simplified)
            image_type = self._classify_image_type(image)

            images.append({
                'image_id': f"IMG-{page_number:03d}-{img_index:02d}",
                'page_number': page_number,
                'image_data': image,
                'ai_description': description,
                'confidence_score': confidence,
                'image_type': image_type,
                'original_width': image.width,
                'original_height': image.height
            })

        return images
```

**Tests:**
- Test image extraction
- Test caption generation
- Test multiple images per page

---

### CHUNK-023: Agent Orchestrator - Sequential Execution
**File:** `src/agents/orchestrator.py`
**LOC:** 50
**Complexity:** Complex
**Effort:** High (4-5 hours)
**Dependencies:** CHUNK-019, CHUNK-020, CHUNK-021, CHUNK-022

**Purpose:** Coordinate all agents for page-by-page processing

**Scope:**
```python
class AgentOrchestrator:
    def __init__(self, book_id: int, pdf_path: str, settings: dict):
        self.book_id = book_id
        self.pdf_path = pdf_path
        self.settings = settings
        self.reader = ReaderAgent()
        self.splitter = SplitterAgent()
        self.marker = MarkerAgent()
        self.image_reader = ImageReaderAgent()

    def process_page(self, page_number: int) -> dict:
        """Process single page through all agents."""
        logger.info(f"Processing page {page_number}...")

        # 1. Reader Agent
        text_data = self.reader.read_page(
            self.pdf_path, page_number,
            self.settings['language_setting'],
            self.settings['ocr_quality']
        )

        # 2. Splitter Agent
        knowledge_units = self.splitter.split_text(text_data['text'], page_number)

        # 3. Image-Reader Agent
        images = self.image_reader.extract_images(self.pdf_path, page_number)

        # 4. Marker Agent
        page_image = pdf_page_to_image(self.pdf_path, page_number)
        marked_image, rect_data = self.marker.create_markers(
            page_image, knowledge_units, images
        )

        return {
            'page_number': page_number,
            'knowledge_units': knowledge_units,
            'images': images,
            'page_image': page_image,
            'marked_image': marked_image,
            'rectangle_data': rect_data
        }
```

**Tests:**
- Test page processing
- Test agent coordination
- Test data flow

---

### CHUNK-024: Database Service - Knowledge Units CRUD
**File:** `src/database/services/knowledge_unit_service.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-002 (connection), CHUNK-009 (table creation)

**Purpose:** CRUD operations for knowledge units

**Scope:**
```python
class KnowledgeUnitService:
    def insert_knowledge_units(self, book_id: int, knowledge_units: list[dict]):
        """Batch insert knowledge units."""
        db = SessionLocal()
        try:
            table_name = get_table_name(book_id, 'knowledge_units')

            # Bulk insert
            db.execute(
                text(f"INSERT INTO {table_name} (text_content, text_length, line_count, ...) VALUES (:text, :length, :lines, ...)"),
                knowledge_units
            )
            db.commit()
        finally:
            db.close()

    def get_knowledge_units(self, book_id: int, page: int, limit: int, verified: bool = None):
        """Get paginated knowledge units."""
        # Implementation
        pass

    def update_knowledge_unit(self, book_id: int, record_id: int, updates: dict):
        """Update single knowledge unit."""
        # Implementation
        pass

    def merge_knowledge_units(self, book_id: int, keep_id: int, delete_id: int):
        """Merge two knowledge units."""
        # Implementation
        pass
```

**Tests:**
- Test batch insert
- Test query with pagination
- Test update
- Test merge

---

### CHUNK-025: Database Service - Images CRUD
**File:** `src/database/services/image_service.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-002, CHUNK-009, CHUNK-015 (compression)

**Purpose:** CRUD operations for images with compression

**Scope:**
```python
class ImageService:
    def insert_images(self, book_id: int, images: list[dict]):
        """Insert images with LZ4 compression."""
        db = SessionLocal()
        try:
            for img in images:
                # Compress image data
                compressed = compress_image(img['image_data'])

                # Generate thumbnail
                thumbnail = img['image_data'].copy()
                thumbnail.thumbnail((200, 200))
                compressed_thumb = compress_image(thumbnail)

                # Insert
                table_name = get_table_name(book_id, 'images')
                db.execute(
                    text(f"INSERT INTO {table_name} (...) VALUES (...)"),
                    {
                        'image_id': img['image_id'],
                        'image_data': compressed,
                        'thumbnail_data': compressed_thumb,
                        # ... other fields
                    }
                )
            db.commit()
        finally:
            db.close()

    def get_image(self, book_id: int, image_id: int) -> Image:
        """Get and decompress image."""
        # Implementation with decompression
        pass
```

**Tests:**
- Test image insert with compression
- Test image retrieval with decompression
- Test thumbnail generation

---

### CHUNK-026: Database Service - Pages CRUD
**File:** `src/database/services/page_service.py`
**LOC:** 40-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-002, CHUNK-009, CHUNK-015

**Purpose:** Store page images (original + marked)

**Scope:**
```python
class PageService:
    def insert_page(self, book_id: int, page_data: dict):
        """Insert page with original and marked images."""
        db = SessionLocal()
        try:
            # Compress both images
            original_compressed = compress_image(page_data['page_image'])
            marked_compressed = compress_image(page_data['marked_image'])

            table_name = get_table_name(book_id, 'pages')
            db.execute(
                text(f"INSERT INTO {table_name} (...) VALUES (...)"),
                {
                    'page_number': page_data['page_number'],
                    'original_image_data': original_compressed,
                    'marked_image_data': marked_compressed,
                    'green_rectangles': json.dumps(page_data['rectangle_data']['green_rectangles']),
                    'orange_rectangles': json.dumps(page_data['rectangle_data']['orange_rectangles'])
                }
            )
            db.commit()
        finally:
            db.close()
```

**Tests:**
- Test page insert
- Test rectangle data JSON storage
- Test compression

---

### CHUNK-027: Database Service - Processing State
**File:** `src/database/services/processing_state_service.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-002, CHUNK-009

**Purpose:** Update processing state continuously

**Scope:**
```python
class ProcessingStateService:
    def update_state(self, book_id: int, updates: dict):
        """Update processing state (single-row table)."""
        db = SessionLocal()
        try:
            table_name = get_table_name(book_id, 'processing_state')

            # Calculate progress percentage
            if 'current_page' in updates:
                progress = (updates['current_page'] / updates['total_pages']) * 100
                updates['progress_percentage'] = round(progress, 2)

            # Update single row (id=1)
            set_clause = ', '.join([f"{k} = :{k}" for k in updates.keys()])
            db.execute(
                text(f"UPDATE {table_name} SET {set_clause}, last_updated_at = NOW() WHERE id = 1"),
                updates
            )
            db.commit()
        finally:
            db.close()

    def get_state(self, book_id: int) -> dict:
        """Get current processing state."""
        # Implementation
        pass

    def save_checkpoint(self, book_id: int, page_number: int):
        """Save checkpoint."""
        self.update_state(book_id, {
            'last_checkpoint_page': page_number,
            'last_checkpoint_at': datetime.now()
        })
```

**Tests:**
- Test state updates
- Test checkpoint saving
- Test progress calculation

---

### CHUNK-028: Database Service - Book Settings
**File:** `src/database/services/book_settings_service.py`
**LOC:** 35-40
**Complexity:** Simple
**Effort:** Low (1-2 hours)
**Dependencies:** CHUNK-002, CHUNK-009

**Purpose:** Get/update book settings

**Scope:**
```python
class BookSettingsService:
    def get_settings(self, book_id: int) -> dict:
        """Get book settings (single-row table)."""
        db = SessionLocal()
        try:
            table_name = get_table_name(book_id, 'settings')
            result = db.execute(
                text(f"SELECT * FROM {table_name} WHERE id = 1")
            ).fetchone()
            return dict(result) if result else {}
        finally:
            db.close()

    def update_settings(self, book_id: int, updates: dict):
        """Update book settings."""
        # Implementation
        pass
```

**Tests:**
- Test settings retrieval
- Test settings update

---

### CHUNK-029: Database Service - Attribute Keys
**File:** `src/database/services/attribute_key_service.py`
**LOC:** 40-45
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** CHUNK-002, CHUNK-009

**Purpose:** Manage attribute key names (30 attributes)

**Scope:**
```python
class AttributeKeyService:
    def get_attribute_keys(self, book_id: int) -> dict:
        """Get all 30 attribute key names."""
        db = SessionLocal()
        try:
            table_name = get_table_name(book_id, 'attribute_keys')
            results = db.execute(
                text(f"SELECT attr_number, key_name FROM {table_name} ORDER BY attr_number")
            ).fetchall()

            # Convert to dict: {1: "related_image", 2: "Difficulty Level", ...}
            return {row['attr_number']: row['key_name'] for row in results}
        finally:
            db.close()

    def update_attribute_keys(self, book_id: int, key_updates: dict):
        """Update attribute key names (cannot edit attr1)."""
        db = SessionLocal()
        try:
            if 1 in key_updates:
                raise ValueError("Cannot edit attribute 1 (system-defined)")

            table_name = get_table_name(book_id, 'attribute_keys')
            for attr_num, key_name in key_updates.items():
                db.execute(
                    text(f"UPDATE {table_name} SET key_name = :key_name WHERE attr_number = :num"),
                    {'key_name': key_name, 'num': attr_num}
                )
            db.commit()
        finally:
            db.close()
```

**Tests:**
- Test key retrieval
- Test key updates
- Test attr1 protection

---

### CHUNK-030: Background Processing Task
**File:** `src/api/background_processor.py`
**LOC:** 50
**Complexity:** Complex
**Effort:** High (4-5 hours)
**Dependencies:** CHUNK-023 (orchestrator), CHUNK-024-029 (DB services)

**Purpose:** Background task for processing books

**Scope:**
```python
async def process_book_background(book_id: int, pdf_path: str):
    """
    Background task for processing book.
    Runs in ProcessPoolExecutor to avoid blocking.
    """
    try:
        # Get book metadata and settings
        book = BooksMetadata.get_by_id(book_id)
        settings = BookSettingsService().get_settings(book_id)

        # Initialize orchestrator
        orchestrator = AgentOrchestrator(book_id, pdf_path, settings)

        # Get total pages
        total_pages = book.total_pages
        if settings['partial_processing_enabled']:
            total_pages = min(total_pages, settings['partial_processing_pages'])

        # Update status to processing
        BooksMetadata.update_status(book_id, 'processing')

        # Process pages
        for page_num in range(1, total_pages + 1):
            # Check for pause signal
            state = ProcessingStateService().get_state(book_id)
            if state['status'] == 'paused':
                logger.info(f"Processing paused at page {page_num}")
                break

            # Process page
            page_data = orchestrator.process_page(page_num)

            # Save to database
            KnowledgeUnitService().insert_knowledge_units(book_id, page_data['knowledge_units'])
            ImageService().insert_images(book_id, page_data['images'])
            PageService().insert_page(book_id, page_data)

            # Update state
            ProcessingStateService().update_state(book_id, {
                'current_page': page_num,
                'pages_processed': page_num,
                'knowledge_units_extracted': state['knowledge_units_extracted'] + len(page_data['knowledge_units']),
                'images_extracted': state['images_extracted'] + len(page_data['images'])
            })

            # Checkpoint every N pages
            if page_num % settings['checkpoint_frequency'] == 0:
                ProcessingStateService().save_checkpoint(book_id, page_num)
                logger.info(f"Checkpoint saved at page {page_num}")

        # Mark as completed
        BooksMetadata.update_status(book_id, 'completed')
        logger.info(f"Book {book_id} processing completed!")

    except Exception as e:
        logger.error(f"Processing error: {e}")
        BooksMetadata.update_status(book_id, 'error')
        ProcessingStateService().update_state(book_id, {
            'status': 'error',
            'last_error_message': str(e),
            'last_error_at': datetime.now()
        })
```

**Tests:**
- Test full processing flow
- Test pause signal handling
- Test checkpoint logic
- Test error handling

---

## 📦 LEVEL 3: PRESENTATION (10 chunks)

### CHUNK-031: FastAPI Application Setup
**File:** `src/main.py`
**LOC:** 40-50
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** CHUNK-001 (config), CHUNK-007 (logging)

**Purpose:** Initialize FastAPI app with middleware

**Scope:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Knowledge Extraction System",
    version="1.0.0",
    description="Extract and verify knowledge from documents"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

# Setup logging
setup_logging()

# Include routers
from src.api import routes
app.include_router(routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
```

**Tests:**
- Test app startup
- Test CORS
- Test static file serving

---

### CHUNK-032: API Routes - Upload
**File:** `src/api/routes/upload.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-003, CHUNK-004, CHUNK-005, CHUNK-006, CHUNK-009

**Purpose:** File upload endpoint

**Scope:**
```python
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/api", tags=["upload"])

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    book_name: str = Form(...),
    language_setting: str = Form("auto"),
    # ... other settings
):
    """Upload file and create book metadata."""
    # Validate file size
    if file.size > 500 * 1024 * 1024:  # 500MB
        raise HTTPException(status_code=413, detail="File too large")

    # Save file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Detect file type
    file_type = detect_file_type(temp_path)

    # Get page count (PDF-specific for now)
    if file_type == 'PDF':
        doc = fitz.open(temp_path)
        total_pages = len(doc)
        doc.close()
    else:
        total_pages = 1  # Simplified

    # Get next book_id
    db = SessionLocal()
    max_id = db.execute(text("SELECT MAX(book_id) FROM books_metadata")).scalar()
    book_id = (max_id or 0) + 1

    # Sanitize name
    sanitized = sanitize_book_name(book_name)
    table_prefix = generate_table_prefix(book_id, sanitized)

    # Create metadata record
    book = BooksMetadata(
        book_id=book_id,
        book_name=book_name,
        sanitized_name=sanitized,
        table_prefix=table_prefix,
        file_type=file_type,
        file_size_bytes=file.size,
        total_pages=total_pages
    )
    db.add(book)
    db.commit()

    # Create book-specific tables
    create_book_tables(book_id, sanitized, total_pages)

    # Save settings
    # Save attribute keys
    # ...

    return {
        "book_id": book_id,
        "message": "Book uploaded successfully"
    }
```

**Tests:**
- Test file upload
- Test table creation
- Test validation

---

### CHUNK-033: API Routes - Processing Control
**File:** `src/api/routes/processing.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-030 (background processor)

**Purpose:** Start/pause/resume processing

**Scope:**
```python
from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter(prefix="/api", tags=["processing"])

@router.post("/start-processing")
async def start_processing(
    book_id: int,
    background_tasks: BackgroundTasks
):
    """Start processing a book in background."""
    # Get book
    book = BooksMetadata.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.processing_status == 'processing':
        raise HTTPException(status_code=409, detail="Already processing")

    # Get file path
    pdf_path = f"/uploads/{book.book_name}"

    # Start background task
    background_tasks.add_task(process_book_background, book_id, pdf_path)

    return {
        "book_id": book_id,
        "processing_status": "processing",
        "message": "Processing started"
    }

@router.post("/pause/{book_id}")
async def pause_processing(book_id: int):
    """Pause processing."""
    ProcessingStateService().update_state(book_id, {'status': 'paused'})
    return {"message": "Processing paused"}

@router.post("/resume/{book_id}")
async def resume_processing(book_id: int, background_tasks: BackgroundTasks):
    """Resume processing."""
    # Similar to start_processing
    pass
```

**Tests:**
- Test start processing
- Test pause
- Test resume

---

### CHUNK-034: API Routes - Books Management
**File:** `src/api/routes/books.py`
**LOC:** 45-50
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** CHUNK-003, CHUNK-006

**Purpose:** List/get/delete books

**Scope:**
```python
@router.get("/books")
async def list_books(
    status: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List books with filters."""
    db = SessionLocal()
    query = db.query(BooksMetadata)

    if status:
        query = query.filter(BooksMetadata.processing_status == status)
    if language:
        query = query.filter(BooksMetadata.language == language)

    total = query.count()
    books = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "books": [BookResponse.from_orm(b) for b in books]
    }

@router.get("/book/{book_id}")
async def get_book(book_id: int):
    """Get book details."""
    book = BooksMetadata.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookResponse.from_orm(book)

@router.delete("/book/{book_id}")
async def delete_book(book_id: int):
    """Delete book and all tables."""
    # Implementation
    pass
```

**Tests:**
- Test list with filters
- Test get single book
- Test delete

---

### CHUNK-035: API Routes - Knowledge Units
**File:** `src/api/routes/knowledge_units.py`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-024 (KU service), CHUNK-006

**Purpose:** CRUD for knowledge units

**Scope:**
```python
@router.get("/records/{book_id}")
async def get_records(
    book_id: int,
    page: int = 1,
    limit: int = 20,
    verified: Optional[bool] = None,
    page_number: Optional[int] = None,
    confidence_min: Optional[float] = None
):
    """Get paginated knowledge units."""
    records = KnowledgeUnitService().get_knowledge_units(
        book_id, page, limit, verified, page_number, confidence_min
    )
    return records

@router.get("/record/{record_id}")
async def get_record(record_id: int, book_id: int):
    """Get single record with context."""
    # Implementation with previous/next
    pass

@router.put("/record/{record_id}")
async def update_record(record_id: int, book_id: int, updates: KnowledgeUnitUpdate):
    """Update knowledge unit."""
    KnowledgeUnitService().update_knowledge_unit(book_id, record_id, updates.dict())
    return {"message": "Record updated"}

@router.post("/merge")
async def merge_records(book_id: int, keep_record_id: int, delete_record_id: int):
    """Merge two records."""
    KnowledgeUnitService().merge_knowledge_units(book_id, keep_record_id, delete_record_id)
    return {"message": "Records merged"}
```

**Tests:**
- Test pagination
- Test filters
- Test update
- Test merge

---

### CHUNK-036: API Routes - Images
**File:** `src/api/routes/images.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (2-3 hours)
**Dependencies:** CHUNK-025 (image service)

**Purpose:** Image retrieval endpoints

**Scope:**
```python
from fastapi.responses import Response

@router.get("/images/{book_id}")
async def get_images(
    book_id: int,
    page_number: Optional[int] = None,
    image_type: Optional[str] = None,
    limit: int = 20
):
    """Get images for book."""
    images = ImageService().get_images(book_id, page_number, image_type, limit)
    return images

@router.get("/image/{book_id}/{image_id}")
async def get_image_details(book_id: int, image_id: int):
    """Get full image details with linked texts."""
    # Implementation
    pass

@router.get("/image-data/{book_id}/{image_id}")
async def get_image_data(book_id: int, image_id: int):
    """Get raw image binary."""
    image = ImageService().get_image(book_id, image_id)

    # Convert to PNG bytes
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)

    return Response(content=buffer.read(), media_type="image/png")

@router.get("/image-thumbnail/{book_id}/{image_id}")
async def get_thumbnail(book_id: int, image_id: int):
    """Get image thumbnail."""
    # Similar to get_image_data but with thumbnail
    pass
```

**Tests:**
- Test image list
- Test binary image retrieval
- Test thumbnail

---

### CHUNK-037: API Routes - Pages
**File:** `src/api/routes/pages.py`
**LOC:** 40-45
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** CHUNK-026 (page service)

**Purpose:** Page image endpoints

**Scope:**
```python
@router.get("/page-image/{book_id}/{page_number}")
async def get_page_image(book_id: int, page_number: int):
    """Get original page image."""
    page_image = PageService().get_page_image(book_id, page_number, marked=False)

    buffer = BytesIO()
    page_image.save(buffer, format='PNG')
    buffer.seek(0)

    return Response(content=buffer.read(), media_type="image/png")

@router.get("/page-marked/{book_id}/{page_number}")
async def get_marked_page(book_id: int, page_number: int):
    """Get marked page image with rectangles."""
    marked_image = PageService().get_page_image(book_id, page_number, marked=True)

    buffer = BytesIO()
    marked_image.save(buffer, format='PNG')
    buffer.seek(0)

    return Response(content=buffer.read(), media_type="image/png")
```

**Tests:**
- Test original page retrieval
- Test marked page retrieval

---

### CHUNK-038: WebSocket Handler
**File:** `src/api/websocket.py`
**LOC:** 45-50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-027 (processing state)

**Purpose:** Real-time processing updates via WebSocket

**Scope:**
```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@app.websocket("/ws/processing/{book_id}")
async def websocket_processing(websocket: WebSocket, book_id: int):
    """WebSocket endpoint for real-time processing updates."""
    await websocket.accept()

    try:
        while True:
            # Get current processing state
            state = ProcessingStateService().get_state(book_id)

            # Send update
            await websocket.send_json({
                "event": "processing_update",
                "book_id": book_id,
                "current_page": state['current_page'],
                "progress_percentage": state['progress_percentage'],
                "knowledge_units_extracted": state['knowledge_units_extracted'],
                "images_extracted": state['images_extracted'],
                "estimated_time_remaining": state['estimated_time_remaining'],
                "timestamp": datetime.now().isoformat()
            })

            # Check if completed
            if state['status'] == 'completed':
                await websocket.send_json({
                    "event": "processing_complete",
                    "book_id": book_id,
                    "timestamp": datetime.now().isoformat()
                })
                break

            # Wait 2 seconds before next update
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for book {book_id}")
```

**Tests:**
- Test WebSocket connection
- Test message sending
- Test disconnection

---

### CHUNK-039: HTML Template - Upload Page
**File:** `src/frontend/templates/upload.html`
**LOC:** 50
**Complexity:** Simple
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-031 (FastAPI app)

**Purpose:** Upload page HTML/CSS/JavaScript

**Scope:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Upload Book - Knowledge Extraction</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <div class="upload-container">
        <h1>Upload Document</h1>
        <form id="upload-form">
            <div class="file-upload">
                <input type="file" id="file-input" required>
                <label for="file-input">Choose File or Drag & Drop</label>
            </div>

            <div class="settings">
                <label>Language:
                    <select id="language-setting">
                        <option value="auto">Auto-Detect</option>
                        <option value="english">English</option>
                        <option value="arabic">Arabic</option>
                    </select>
                </label>

                <!-- More settings -->

                <div class="attribute-keys">
                    <h3>Custom Attributes (2-30)</h3>
                    <input type="text" id="attr2" placeholder="e.g., Difficulty Level">
                    <input type="text" id="attr3" placeholder="e.g., Topic Category">
                    <!-- ... up to attr30 -->
                </div>
            </div>

            <button type="submit">Upload & Start Processing</button>
        </form>
    </div>

    <script src="/static/js/upload.js"></script>
</body>
</html>
```

**Tests:**
- Test file upload
- Test form validation
- Test settings submission

---

### CHUNK-040: JavaScript - Upload Handler
**File:** `src/frontend/static/js/upload.js`
**LOC:** 50
**Complexity:** Moderate
**Effort:** Medium (3 hours)
**Dependencies:** CHUNK-032 (upload API), CHUNK-039 (upload HTML)

**Purpose:** Handle file upload and form submission

**Scope:**
```javascript
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file');
        return;
    }

    // Collect settings
    const formData = new FormData();
    formData.append('file', file);
    formData.append('book_name', file.name);
    formData.append('language_setting', document.getElementById('language-setting').value);
    // ... other settings

    // Collect attribute keys
    const attribute_keys = {};
    for (let i = 2; i <= 30; i++) {
        const input = document.getElementById(`attr${i}`);
        if (input && input.value) {
            attribute_keys[i] = input.value;
        }
    }
    formData.append('attribute_keys', JSON.stringify(attribute_keys));

    // Upload
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            // Start processing
            await fetch('/api/start-processing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ book_id: result.book_id })
            });

            // Redirect to dashboard
            window.location.href = `/dashboard?book_id=${result.book_id}`;
        } else {
            alert(`Error: ${result.detail}`);
        }
    } catch (error) {
        alert(`Upload failed: ${error.message}`);
    }
});
```

**Tests:**
- Test form submission
- Test file validation
- Test API calls

---

## 📦 LEVEL 4: INTEGRATION (5 chunks)

### CHUNK-041: Database Initialization Script
**File:** `src/database/init_db.py`
**LOC:** 40-50
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** CHUNK-002, CHUNK-003

**Purpose:** Initialize database with shared tables

**Scope:**
```python
def init_database():
    """Initialize database with shared tables and extensions."""
    # Create extensions
    engine.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
    engine.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create trigger function
    engine.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create shared tables
    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
```

**Tests:**
- Test database creation
- Test extensions
- Test trigger function

---

### CHUNK-042: Complete Frontend CSS
**File:** `src/frontend/static/css/styles.css`
**LOC:** 50
**Complexity:** Simple
**Effort:** Low (2 hours)
**Dependencies:** None

**Purpose:** Complete CSS styling for all pages

**Scope:**
```css
/* Reset and base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #f5f5f5;
}

/* Upload page styles */
.upload-container {
    max-width: 800px;
    margin: 50px auto;
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

/* Processing dashboard styles */
/* ... */

/* Verification interface styles (split-screen) */
/* ... */

/* Color coding */
.green { color: #00c853; }
.orange { color: #ff9800; }
.red { color: #f44336; }
.blue { color: #2196f3; }
```

**Tests:**
- Visual testing
- Responsive testing

---

### CHUNK-043: Requirements.txt & Setup Script
**File:** `requirements.txt` & `setup.sh`
**LOC:** 40 (combined)
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Dependency management and automated setup

**requirements.txt:**
```txt
(Content from technology-stack.md)
```

**setup.sh:**
```bash
#!/bin/bash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download AI models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Download spaCy models
python -m spacy download en_core_web_sm

echo "Setup complete! Initialize database with: python src/database/init_db.py"
```

**Tests:**
- Test setup script execution
- Verify all dependencies installed

---

### CHUNK-044: Configuration Files
**File:** `.env.example`, `config.yaml`
**LOC:** 30-40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** None

**Purpose:** Configuration templates

**.env.example:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_extraction
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
MODEL_CACHE_DIR=C:\Users\username\.cache\models
```

**config.yaml:**
```yaml
database:
  pool_size: 10
  max_overflow: 20

processing:
  checkpoint_frequency: 50
  batch_insert_size: 50

image:
  max_width: 800
  max_height: 600
  compression: lz4
```

**Tests:**
- Validate config loading

---

### CHUNK-045: Main Entry Point & Documentation
**File:** `README.md`, `src/__init__.py`
**LOC:** 40
**Complexity:** Simple
**Effort:** Low (1 hour)
**Dependencies:** All previous chunks

**Purpose:** Entry point and user documentation

**README.md:**
```markdown
# Knowledge Extraction System

## Quick Start

1. Install dependencies:
   ```bash
   bash setup.sh
   ```

2. Configure database:
   - Copy `.env.example` to `.env`
   - Update DATABASE_URL with your PostgreSQL credentials

3. Initialize database:
   ```bash
   python src/database/init_db.py
   ```

4. Run application:
   ```bash
   python src/main.py
   ```

5. Open browser:
   ```
   http://localhost:8000
   ```

## Requirements

- Python 3.9+
- PostgreSQL 15+ with pgvector
- Tesseract OCR 4.1+
```

**Tests:**
- Follow documentation
- Verify startup

---

## ✅ Summary

**Total Chunks:** 45
**Total Estimated LOC:** ~2,000 lines
**Total Estimated Time:** ~120-150 hours

**Dependency Levels:**
- Level 0: 8 chunks (Foundation)
- Level 1: 10 chunks (Core Logic)
- Level 2: 12 chunks (Services)
- Level 3: 10 chunks (Presentation)
- Level 4: 5 chunks (Integration)

**Developer Workflow:**
1. Implement chunks in order (CHUNK-001 → CHUNK-045)
2. Test each chunk before proceeding
3. Cannot skip or reorder chunks
4. Must pass all tests before moving to next level

**Ready for:** Tester Agent (generate test cases) + Developer Agent (implement chunks)

