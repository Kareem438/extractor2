# Data Model - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Architect:** Claude (Architect Agent)
**Status:** ✅ Data Model Complete

---

## 📋 Overview

This document provides detailed field specifications for all data entities in the system. It complements the database schema with business logic, validation rules, and data relationships.

---

## 🗂️ Entity Catalog

### Shared Entities
1. **BooksMetadata** - Shared table tracking all books

### Raw Data Entities (OCR Input/Output)
2. **RawPage** - Original page images extracted from PDF (OCR input)
3. **RawKnowledgeUnit** - Full page text from each OCR run (before splitting)

### Processed Data Entities (Split/Verified Records)
4. **KnowledgeUnit** - Split semantic text units (3-5 lines each)
5. **Page** - Page marking rectangles (references raw_pages for image data)
6. **Image** - Extracted images with AI descriptions
7. **ProcessingState** - Processing progress and agent states
8. **BookSettings** - Book-specific configuration
9. **Hierarchy** - Document structure (chapters/topics)
10. **AttributeKey** - Book-level attribute names (1-40)

---

## 1. BooksMetadata

**Purpose:** Central registry of all books in the system

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **book_id** | INTEGER | PRIMARY KEY, AUTO | - | Sequential book number (1, 2, 3, ...) |
| **book_name** | VARCHAR(255) | NOT NULL | - | Original filename (e.g., "Machine Learning.pdf") |
| **sanitized_name** | VARCHAR(100) | NOT NULL, UNIQUE | - | Sanitized name for tables (e.g., "ml_fundamentals") |
| **table_prefix** | VARCHAR(100) | NOT NULL, UNIQUE | - | Full prefix (e.g., "book1_ml_fundamentals") |
| **upload_date** | TIMESTAMP | NOT NULL | NOW() | When book was uploaded |
| **file_type** | VARCHAR(50) | NOT NULL | - | File extension (PDF, DOCX, TXT, EPUB, etc.) |
| **file_size_bytes** | BIGINT | NOT NULL | - | Original file size in bytes |
| **total_pages** | INTEGER | NOT NULL | - | Total number of pages |
| **processing_status** | VARCHAR(50) | NOT NULL | 'uploaded' | See status enum below |
| **current_page** | INTEGER | - | 0 | Last processed page number |
| **last_checkpoint_page** | INTEGER | - | 0 | Last checkpoint saved at page N |
| **language** | VARCHAR(50) | - | NULL | english, arabic, mixed, or NULL (auto-detected) |
| **extraction_sensitivity** | VARCHAR(50) | - | NULL | conservative, balanced, aggressive |
| **total_knowledge_units** | INTEGER | - | 0 | Total extracted records (updated during processing) |
| **total_images** | INTEGER | - | 0 | Total extracted images |
| **verified_units** | INTEGER | - | 0 | Count of verified knowledge units |
| **verified_percentage** | NUMERIC(5,2) | - | 0.00 | Calculated: (verified/total)*100 |
| **processing_started_at** | TIMESTAMP | NULLABLE | NULL | When processing began |
| **processing_completed_at** | TIMESTAMP | NULLABLE | NULL | When processing completed |
| **last_updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |
| **created_by** | VARCHAR(100) | - | 'system' | Future: user tracking |
| **notes** | TEXT | NULLABLE | NULL | Admin notes about the book |

### Status Enum

```python
class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"        # File uploaded, not yet processing
    PROCESSING = "processing"    # Currently being processed
    PAUSED = "paused"           # Processing paused by user
    COMPLETED = "completed"     # Processing finished
    ERROR = "error"             # Error during processing
```

### Business Rules

1. **Book Number Assignment:**
   - Sequential: 1, 2, 3, 4, ...
   - Never reused (even if book deleted)
   - Assigned when user clicks "Start Processing"

2. **Sanitization Rules:**
   ```python
   def sanitize_book_name(filename: str) -> str:
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
       return name
   ```

3. **Verified Percentage:**
   - Calculated automatically via trigger/function
   - Updated after each verification action
   - Formula: `(verified_units / total_knowledge_units) * 100`

4. **Table Prefix:**
   - Format: `book{book_id}_{sanitized_name}`
   - Example: `book1_ml_fundamentals`

### Sample Record

```python
{
    "book_id": 1,
    "book_name": "Machine Learning Fundamentals.pdf",
    "sanitized_name": "ml_fundamentals",
    "table_prefix": "book1_ml_fundamentals",
    "upload_date": "2025-11-03T10:30:00",
    "file_type": "PDF",
    "file_size_bytes": 52428800,  # 50 MB
    "total_pages": 450,
    "processing_status": "processing",
    "current_page": 45,
    "last_checkpoint_page": 0,
    "language": "english",
    "extraction_sensitivity": "balanced",
    "total_knowledge_units": 2250,
    "total_images": 180,
    "verified_units": 0,
    "verified_percentage": 0.00,
    "processing_started_at": "2025-11-03T10:35:00",
    "processing_completed_at": None,
    "last_updated_at": "2025-11-03T11:00:00",
    "created_by": "system",
    "notes": None
}
```

---

## 2. RawPage

**Purpose:** Store original page images extracted from PDF (used as OCR input)

**Note:** This is a base model - actual tables are book-specific (e.g., `raw_book1_ml_fundamentals_pages`)

**Data Flow:** PDF → **RawPage** → OCR Engines → RawKnowledgeUnit

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique page ID |
| **page_number** | INTEGER | NOT NULL, UNIQUE | - | Page number (1, 2, 3, ...) |
| **original_image_data** | BYTEA | NOT NULL | - | Compressed original page image (LZ4) |
| **original_format** | VARCHAR(20) | NOT NULL | - | Image format (PNG, JPEG) |
| **original_width** | INTEGER | NOT NULL | - | Image width in pixels |
| **original_height** | INTEGER | NOT NULL | - | Image height in pixels |
| **original_size_bytes** | INTEGER | NOT NULL | - | Compressed image size |
| **chapter** | VARCHAR(255) | NULLABLE | NULL | Book chapter (auto-detected from hierarchy) |
| **topic** | VARCHAR(255) | NULLABLE | NULL | Chapter topic |
| **sub_topic** | VARCHAR(255) | NULLABLE | NULL | Sub-topic |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |

### Business Rules

1. **Image Storage:**
   - Stored ONCE in raw_pages table
   - Referenced by both raw_knowledge_units (OCR input) and pages (for display)
   - Compressed with LZ4 algorithm
   - Original format preserved (no lossy conversion)

2. **Image Format:**
   - Preferred: PNG (lossless)
   - Fallback: JPEG (if PDF contains JPEG images)
   - Always extracted at original resolution
   - No rectangles or markers added

3. **Page Numbers:**
   - Sequential: 1, 2, 3, ...
   - Must be unique within book
   - Matches PDF page ordering

4. **Hierarchy Fields (chapter, topic, sub_topic):**
   - Auto-populated from hierarchy table based on page ranges
   - Matches structure defined in book{N}_{name}_hierarchy table
   - Used for organizing and filtering pages by document structure
   - NULL if page falls outside defined hierarchy ranges

### Sample Record

```python
{
    "id": 15,
    "page_number": 15,
    "original_image_data": b"\x89PNG\r\n...",  # Binary data
    "original_format": "PNG",
    "original_width": 1200,
    "original_height": 1600,
    "original_size_bytes": 234567,
    "chapter": "Chapter 1: Introduction to Machine Learning",
    "topic": "Types of Machine Learning",
    "sub_topic": None,
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T10:30:00"
}
```

---

## 3. RawKnowledgeUnit

**Purpose:** Store raw OCR extractions (full page text per OCR run, before splitting)

**Note:** This is a base model - actual tables are book-specific (e.g., `raw_book1_ml_fundamentals_knowledge_units`)

**Data Flow:** RawPage → OCR Engines → **RawKnowledgeUnit** → Split → KnowledgeUnit

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique raw extraction ID |
| **raw_page_id** | INTEGER | FK, NOT NULL | - | References raw_pages(id) |
| **page_number** | INTEGER | NOT NULL | - | Page number (for convenience) |
| **ocr_engine** | VARCHAR(50) | NOT NULL | - | paddleocr, surya, tesseract |
| **ocr_run_timestamp** | TIMESTAMP | NOT NULL | NOW() | When this OCR was run |
| **full_page_text** | TEXT | NOT NULL | - | Complete OCR result for entire page (UNSPLIT) |
| **text_length** | INTEGER | NOT NULL | - | Character count |
| **confidence_score** | NUMERIC(5,2) | NOT NULL | - | Average confidence for page (0.00-100.00) |
| **language** | VARCHAR(50) | NOT NULL | - | english, arabic, mixed |
| **extracted_image_ids** | TEXT[] | NULLABLE | NULL | Array of image IDs found on this page |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |

### OCR Engine Enum

```python
class OcrEngine(str, Enum):
    PADDLEOCR = "paddleocr"
    SURYA = "surya"
    TESSERACT = "tesseract"
```

### Business Rules

1. **OCR Sequential Processing:**
   - Each page processed by 3 OCR engines sequentially
   - Each OCR run creates one record per page
   - 500-page book = 1,500 raw_knowledge_units records (3 × 500)

2. **Full Page Text:**
   - Contains ALL text extracted from page (not split yet)
   - Preserves original OCR output exactly
   - May be 1000+ characters for dense pages
   - Used as source for splitting into semantic units

3. **Confidence Score:**
   - Average confidence for entire page
   - Used to select "best" OCR result for splitting
   - Range: 0.00 to 100.00
   - Higher score = selected for text_content in KnowledgeUnit

4. **Foreign Key Relationship:**
   - raw_page_id references raw_pages(id)
   - ON DELETE CASCADE: Deleting raw_page deletes all OCR extractions
   - Ensures OCR data linked to source image

5. **Workflow Integration:**
   - User clicks "Evaluate, Split & Mark" button
   - System selects highest confidence OCR result (attr2, attr3, or attr4)
   - Selected text split into semantic units (3-5 lines each)
   - Split records created in knowledge_units table with raw_knowledge_unit_id FK

### Sample Records

```python
# PaddleOCR extraction for page 15
{
    "id": 45,
    "raw_page_id": 15,
    "page_number": 15,
    "ocr_engine": "paddleocr",
    "ocr_run_timestamp": "2025-11-03T10:30:15",
    "full_page_text": "Machine learning is a subset of artificial intelligence that focuses on developing systems that can learn from data. These systems improve their performance over time without being explicitly programmed.\n\nKey Concepts:\n- Supervised Learning\n- Unsupervised Learning\n- Reinforcement Learning\n\n[FULL PAGE TEXT CONTINUES...]",
    "text_length": 2345,
    "confidence_score": 92.50,
    "language": "english",
    "extracted_image_ids": ["IMG-068", "IMG-069"],
    "created_at": "2025-11-03T10:30:15",
    "updated_at": "2025-11-03T10:30:15"
}

# Surya extraction for same page 15
{
    "id": 46,
    "raw_page_id": 15,
    "page_number": 15,
    "ocr_engine": "surya",
    "ocr_run_timestamp": "2025-11-03T10:30:18",
    "full_page_text": "Machine learning is a subset of artificial intelligence that focuses on developing systems that can learn from data. These systems improve their performance over time without being explicitly programmed.\n\n[SLIGHTLY DIFFERENT TEXT FROM SURYA]",
    "text_length": 2298,
    "confidence_score": 89.30,
    "language": "english",
    "extracted_image_ids": ["IMG-068", "IMG-069"],
    "created_at": "2025-11-03T10:30:18",
    "updated_at": "2025-11-03T10:30:18"
}
```

---

## 4. KnowledgeUnit

**Purpose:** Split semantic text units (3-5 lines per unit, processed from raw OCR data)

**Note:** This is a base model - actual tables are book-specific (e.g., `book1_ml_fundamentals_knowledge_units`)

**Data Flow:** RawKnowledgeUnit → **Split** → KnowledgeUnit (3-5 line records)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique record ID |
| **text_content** | TEXT | NOT NULL | - | Extracted text (3-5 lines) |
| **text_length** | INTEGER | NOT NULL | - | Character count |
| **line_count** | INTEGER | NOT NULL | - | Number of lines (typically 3-5) |
| **page_number** | INTEGER | NOT NULL | - | Source page number |
| **position_x** | INTEGER | NULLABLE | NULL | X coordinate of bounding box (pixels) |
| **position_y** | INTEGER | NULLABLE | NULL | Y coordinate (pixels) |
| **position_width** | INTEGER | NULLABLE | NULL | Bounding box width (pixels) |
| **position_height** | INTEGER | NULLABLE | NULL | Bounding box height (pixels) |
| **language** | VARCHAR(50) | NOT NULL | - | english, arabic, mixed |
| **confidence_score** | NUMERIC(5,2) | NOT NULL | - | 0.00 to 100.00 |
| **extraction_method** | VARCHAR(50) | NULLABLE | NULL | See extraction method enum |
| **chapter** | VARCHAR(255) | NULLABLE | NULL | Chapter name (editable) |
| **topic** | VARCHAR(255) | NULLABLE | NULL | Topic name (editable) |
| **sub_topic** | VARCHAR(255) | NULLABLE | NULL | Sub-topic name (editable) |
| **verified** | BOOLEAN | NOT NULL | FALSE | User verified this record? |
| **verified_at** | TIMESTAMP | NULLABLE | NULL | When verified |
| **verified_by** | VARCHAR(100) | NULLABLE | NULL | Who verified (future) |
| **raw_knowledge_unit_id** | INTEGER | FK, NOT NULL | - | References raw_knowledge_units(id) - parent OCR extraction |
| **attr1_value** | TEXT | NULLABLE | NULL | RESERVED: related_image |
| **attr2_value** | TEXT | NULLABLE | NULL | RESERVED: OCR text (paddleocr) |
| **attr3_value** | TEXT | NULLABLE | NULL | RESERVED: OCR text (surya) |
| **attr4_value** | TEXT | NULLABLE | NULL | RESERVED: OCR text (tesseract) |
| **attr5_value** | TEXT | NULLABLE | NULL | RESERVED: OCR confidence (paddleocr) |
| **attr6_value** | TEXT | NULLABLE | NULL | RESERVED: OCR confidence (surya) |
| **attr7_value** | TEXT | NULLABLE | NULL | RESERVED: OCR confidence (tesseract) |
| **attr8_value** | TEXT | NOT NULL | 'enabled' | RESERVED: record_status ('enabled' or 'disabled') |
| ... (attr9-attr40) | TEXT | NULLABLE | NULL | User-defined attributes 9-40 (32 total) |
| **merged_into_record_id** | INTEGER | NULLABLE (FK) | NULL | If disabled, which record was it merged into? |
| **original_record_ids** | TEXT[] | NULLABLE | NULL | Array of original record IDs (merge/split history) |
| **notes** | TEXT | NULLABLE | NULL | User notes/comments |
| **tags** | TEXT[] | NULLABLE | NULL | Array of tags |
| **linked_image_ids** | TEXT[] | NULLABLE | NULL | Array of image IDs (parsed from attr1_value) |
| **embedding** | vector(384) | NULLABLE | NULL | Text embedding for similarity search |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |

### Extraction Method Enum

```python
class ExtractionMethod(str, Enum):
    NATIVE_TEXT = "native_text"      # Extracted from PDF text layer
    OCR_STANDARD = "ocr_standard"    # Standard OCR (attempt 1)
    OCR_RETRY_ZOOM = "ocr_retry_zoom" # OCR with 200% zoom (attempt 2)
    OCR_RETRY_SEGMENT = "ocr_retry_segment" # OCR with region segmentation (attempt 3)
```

### Language Enum

```python
class Language(str, Enum):
    ENGLISH = "english"
    ARABIC = "arabic"
    MIXED = "mixed"  # Contains both English and Arabic
```

### Business Rules

1. **Text Content:**
   - Minimum 10 characters
   - Maximum 2000 characters (typical 100-500)
   - Target: 3-5 lines of text
   - Line break preservation: Use `\n` for line breaks

2. **Line Count:**
   - Target: 3-5 lines
   - Minimum: 1 line (for short extractions)
   - Maximum: 10 lines (if semantic unit requires)

3. **Confidence Score:**
   - Range: 0.00 to 100.00
   - Low: < 60% (needs review)
   - Medium: 60-80% (acceptable)
   - High: > 80% (good quality)
   - Triggers merge context display if < 70%

4. **Position Coordinates:**
   - Origin: Top-left corner of page
   - Units: Pixels
   - NULL if position unknown (fallback extraction)

5. **Raw Data Foreign Key:**
   - **raw_knowledge_unit_id:** References the parent OCR extraction in raw_knowledge_units
   - Links split record back to original full-page OCR extraction
   - ON DELETE RESTRICT: Cannot delete raw data if split records exist
   - Enables traceability from processed records back to raw OCR

6. **System-Reserved Attributes (1-8):**
   - **Attribute 1:** `related_image` - Links to related images
     - Format: `"image_id:IMG-068, page:136, figure:5.3"`
     - Multiple images: `"image_id:IMG-068, page:136; image_id:IMG-069, page:137"`
     - Parsed into `linked_image_ids` array for queries
   - **Attributes 2-4:** OCR text results (SPLIT from raw_knowledge_units)
     - Contains ONLY the text portion for this split record
     - Split proportionally based on semantic boundaries
     - Source: raw_knowledge_units.full_page_text (parent OCR extraction)
     - attr2: PaddleOCR split text
     - attr3: Surya split text
     - attr4: Tesseract split text
   - **Attributes 5-7:** OCR confidence scores from PaddleOCR, Surya, Tesseract
     - Inherited from parent raw_knowledge_units record
   - **Attribute 8:** `record_status` - 'enabled' (active) or 'disabled' (merged)
     - Default: 'enabled'
     - Set to 'disabled' when record is merged into another
     - Used for filtering in verification interface

7. **User-Defined Attributes (9-40):**
   - 32 attributes available for custom metadata
   - Key names defined in attribute_keys table
   - Values stored in knowledge_units table
   - Fully editable via Book Settings page

8. **Record Merging/Splitting:**
   - **merged_into_record_id**: References the target record if this record was merged
   - **original_record_ids**: Array of original record IDs for merge/split history
   - Merge: Target record receives combined text, source records marked disabled
   - Split: New records created with reference to original record ID
   - Undo: Can restore merged records or recombine split records

9. **Verification:**
   - `verified = FALSE` initially
   - Set to TRUE when user clicks "Approve" or "Approve & Next"
   - `verified_at` timestamp set automatically

9. **Embeddings:**
   - Generated by sentence-transformers (MiniLM model)
   - 384 dimensions
   - Used for similarity search (future cross-book linking)

### Sample Record

```python
{
    "id": 123,
    "text_content": "Machine learning algorithms can be broadly categorized into three types:\nsupervised learning, unsupervised learning, and reinforcement learning.\nEach type has distinct characteristics and use cases.",
    "text_length": 195,
    "line_count": 3,
    "page_number": 15,
    "position_x": 100,
    "position_y": 450,
    "position_width": 800,
    "position_height": 120,
    "language": "english",
    "confidence_score": 92.50,
    "extraction_method": "native_text",
    "chapter": "Chapter 1: Introduction",
    "topic": "Types of Machine Learning",
    "sub_topic": None,
    "verified": True,
    "verified_at": "2025-11-03T14:30:00",
    "verified_by": None,
    "attr1_value": None,  # No related image (system-reserved)
    "attr2_value": "Machine learning algorithms...",  # OCR result paddleocr (system-reserved)
    "attr3_value": "Machine learning algorithms...",  # OCR result surya (system-reserved)
    "attr4_value": "Machine learning algorithms...",  # OCR result tesseract (system-reserved)
    "attr5_value": "92.5",  # OCR confidence paddleocr (system-reserved)
    "attr6_value": "91.0",  # OCR confidence surya (system-reserved)
    "attr7_value": "89.5",  # OCR confidence tesseract (system-reserved)
    "attr8_value": "enabled",  # record_status (system-reserved)
    "attr9_value": "Beginner",  # Difficulty Level (user-defined)
    "attr10_value": "Theory",  # Topic Category (user-defined)
    "attr11_value": "High",  # Importance (user-defined)
    "attr12_value": "machine learning, supervised, unsupervised, reinforcement",  # Keywords (user-defined)
    # ... attr13-attr40 ...
    "merged_into_record_id": None,  # Not merged
    "original_record_ids": None,  # Not result of merge/split
    "notes": "Core definition - reference frequently",
    "tags": ["definition", "core_concept"],
    "linked_image_ids": [],
    "embedding": [0.123, -0.456, 0.789, ...],  # 384-dim vector
    "created_at": "2025-11-03T11:15:00",
    "updated_at": "2025-11-03T14:30:00"
}
```

---

## 6. Image

**Purpose:** Extracted images with AI-generated descriptions

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique image ID |
| **image_id** | VARCHAR(50) | NOT NULL, UNIQUE | - | Human-readable ID (e.g., "IMG-068") |
| **page_number** | INTEGER | NOT NULL | - | Source page number |
| **image_data** | BYTEA | NOT NULL | - | Compressed image blob (LZ4) |
| **image_format** | VARCHAR(20) | NOT NULL | - | PNG, JPEG, etc. |
| **original_width** | INTEGER | NOT NULL | - | Original width (pixels) |
| **original_height** | INTEGER | NOT NULL | - | Original height (pixels) |
| **stored_width** | INTEGER | NOT NULL | - | Stored width (may be resized) |
| **stored_height** | INTEGER | NOT NULL | - | Stored height |
| **file_size_bytes** | INTEGER | NOT NULL | - | Compressed size in bytes |
| **thumbnail_data** | BYTEA | NULLABLE | NULL | 200x200 thumbnail (LZ4) |
| **thumbnail_size_bytes** | INTEGER | NULLABLE | NULL | Thumbnail size |
| **position_x** | INTEGER | NULLABLE | NULL | X coordinate on page |
| **position_y** | INTEGER | NULLABLE | NULL | Y coordinate |
| **position_width** | INTEGER | NULLABLE | NULL | Bounding box width |
| **position_height** | INTEGER | NULLABLE | NULL | Bounding box height |
| **ai_description** | TEXT | NOT NULL | - | Human-readable AI description |
| **structured_json** | JSONB | NULLABLE | NULL | Structured data extraction |
| **image_type** | VARCHAR(50) | NULLABLE | NULL | See image type enum |
| **confidence_score** | NUMERIC(5,2) | NOT NULL | - | 0.00 to 100.00 |
| **tags** | TEXT[] | NULLABLE | NULL | User-defined tags |
| **caption** | TEXT | NULLABLE | NULL | Original caption (if detected) |
| **figure_number** | VARCHAR(50) | NULLABLE | NULL | e.g., "Figure 5.3", "Table 2.1" |
| **linked_text_ids** | INTEGER[] | NULLABLE | NULL | Array of knowledge_unit IDs |
| **embedding** | vector(512) | NULLABLE | NULL | Image embedding (CLIP model, future) |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |

### Image Type Enum

```python
class ImageType(str, Enum):
    DIAGRAM = "diagram"        # Flowcharts, diagrams
    CHART = "chart"           # Bar charts, line charts, pie charts
    GRAPH = "graph"           # Mathematical graphs
    TABLE = "table"           # Data tables
    PHOTO = "photo"           # Photographs
    SCREENSHOT = "screenshot" # Screenshots
    FORMULA = "formula"       # Mathematical formulas
    CODE = "code"             # Code snippets
    ILLUSTRATION = "illustration"  # General illustrations
    MAP = "map"               # Geographic maps
    OTHER = "other"           # Unknown type
```

### Business Rules

1. **Image ID Format:**
   - Pattern: `IMG-{NNN}` (e.g., IMG-001, IMG-068)
   - Sequential within book
   - Zero-padded to 3 digits

2. **Image Storage:**
   - Max dimensions: 800x600 (configurable in book settings)
   - Compression: LZ4 (fast, 30-50% reduction)
   - Format: PNG preferred (lossless)
   - Thumbnail: 200x200 square (for library view)

3. **AI Description:**
   - Generated by BLIP model
   - Minimum 20 characters
   - Human-readable sentence
   - Example: "A flowchart diagram showing the machine learning pipeline from data collection to model deployment."

4. **Structured JSON:**
   - Optional extraction of data from charts/tables
   - Example for bar chart:
     ```json
     {
       "type": "bar_chart",
       "title": "Model Accuracy Comparison",
       "x_axis": "Model Name",
       "y_axis": "Accuracy (%)",
       "data": [
         {"label": "SVM", "value": 85.5},
         {"label": "Random Forest", "value": 92.3}
       ]
     }
     ```

5. **Figure Number Detection:**
   - Regex pattern: `(Figure|Fig\.|Table|Diagram)\s+(\d+\.?\d*)`
   - Examples: "Figure 5.3", "Table 2.1", "Fig. 3"
   - Stored for reference in attr1_value of knowledge units

6. **Linked Text:**
   - Array of knowledge_unit IDs that reference this image
   - Updated when attr1_value mentions this image_id
   - Bidirectional relationship

### Sample Record

```python
{
    "id": 68,
    "image_id": "IMG-068",
    "page_number": 136,
    "image_data": b"\x04\x22\x4d\x18...",  # LZ4 compressed bytes
    "image_format": "PNG",
    "original_width": 1200,
    "original_height": 800,
    "stored_width": 800,
    "stored_height": 600,
    "file_size_bytes": 45678,
    "thumbnail_data": b"\x04\x22\x4d\x18...",
    "thumbnail_size_bytes": 8920,
    "position_x": 200,
    "position_y": 300,
    "position_width": 1000,
    "position_height": 700,
    "ai_description": "A detailed flowchart diagram illustrating the machine learning pipeline, starting from data collection, through preprocessing and feature engineering, to model training and evaluation, ending with deployment.",
    "structured_json": {
        "type": "flowchart",
        "steps": ["Data Collection", "Preprocessing", "Feature Engineering", "Model Training", "Evaluation", "Deployment"],
        "connections": [...]
    },
    "image_type": "diagram",
    "confidence_score": 92.30,
    "tags": ["pipeline", "workflow"],
    "caption": "Figure 5.3: Machine Learning Pipeline",
    "figure_number": "Figure 5.3",
    "linked_text_ids": [245, 246, 247],  # 3 knowledge units reference this image
    "embedding": None,  # Future: CLIP embeddings
    "created_at": "2025-11-03T11:20:00",
    "updated_at": "2025-11-03T14:00:00"
}
```

---

## 5. Page

**Purpose:** Store visual markers (green/orange rectangles) for split records

**Note:** This entity NO LONGER stores images - only rectangles. Images stored in raw_pages table.

**Data Flow:** RawPage (image stored once) ← **Page** (rectangles only)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique page record ID |
| **page_number** | INTEGER | NOT NULL, UNIQUE | - | Page number (1, 2, 3, ...) |
| **raw_page_id** | INTEGER | FK, NOT NULL | - | References raw_pages(id) for image data |
| **green_rectangles** | JSONB | NULLABLE | NULL | Array of green marker coordinates (see format below) |
| **orange_rectangles** | JSONB | NULLABLE | NULL | Array of orange marker coordinates (see format below) |
| **marker_generated** | BOOLEAN | NOT NULL | FALSE | Has marker been created? |
| **marker_generated_at** | TIMESTAMP | NULLABLE | NULL | When marker generated |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update timestamp |

### Rectangle Format (JSONB)

```json
// green_rectangles - Text extraction markers (correspond to split knowledge_units)
[
  {
    "x": 100,
    "y": 450,
    "width": 800,
    "height": 120,
    "knowledge_unit_id": 123,  // References knowledge_units.id (split record)
    "confidence": 92.5
  },
  {
    "x": 100,
    "y": 580,
    "width": 800,
    "height": 100,
    "knowledge_unit_id": 124,
    "confidence": 87.0
  }
]

// orange_rectangles - Image-linked text markers
[
  {
    "x": 150,
    "y": 900,
    "width": 600,
    "height": 80,
    "knowledge_unit_id": 125,  // References knowledge_units.id (split record)
    "image_id": "IMG-068",
    "figure_number": "Figure 5.3"
  }
]
```

### Business Rules

1. **Image Storage (NEW ARCHITECTURE):**
   - **NO image data** stored in pages table
   - Images stored ONCE in raw_pages table
   - raw_page_id foreign key references raw_pages(id)
   - Display marked page: Load raw_pages image + overlay rectangles from this table

2. **Rectangle Correspondence:**
   - Each green rectangle corresponds to ONE split record in knowledge_units
   - Rectangles generated AFTER "Evaluate, Split & Mark" completes
   - Rectangle coordinates match knowledge_units.position_* fields
   - Number of green rectangles = Number of split records for this page

3. **Marker Colors:**
   - Green rectangles: 2px thick, RGB(0, 255, 0) - Regular text extractions
   - Orange rectangles: 2px thick, RGB(255, 165, 0) - Image-linked text (contains attr1_value)

4. **Marker Generation Workflow:**
   - User clicks "Evaluate, Split & Mark"
   - System splits raw_knowledge_units into knowledge_units (3-5 line records)
   - Marker Agent generates rectangles based on knowledge_units positions
   - Rectangles stored as JSONB in this table
   - marker_generated flag set to TRUE

5. **Foreign Key Cascade:**
   - ON DELETE CASCADE: Deleting raw_page deletes this pages record
   - Ensures referential integrity with raw data

### Sample Record

```python
{
    "id": 15,
    "page_number": 15,
    "raw_page_id": 15,  # FK to raw_pages (image stored there)
    "green_rectangles": [
        {"x": 100, "y": 450, "width": 800, "height": 120, "knowledge_unit_id": 123, "confidence": 92.5},
        {"x": 100, "y": 580, "width": 800, "height": 100, "knowledge_unit_id": 124, "confidence": 87.0}
    ],
    "orange_rectangles": [
        {"x": 150, "y": 900, "width": 600, "height": 80, "knowledge_unit_id": 125, "image_id": "IMG-068"}
    ],
    "marker_generated": True,
    "marker_generated_at": "2025-11-03T11:25:00",
    "created_at": "2025-11-03T11:15:00",
    "updated_at": "2025-11-03T11:25:00"
}
```

---

## 7. ProcessingState

**Purpose:** Track processing progress for pause/resume

**Note:** Single-row table per book (id always = 1)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY | 1 | Always 1 (single row) |
| **status** | VARCHAR(50) | NOT NULL | 'not_started' | See status enum |
| **current_page** | INTEGER | NOT NULL | 0 | Currently processing page |
| **total_pages** | INTEGER | NOT NULL | - | Total pages in book |
| **progress_percentage** | NUMERIC(5,2) | - | 0.00 | (current/total)*100 |
| **last_checkpoint_page** | INTEGER | - | 0 | Last checkpoint saved |
| **checkpoint_frequency** | INTEGER | - | 50 | Save every N pages |
| **last_checkpoint_at** | TIMESTAMP | NULLABLE | NULL | Checkpoint timestamp |
| **agent_states** | JSONB | NULLABLE | NULL | Current state of all agents |
| **pages_processed** | INTEGER | - | 0 | Total pages completed |
| **knowledge_units_extracted** | INTEGER | - | 0 | Total KUs extracted |
| **images_extracted** | INTEGER | - | 0 | Total images extracted |
| **ocr_retry_count** | INTEGER | - | 0 | Total OCR retries |
| **error_count** | INTEGER | - | 0 | Total errors |
| **avg_page_processing_time** | NUMERIC(10,2) | NULLABLE | NULL | Seconds per page |
| **estimated_time_remaining** | INTEGER | NULLABLE | NULL | Seconds (calculated) |
| **last_error_message** | TEXT | NULLABLE | NULL | Last error |
| **last_error_at** | TIMESTAMP | NULLABLE | NULL | Error timestamp |
| **paused_at** | TIMESTAMP | NULLABLE | NULL | When paused |
| **resumed_at** | TIMESTAMP | NULLABLE | NULL | When resumed |
| **pause_count** | INTEGER | - | 0 | Times paused |
| **processing_started_at** | TIMESTAMP | NULLABLE | NULL | Start timestamp |
| **processing_completed_at** | TIMESTAMP | NULLABLE | NULL | End timestamp |
| **last_updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update |

### Agent States Format (JSONB)

```json
{
  "reader": {
    "status": "processing",
    "current_page": 45,
    "last_updated": "2025-11-03T11:30:00"
  },
  "splitter": {
    "status": "idle",
    "current_page": 44,
    "last_updated": "2025-11-03T11:29:00"
  },
  "marker": {
    "status": "idle",
    "current_page": 44,
    "last_updated": "2025-11-03T11:29:00"
  },
  "image_reader": {
    "status": "idle",
    "current_page": 44,
    "last_updated": "2025-11-03T11:29:00"
  }
}
```

### Business Rules

1. **Single Row Enforcement:**
   - Only one row per book
   - id always = 1
   - Enforced by CHECK constraint

2. **Progress Calculation:**
   - Formula: `(current_page / total_pages) * 100`
   - Updated after each page

3. **Checkpoint Logic:**
   - Save every 50 pages (configurable)
   - Save on pause
   - Save on error

4. **Time Estimation:**
   - Calculate avg time per page
   - Estimate remaining: `(total_pages - current_page) * avg_time`

### Sample Record

```python
{
    "id": 1,
    "status": "processing",
    "current_page": 45,
    "total_pages": 450,
    "progress_percentage": 10.00,
    "last_checkpoint_page": 0,
    "checkpoint_frequency": 50,
    "last_checkpoint_at": None,
    "agent_states": {
        "reader": {"status": "processing", "current_page": 45},
        "splitter": {"status": "idle", "current_page": 44},
        "marker": {"status": "idle", "current_page": 44},
        "image_reader": {"status": "idle", "current_page": 44}
    },
    "pages_processed": 44,
    "knowledge_units_extracted": 2200,
    "images_extracted": 72,
    "ocr_retry_count": 5,
    "error_count": 0,
    "avg_page_processing_time": 12.50,  # 12.5 seconds per page
    "estimated_time_remaining": 5062,  # ~84 minutes
    "last_error_message": None,
    "last_error_at": None,
    "paused_at": None,
    "resumed_at": None,
    "pause_count": 0,
    "processing_started_at": "2025-11-03T10:35:00",
    "processing_completed_at": None,
    "last_updated_at": "2025-11-03T11:00:00"
}
```

---

## 8. BookSettings

**Purpose:** Book-specific processing configuration

**Note:** Single-row table per book (id always = 1)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY | 1 | Always 1 (single row) |
| **special_instructions** | TEXT | NULLABLE | NULL | User-provided instructions |
| **language_setting** | VARCHAR(50) | - | 'auto' | auto, english, arabic, both |
| **extraction_sensitivity** | VARCHAR(50) | - | 'balanced' | conservative, balanced, aggressive |
| **image_processing** | VARCHAR(50) | - | 'all' | all, diagrams_only, skip |
| **ocr_quality** | VARCHAR(50) | - | 'balanced' | fast, balanced, high |
| **hierarchy_detection** | VARCHAR(50) | - | 'auto' | auto, manual, skip |
| **auto_detect_chapters** | BOOLEAN | - | TRUE | Auto-detect chapters? |
| **auto_detect_topics** | BOOLEAN | - | TRUE | Auto-detect topics? |
| **partial_processing_enabled** | BOOLEAN | - | FALSE | Process only first N pages? |
| **partial_processing_pages** | INTEGER | NULLABLE | NULL | How many pages (if enabled) |
| **ocr_retry_enabled** | BOOLEAN | - | TRUE | Enable retry logic? |
| **ocr_retry_max_attempts** | INTEGER | - | 3 | Max OCR attempts (1-5) |
| **ocr_zoom_factor** | NUMERIC(3,2) | - | 2.0 | Zoom for retry (1.0-5.0) |
| **image_max_width** | INTEGER | - | 800 | Max stored width |
| **image_max_height** | INTEGER | - | 600 | Max stored height |
| **image_compression** | VARCHAR(20) | - | 'lz4' | lz4, none |
| **thumbnail_size** | INTEGER | - | 200 | Thumbnail dimensions |
| **checkpoint_frequency** | INTEGER | - | 50 | Save every N pages |
| **batch_insert_size** | INTEGER | - | 50 | Insert N records at once |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update |

### Business Rules

1. **Validation:**
   - `ocr_zoom_factor`: 1.0 to 5.0
   - `ocr_retry_max_attempts`: 1 to 5
   - `checkpoint_frequency`: 10 to 200
   - `batch_insert_size`: 10 to 200
   - `partial_processing_pages`: 1 to total_pages

2. **Defaults:**
   - Most fields have sensible defaults
   - User can override at upload time
   - Settings cannot be changed during processing

### Sample Record

```python
{
    "id": 1,
    "special_instructions": "Focus on extracting code examples and mathematical formulas. Be aggressive with table detection.",
    "language_setting": "english",
    "extraction_sensitivity": "aggressive",
    "image_processing": "all",
    "ocr_quality": "high",
    "hierarchy_detection": "auto",
    "auto_detect_chapters": True,
    "auto_detect_topics": True,
    "partial_processing_enabled": True,
    "partial_processing_pages": 10,  # Test mode: first 10 pages only
    "ocr_retry_enabled": True,
    "ocr_retry_max_attempts": 3,
    "ocr_zoom_factor": 2.0,
    "image_max_width": 800,
    "image_max_height": 600,
    "image_compression": "lz4",
    "thumbnail_size": 200,
    "checkpoint_frequency": 50,
    "batch_insert_size": 50,
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T10:30:00"
}
```

---

## 9. Hierarchy

**Purpose:** Document structure (chapters, topics, sub-topics)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique hierarchy ID |
| **level** | INTEGER | NOT NULL | - | 1=chapter, 2=topic, 3=sub_topic |
| **parent_id** | INTEGER | NULLABLE (FK) | NULL | Parent hierarchy ID (NULL for chapters) |
| **name** | VARCHAR(255) | NOT NULL | - | Chapter/Topic/Sub-topic name |
| **page_start** | INTEGER | NOT NULL | - | First page of this section |
| **page_end** | INTEGER | NULLABLE | NULL | Last page (NULL if unknown) |
| **order_index** | INTEGER | NOT NULL | - | Order within parent (1, 2, 3, ...) |
| **auto_detected** | BOOLEAN | - | TRUE | Detected by AI or manual? |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update |

### Level Enum

```python
class HierarchyLevel(int, Enum):
    CHAPTER = 1
    TOPIC = 2
    SUB_TOPIC = 3
```

### Business Rules

1. **Hierarchy Structure:**
   - Level 1 (Chapters): parent_id = NULL
   - Level 2 (Topics): parent_id = chapter_id
   - Level 3 (Sub-topics): parent_id = topic_id

2. **Order Index:**
   - Sequential within same level and parent
   - Chapter 1, Chapter 2, Chapter 3
   - Topic 1.1, Topic 1.2, Topic 1.3 (within Chapter 1)

3. **Page Ranges:**
   - page_start is required
   - page_end is optional (estimated or NULL)
   - Used to auto-assign hierarchy to knowledge units

4. **Name Format:**
   - Can include numbering: "Chapter 1: Introduction"
   - Or without: "Introduction"
   - Editable by user

### Sample Records

```python
# Chapter 1
{
    "id": 1,
    "level": 1,
    "parent_id": None,
    "name": "Chapter 1: Introduction to Machine Learning",
    "page_start": 1,
    "page_end": 50,
    "order_index": 1,
    "auto_detected": True,
    "created_at": "2025-11-03T10:35:00",
    "updated_at": "2025-11-03T10:35:00"
}

# Topic 1.1
{
    "id": 2,
    "level": 2,
    "parent_id": 1,  # Chapter 1
    "name": "1.1 What is Machine Learning?",
    "page_start": 5,
    "page_end": 15,
    "order_index": 1,
    "auto_detected": True,
    "created_at": "2025-11-03T10:35:00",
    "updated_at": "2025-11-03T10:35:00"
}

# Sub-topic 1.1.1
{
    "id": 3,
    "level": 3,
    "parent_id": 2,  # Topic 1.1
    "name": "1.1.1 Supervised Learning",
    "page_start": 6,
    "page_end": 10,
    "order_index": 1,
    "auto_detected": True,
    "created_at": "2025-11-03T10:35:00",
    "updated_at": "2025-11-03T10:35:00"
}
```

---

## 10. AttributeKey

**Purpose:** Book-level attribute key names (80 attributes)

### Fields

| Field Name | Type | Constraints | Default | Description |
|------------|------|-------------|---------|-------------|
| **id** | INTEGER | PRIMARY KEY, AUTO | - | Unique attribute key ID |
| **attr_number** | INTEGER | NOT NULL, UNIQUE | - | 1 to 40 |
| **key_name** | VARCHAR(100) | NOT NULL | - | Attribute name (e.g., "Difficulty Level") |
| **is_system_reserved** | BOOLEAN | - | FALSE | TRUE for attributes 1-8 (system-reserved) |
| **is_editable** | BOOLEAN | - | TRUE | FALSE for attributes 1-8 |
| **description** | TEXT | NULLABLE | NULL | Optional description |
| **placeholder_example** | VARCHAR(255) | NULLABLE | NULL | Example value for UI |
| **created_at** | TIMESTAMP | NOT NULL | NOW() | Creation timestamp |
| **updated_at** | TIMESTAMP | NOT NULL | NOW() | Last update |

### Business Rules

1. **40 Attributes:**
   - attr_number 1-40 (exactly 40 rows)
   - Each book has exactly 40 attribute keys

2. **System-Reserved Attributes (1-8):**
   - **Attribute 1:** "related_image" - Links to related images
   - **Attribute 2:** "ocr_text_paddleocr" - OCR text result from PaddleOCR
   - **Attribute 3:** "ocr_text_surya" - OCR text result from Surya
   - **Attribute 4:** "ocr_text_tesseract" - OCR text result from Tesseract
   - **Attribute 5:** "ocr_confidence_paddleocr" - OCR confidence score from PaddleOCR
   - **Attribute 6:** "ocr_confidence_surya" - OCR confidence score from Surya
   - **Attribute 7:** "ocr_confidence_tesseract" - OCR confidence score from Tesseract
   - **Attribute 8:** "record_status" - Record status ('enabled' or 'disabled')
   - is_system_reserved: TRUE
   - is_editable: FALSE
   - Cannot be changed by user

3. **User-Defined Attributes (9-40):**
   - 32 attributes available for custom metadata
   - key_name: Set by user at upload time
   - Can be edited post-upload via Book Settings page
   - Empty key_name hides attribute in UI

4. **Default Suggestions for User-Defined:**
   - Provide common examples as placeholders:
     - "Difficulty Level" (attr9)
     - "Topic Category" (attr10)
     - "Importance" (attr11)
     - "Keywords" (attr12)
     - "Author Opinion" (attr13)
     - "Code Example" (attr14)
     - "Mathematical" (attr15)
     - etc.

### Sample Records

```python
# Attribute 1 (system-reserved)
{
    "id": 1,
    "attr_number": 1,
    "key_name": "related_image",
    "is_system_reserved": True,
    "is_editable": False,
    "description": "System-reserved: Links to related images (format: image_id:IMG-XX, page:XX, figure:X.X)",
    "placeholder_example": "image_id:IMG-068, page:136, figure:5.3",
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T10:30:00"
}

# Attribute 8 (system-reserved - record_status)
{
    "id": 8,
    "attr_number": 8,
    "key_name": "record_status",
    "is_system_reserved": True,
    "is_editable": False,
    "description": "System-reserved: Record status ('enabled' or 'disabled' for merge/split tracking)",
    "placeholder_example": "enabled",
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T10:30:00"
}

# Attribute 9 (user-defined)
{
    "id": 9,
    "attr_number": 9,
    "key_name": "Difficulty Level",
    "is_system_reserved": False,
    "is_editable": True,
    "description": "Complexity level of the content",
    "placeholder_example": "Beginner, Intermediate, Advanced",
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T14:00:00"  # Edited later
}

# Attribute 20 (empty - hidden in UI)
{
    "id": 20,
    "attr_number": 20,
    "key_name": "",  # Empty = not used
    "is_system_reserved": False,
    "is_editable": True,
    "description": "Custom attribute 20",
    "placeholder_example": None,
    "created_at": "2025-11-03T10:30:00",
    "updated_at": "2025-11-03T10:30:00"
}
```

---

## ✅ Data Model Checklist

- [x] All 8 entities defined with complete field specifications
- [x] Validation rules documented
- [x] Enums defined for status/type fields
- [x] Business rules explained
- [x] Sample records provided for each entity
- [x] Relationships between entities clarified
- [x] Default values specified
- [x] Constraints documented
- [x] 40 attribute architecture detailed (book-level keys, record-level values)
- [x] System-reserved attributes (1-8) documented and locked
- [x] User-defined attributes (9-40) with 32 available for customization
- [x] Record merging/splitting columns documented (merged_into_record_id, original_record_ids)
- [x] Attribute 8 (record_status) for merge/split tracking
- [x] Single-row tables identified (ProcessingState, BookSettings)

---

**Data Model Complete:** ✅
**Total Entities:** 8 (1 shared + 7 book-specific)
**Ready for:** API Design + Code Chunk Breakdown

