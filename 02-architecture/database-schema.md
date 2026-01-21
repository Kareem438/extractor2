# Database Schema - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Database:** PostgreSQL 15+ with pgvector extension
**ORM:** SQLAlchemy 2.0+
**Status:** ✅ Schema Design Complete

---

## 📋 Overview

The database uses a **hybrid approach** with **raw and processed data separation**:
- **1 Shared Table:** `books_metadata` (tracks all books)
- **9 Book-Specific Tables per book:** Isolated data per book with `book{N}_{name}_` prefix
  - **2 Raw Tables:** Store original OCR extractions and page images
  - **7 Processed Tables:** Store split/verified data, marked pages, images, settings, etc.
- **PostgreSQL + pgvector:** Main relational database with vector support
- **Chroma:** Separate vector database for future cross-book similarity

**Total Tables per Book:** 10 (1 shared + 9 book-specific)

### Data Flow Architecture

```
OCR Extraction → raw_pages + raw_knowledge_units (full page text per OCR)
       ↓
User clicks "Evaluate, Split & Mark"
       ↓
Best confidence text selected → Split into semantic units
       ↓
knowledge_units (split records, FK to raw) + pages (rectangles, FK to raw_pages)
```

---

## 🏷️ Naming Convention

### Table Naming Format
```
book{N}_{sanitized_book_name}_{purpose}
```

**Examples:**
- `book1_ml_fundamentals_knowledge_units`
- `book1_ml_fundamentals_images`
- `book2_deep_learning_python_knowledge_units`

### Book Number Assignment
- Sequential integers: 1, 2, 3, 4, ...
- **Never reused** (even if book deleted)
- Assigned when user clicks "Start Processing"

### Sanitization Rules
1. Lowercase all characters
2. Remove file extensions (.pdf, .docx, etc.)
3. Replace spaces with underscores
4. Remove special characters (keep underscores only)
5. Limit to 50 characters
6. Transliterate non-Latin characters (e.g., Arabic → "arabic_title")

---

## 📊 Shared Table: books_metadata

**Purpose:** Track all books in the system (single source of truth)

### Schema

```sql
CREATE TABLE books_metadata (
    -- Primary Key
    book_id                 SERIAL PRIMARY KEY,

    -- Book Identification
    book_name               VARCHAR(255) NOT NULL,          -- Original filename
    sanitized_name          VARCHAR(100) NOT NULL UNIQUE,   -- Sanitized for table names
    table_prefix            VARCHAR(100) NOT NULL UNIQUE,   -- "book{N}_{sanitized_name}"

    -- File Metadata
    upload_date             TIMESTAMP NOT NULL DEFAULT NOW(),
    file_type               VARCHAR(50) NOT NULL,           -- PDF, DOCX, TXT, etc.
    file_size_bytes         BIGINT NOT NULL,                -- Original file size
    total_pages             INTEGER NOT NULL,               -- Total pages in document

    -- Processing Status
    processing_status       VARCHAR(50) NOT NULL DEFAULT 'uploaded',
        -- Values: uploaded, processing, paused, completed, error
    current_page            INTEGER DEFAULT 0,              -- Last processed page
    last_checkpoint_page    INTEGER DEFAULT 0,              -- Last checkpoint saved

    -- Language & Settings
    language                VARCHAR(50),                    -- english, arabic, mixed, auto
    extraction_sensitivity  VARCHAR(50),                    -- conservative, balanced, aggressive

    -- Statistics (updated during processing)
    total_knowledge_units   INTEGER DEFAULT 0,
    total_images            INTEGER DEFAULT 0,
    verified_units          INTEGER DEFAULT 0,              -- Count of verified records
    verified_percentage     NUMERIC(5,2) DEFAULT 0.00,      -- Calculated: (verified/total)*100

    -- Timestamps
    processing_started_at   TIMESTAMP,
    processing_completed_at TIMESTAMP,
    last_updated_at         TIMESTAMP DEFAULT NOW(),

    -- Metadata
    created_by              VARCHAR(100) DEFAULT 'system',  -- Future: user tracking
    notes                   TEXT                            -- Admin notes
);

-- Indexes
CREATE INDEX idx_books_status ON books_metadata(processing_status);
CREATE INDEX idx_books_upload_date ON books_metadata(upload_date DESC);
CREATE INDEX idx_books_language ON books_metadata(language);
CREATE UNIQUE INDEX idx_books_table_prefix ON books_metadata(table_prefix);
```

**Sample Data:**
```sql
INSERT INTO books_metadata (book_id, book_name, sanitized_name, table_prefix, file_type, file_size_bytes, total_pages, language)
VALUES (1, 'Machine Learning Fundamentals.pdf', 'ml_fundamentals', 'book1_ml_fundamentals', 'PDF', 52428800, 450, 'english');
```

---

## 📘 Book-Specific Tables (9 per book)

### Raw Data Tables (2 tables)

#### 1. raw_book{N}_{name}_pages

**Purpose:** Store original page images extracted from PDF (no rectangles, used as input for OCR)

**Schema:**
```sql
CREATE TABLE raw_book1_ml_fundamentals_pages (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Page Identification
    page_number             INTEGER NOT NULL UNIQUE,        -- 1, 2, 3, ...

    -- Original Page Image (INPUT for OCR)
    original_image_data     BYTEA NOT NULL,                 -- Compressed original page (LZ4)
    original_format         VARCHAR(20) NOT NULL,           -- PNG, JPEG
    original_width          INTEGER NOT NULL,
    original_height         INTEGER NOT NULL,
    original_size_bytes     INTEGER NOT NULL,

    -- Hierarchy (Document Structure)
    chapter                 VARCHAR(255),                   -- Book chapter (auto-detected from hierarchy table)
    topic                   VARCHAR(255),                   -- Chapter topic
    sub_topic               VARCHAR(255),                   -- Sub-topic

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_raw_book1_pages_number ON raw_book1_ml_fundamentals_pages(page_number);
CREATE INDEX idx_raw_book1_pages_chapter ON raw_book1_ml_fundamentals_pages(chapter);

-- Trigger
CREATE TRIGGER update_raw_book1_pages_updated_at
    BEFORE UPDATE ON raw_book1_ml_fundamentals_pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
INSERT INTO raw_book1_ml_fundamentals_pages
(page_number, original_image_data, original_format, original_width, original_height, original_size_bytes, chapter, topic, sub_topic)
VALUES
(15, decode('89504e47...', 'hex'), 'PNG', 1200, 1600, 234567, 'Chapter 1: Introduction to Machine Learning', 'Types of Machine Learning', NULL);
```

---

#### 2. raw_book{N}_{name}_knowledge_units

**Purpose:** Store raw OCR extractions (full page text per OCR run, before splitting)

**Schema:**
```sql
CREATE TABLE raw_book1_ml_fundamentals_knowledge_units (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Foreign Key to Raw Pages
    raw_page_id             INTEGER NOT NULL,               -- FK to raw_pages
    page_number             INTEGER NOT NULL,               -- For convenience

    -- OCR Metadata
    ocr_engine              VARCHAR(50) NOT NULL,           -- paddleocr, surya, tesseract
    ocr_run_timestamp       TIMESTAMP DEFAULT NOW(),        -- When this OCR was run

    -- Full Page Text (UNSPLIT)
    full_page_text          TEXT NOT NULL,                  -- Complete OCR result for entire page
    text_length             INTEGER NOT NULL,               -- Character count

    -- OCR Quality Metrics
    confidence_score        NUMERIC(5,2) NOT NULL,          -- 0.00 to 100.00 (average for page)
    language                VARCHAR(50) NOT NULL,           -- english, arabic, mixed

    -- Extracted Images on this Page (from this OCR run)
    extracted_image_ids     TEXT[],                         -- Array of image IDs found on page

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    -- Foreign Key Constraint
    FOREIGN KEY (raw_page_id) REFERENCES raw_book1_ml_fundamentals_pages(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_raw_book1_ku_page ON raw_book1_ml_fundamentals_knowledge_units(page_number);
CREATE INDEX idx_raw_book1_ku_engine ON raw_book1_ml_fundamentals_knowledge_units(ocr_engine);
CREATE INDEX idx_raw_book1_ku_raw_page ON raw_book1_ml_fundamentals_knowledge_units(raw_page_id);

-- Trigger
CREATE TRIGGER update_raw_book1_ku_updated_at
    BEFORE UPDATE ON raw_book1_ml_fundamentals_knowledge_units
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
-- PaddleOCR run for page 15
INSERT INTO raw_book1_ml_fundamentals_knowledge_units
(raw_page_id, page_number, ocr_engine, full_page_text, text_length, confidence_score, language, extracted_image_ids)
VALUES
(15, 15, 'paddleocr', 'Machine learning is a subset of artificial intelligence...
[FULL PAGE TEXT HERE - could be 1000+ characters]', 2345, 92.50, 'english', ARRAY['IMG-068', 'IMG-069']);

-- Surya OCR run for same page 15
INSERT INTO raw_book1_ml_fundamentals_knowledge_units
(raw_page_id, page_number, ocr_engine, full_page_text, text_length, confidence_score, language, extracted_image_ids)
VALUES
(15, 15, 'surya', 'Machine learning is a subset of artificial intelligence...
[FULL PAGE TEXT FROM SURYA]', 2298, 89.30, 'english', ARRAY['IMG-068', 'IMG-069']);
```

---

### Processed Data Tables (7 tables)

#### 3. book{N}_{name}_knowledge_units

**Purpose:** Store split text records with 40 custom attributes (processed from raw OCR data)

**Key Changes:**
- References `raw_knowledge_units` via FK
- Contains split semantic units (3-5 lines each)
- Inherits OCR attribute values from parent raw record (split proportionally)
- System selects highest confidence OCR text for `text_content`

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_knowledge_units (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Core Text Data
    text_content            TEXT NOT NULL,                  -- Extracted text (3-5 lines)
    text_length             INTEGER NOT NULL,               -- Character count
    line_count              INTEGER NOT NULL,               -- Number of lines (3-5)

    -- Location Information
    page_number             INTEGER NOT NULL,               -- Source page
    position_x              INTEGER,                        -- X coordinate (pixels)
    position_y              INTEGER,                        -- Y coordinate (pixels)
    position_width          INTEGER,                        -- Bounding box width
    position_height         INTEGER,                        -- Bounding box height

    -- Language & Confidence
    language                VARCHAR(50) NOT NULL,           -- english, arabic, mixed
    confidence_score        NUMERIC(5,2) NOT NULL,          -- 0.00 to 100.00
    extraction_method       VARCHAR(50),                    -- native_text, ocr_standard, ocr_retry

    -- Hierarchy (editable)
    chapter                 VARCHAR(255),                   -- Book chapter
    topic                   VARCHAR(255),                   -- Chapter topic
    sub_topic               VARCHAR(255),                   -- Sub-topic

    -- Verification Status
    verified                BOOLEAN DEFAULT FALSE,          -- User verified?
    verified_at             TIMESTAMP,                      -- When verified
    verified_by             VARCHAR(100),                   -- Who verified (future)

    -- Foreign Key to Raw Knowledge Units
    raw_knowledge_unit_id   INTEGER NOT NULL,               -- FK to raw_knowledge_units (parent OCR extraction)

    -- Custom Attributes (40 columns for VALUES only, keys stored in attribute_keys table)
    -- System-Reserved Attributes (1-8)
    attr1_value             TEXT,                           -- RESERVED: related_image (e.g., "image_id:IMG-68, page:136, figure:5.3")
    attr2_value             TEXT,                           -- RESERVED: OCR text result (paddleocr) - SPLIT from raw
    attr3_value             TEXT,                           -- RESERVED: OCR text result (surya) - SPLIT from raw
    attr4_value             TEXT,                           -- RESERVED: OCR text result (tesseract) - SPLIT from raw
    attr5_value             TEXT,                           -- RESERVED: OCR confidence score (paddleocr)
    attr6_value             TEXT,                           -- RESERVED: OCR confidence score (surya)
    attr7_value             TEXT,                           -- RESERVED: OCR confidence score (tesseract)
    attr8_value             TEXT DEFAULT 'enabled',         -- RESERVED: record_status ('enabled' or 'disabled')

    -- User-Defined Attributes (9-40)
    attr9_value             TEXT,
    attr10_value            TEXT,
    attr11_value            TEXT,
    attr12_value            TEXT,
    attr13_value            TEXT,
    attr14_value            TEXT,
    attr15_value            TEXT,
    attr16_value            TEXT,
    attr17_value            TEXT,
    attr18_value            TEXT,
    attr19_value            TEXT,
    attr20_value            TEXT,
    attr21_value            TEXT,
    attr22_value            TEXT,
    attr23_value            TEXT,
    attr24_value            TEXT,
    attr25_value            TEXT,
    attr26_value            TEXT,
    attr27_value            TEXT,
    attr28_value            TEXT,
    attr29_value            TEXT,
    attr30_value            TEXT,
    attr31_value            TEXT,
    attr32_value            TEXT,
    attr33_value            TEXT,
    attr34_value            TEXT,
    attr35_value            TEXT,
    attr36_value            TEXT,
    attr37_value            TEXT,
    attr38_value            TEXT,
    attr39_value            TEXT,
    attr40_value            TEXT,

    -- Record Merging/Splitting Tracking
    merged_into_record_id   INTEGER,                        -- If disabled, which record was it merged into?
    original_record_ids     TEXT[],                         -- Array of original record IDs (for merge/split history)

    -- Additional Metadata
    notes                   TEXT,                           -- User notes/comments
    tags                    TEXT[],                         -- Array of tags
    linked_image_ids        TEXT[],                         -- Array of image IDs (extracted from attr1_value)

    -- Vector Embedding (for future similarity search)
    embedding               vector(384),                    -- pgvector: 384-dim from MiniLM model

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    -- Foreign Key Constraints
    FOREIGN KEY (raw_knowledge_unit_id) REFERENCES raw_book1_ml_fundamentals_knowledge_units(id) ON DELETE RESTRICT,
    FOREIGN KEY (merged_into_record_id) REFERENCES book1_ml_fundamentals_knowledge_units(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_book1_ku_page ON book1_ml_fundamentals_knowledge_units(page_number);
CREATE INDEX idx_book1_ku_verified ON book1_ml_fundamentals_knowledge_units(verified);
CREATE INDEX idx_book1_ku_confidence ON book1_ml_fundamentals_knowledge_units(confidence_score);
CREATE INDEX idx_book1_ku_language ON book1_ml_fundamentals_knowledge_units(language);
CREATE INDEX idx_book1_ku_chapter ON book1_ml_fundamentals_knowledge_units(chapter);

-- Indexes for Record Merging/Splitting (NEW)
CREATE INDEX idx_book1_ku_record_status ON book1_ml_fundamentals_knowledge_units(attr8_value);
CREATE INDEX idx_book1_ku_merged_into ON book1_ml_fundamentals_knowledge_units(merged_into_record_id);
CREATE INDEX idx_book1_ku_original_ids ON book1_ml_fundamentals_knowledge_units USING GIN(original_record_ids);

-- Index for Raw FK
CREATE INDEX idx_book1_ku_raw_id ON book1_ml_fundamentals_knowledge_units(raw_knowledge_unit_id);

-- Vector Index (for future similarity search)
CREATE INDEX idx_book1_ku_embedding ON book1_ml_fundamentals_knowledge_units
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_book1_ku_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_knowledge_units
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
-- Regular enabled record
INSERT INTO book1_ml_fundamentals_knowledge_units
(text_content, text_length, line_count, page_number, language, confidence_score, chapter,
 attr1_value, attr8_value, attr9_value)
VALUES
('Machine learning is a subset of artificial intelligence that focuses on
developing systems that can learn from data. These systems improve their
performance over time without being explicitly programmed.', 195, 3, 5, 'english', 95.50,
'Chapter 1: Introduction', NULL, 'enabled', 'Definition');

-- Merged record (disabled)
INSERT INTO book1_ml_fundamentals_knowledge_units
(text_content, text_length, line_count, page_number, language, confidence_score, chapter,
 attr8_value, merged_into_record_id, original_record_ids)
VALUES
('', 0, 0, 5, 'english', 0, 'Chapter 1: Introduction',
 'disabled', 123, ARRAY['124']);

-- Record created from merge (contains original IDs)
UPDATE book1_ml_fundamentals_knowledge_units
SET original_record_ids = ARRAY['123', '124', '125']
WHERE id = 123;
```

---

#### 4. book{N}_{name}_pages

**Purpose:** Store marking rectangles for split records (references raw_pages for image data)

**Key Changes:**
- **NO image storage** - only rectangles
- **FK to raw_pages** for image data
- Rectangles correspond to split records in `knowledge_units`

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_pages (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Page Identification
    page_number             INTEGER NOT NULL UNIQUE,        -- 1, 2, 3, ...

    -- Foreign Key to Raw Pages (for image data)
    raw_page_id             INTEGER NOT NULL,               -- FK to raw_pages (IMAGE STORED ONCE)

    -- Marker Metadata (corresponds to split knowledge_units)
    green_rectangles        JSONB,                          -- Array of green rectangle coordinates
        -- Format: [{"x": 100, "y": 200, "width": 300, "height": 50, "knowledge_unit_id": 123}, ...]
    orange_rectangles       JSONB,                          -- Array of orange rectangle coordinates
        -- Format: [{"x": 150, "y": 400, "width": 200, "height": 60, "image_id": "IMG-068"}, ...]

    -- Processing Metadata
    marker_generated        BOOLEAN DEFAULT FALSE,          -- Has marker been created?
    marker_generated_at     TIMESTAMP,

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    -- Foreign Key Constraint
    FOREIGN KEY (raw_page_id) REFERENCES raw_book1_ml_fundamentals_pages(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_book1_pages_number ON book1_ml_fundamentals_pages(page_number);
CREATE INDEX idx_book1_pages_marker_status ON book1_ml_fundamentals_pages(marker_generated);
CREATE INDEX idx_book1_pages_raw_page ON book1_ml_fundamentals_pages(raw_page_id);

-- Trigger
CREATE TRIGGER update_book1_pages_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
INSERT INTO book1_ml_fundamentals_pages
(page_number, raw_page_id, green_rectangles, orange_rectangles, marker_generated)
VALUES
(5, 15,  -- FK to raw_pages (image stored once in raw table)
 '[{"x": 100, "y": 200, "width": 800, "height": 120, "knowledge_unit_id": 45}]'::jsonb,
 '[{"x": 150, "y": 400, "width": 200, "height": 60, "image_id": "IMG-068"}]'::jsonb,
 TRUE);
```

---

### 5. book{N}_{name}_images

**Purpose:** Store extracted images with AI-generated descriptions

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_images (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Image Identification
    image_id                VARCHAR(50) NOT NULL UNIQUE,    -- e.g., "IMG-001", "IMG-068"
    page_number             INTEGER NOT NULL,               -- Source page

    -- Image Data
    image_data              BYTEA NOT NULL,                 -- Compressed image blob (LZ4)
    image_format            VARCHAR(20) NOT NULL,           -- PNG, JPEG, etc.
    original_width          INTEGER NOT NULL,               -- Original width (pixels)
    original_height         INTEGER NOT NULL,               -- Original height (pixels)
    stored_width            INTEGER NOT NULL,               -- Stored width (may be resized)
    stored_height           INTEGER NOT NULL,               -- Stored height
    file_size_bytes         INTEGER NOT NULL,               -- Compressed size

    -- Thumbnail
    thumbnail_data          BYTEA,                          -- 200x200 thumbnail (LZ4)
    thumbnail_size_bytes    INTEGER,

    -- Position Information
    position_x              INTEGER,                        -- X coordinate on page
    position_y              INTEGER,                        -- Y coordinate on page
    position_width          INTEGER,                        -- Bounding box width
    position_height         INTEGER,                        -- Bounding box height

    -- AI Analysis
    ai_description          TEXT NOT NULL,                  -- Human-readable description
    structured_json         JSONB,                          -- Structured data extraction
    image_type              VARCHAR(50),                    -- diagram, chart, photo, table, etc.
    confidence_score        NUMERIC(5,2) NOT NULL,          -- 0.00 to 100.00

    -- Metadata
    tags                    TEXT[],                         -- User-defined tags
    caption                 TEXT,                           -- Original caption (if detected)
    figure_number           VARCHAR(50),                    -- e.g., "Figure 5.3"

    -- Linked Knowledge Units
    linked_text_ids         INTEGER[],                      -- Array of knowledge_unit IDs

    -- Vector Embedding (for future image similarity)
    embedding               vector(512),                    -- Image embedding (CLIP model)

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_book1_img_page ON book1_ml_fundamentals_images(page_number);
CREATE INDEX idx_book1_img_type ON book1_ml_fundamentals_images(image_type);
CREATE INDEX idx_book1_img_confidence ON book1_ml_fundamentals_images(confidence_score);
CREATE INDEX idx_book1_img_id ON book1_ml_fundamentals_images(image_id);

-- GIN Index for array searches
CREATE INDEX idx_book1_img_tags ON book1_ml_fundamentals_images USING GIN(tags);
CREATE INDEX idx_book1_img_linked_ids ON book1_ml_fundamentals_images USING GIN(linked_text_ids);

-- Trigger
CREATE TRIGGER update_book1_img_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
INSERT INTO book1_ml_fundamentals_images
(image_id, page_number, image_data, image_format, original_width, original_height,
 stored_width, stored_height, file_size_bytes, ai_description, image_type, confidence_score)
VALUES
('IMG-068', 136, decode('89504e470d0a1a0a...', 'hex'), 'PNG', 1200, 800, 800, 600, 45678,
 'A flowchart diagram showing the machine learning pipeline from data collection to model deployment.',
 'diagram', 92.30);
```

---

### 6. book{N}_{name}_processing_state

**Purpose:** Track processing progress for pause/resume functionality

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_processing_state (
    -- Single Row Table (only 1 row per book)
    id                      INTEGER PRIMARY KEY DEFAULT 1,  -- Always 1
    CONSTRAINT single_row_check CHECK (id = 1),             -- Enforce single row

    -- Processing Progress
    status                  VARCHAR(50) NOT NULL DEFAULT 'not_started',
        -- Values: not_started, processing, paused, completed, error
    current_page            INTEGER NOT NULL DEFAULT 0,     -- Currently processing page
    total_pages             INTEGER NOT NULL,               -- Total pages in book
    progress_percentage     NUMERIC(5,2) DEFAULT 0.00,      -- (current/total)*100

    -- Checkpoint Information
    last_checkpoint_page    INTEGER DEFAULT 0,              -- Last saved checkpoint
    checkpoint_frequency    INTEGER DEFAULT 50,             -- Save checkpoint every N pages
    last_checkpoint_at      TIMESTAMP,

    -- Agent States (JSON)
    agent_states            JSONB,
        -- Format: {
        --   "reader": {"status": "idle", "current_page": 45},
        --   "splitter": {"status": "processing", "current_page": 44},
        --   "marker": {"status": "idle", "current_page": 44},
        --   "image_reader": {"status": "idle", "current_page": 44}
        -- }

    -- Processing Statistics
    pages_processed         INTEGER DEFAULT 0,
    knowledge_units_extracted INTEGER DEFAULT 0,
    images_extracted        INTEGER DEFAULT 0,
    ocr_retry_count         INTEGER DEFAULT 0,              -- Total OCR retries
    error_count             INTEGER DEFAULT 0,              -- Total errors encountered

    -- Performance Metrics
    avg_page_processing_time NUMERIC(10,2),                 -- Seconds per page
    estimated_time_remaining INTEGER,                       -- Seconds (calculated)

    -- Error Information
    last_error_message      TEXT,
    last_error_at           TIMESTAMP,

    -- Pause/Resume
    paused_at               TIMESTAMP,
    resumed_at              TIMESTAMP,
    pause_count             INTEGER DEFAULT 0,              -- Number of times paused

    -- Timestamps
    processing_started_at   TIMESTAMP,
    processing_completed_at TIMESTAMP,
    last_updated_at         TIMESTAMP DEFAULT NOW()
);

-- Insert single row on table creation
INSERT INTO book1_ml_fundamentals_processing_state (total_pages) VALUES (450);

-- Trigger
CREATE TRIGGER update_book1_state_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_processing_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
UPDATE book1_ml_fundamentals_processing_state
SET status = 'processing',
    current_page = 45,
    progress_percentage = 10.00,
    agent_states = '{"reader": {"status": "processing", "current_page": 45}}'::jsonb
WHERE id = 1;
```

---

### 7. book{N}_{name}_settings

**Purpose:** Store book-specific processing settings and instructions

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_settings (
    -- Single Row Table (only 1 row per book)
    id                      INTEGER PRIMARY KEY DEFAULT 1,
    CONSTRAINT single_row_check CHECK (id = 1),

    -- User Instructions
    special_instructions    TEXT,                           -- User-provided instructions

    -- Processing Settings
    language_setting        VARCHAR(50) DEFAULT 'auto',     -- auto, english, arabic, both
    extraction_sensitivity  VARCHAR(50) DEFAULT 'balanced', -- conservative, balanced, aggressive
    image_processing        VARCHAR(50) DEFAULT 'all',      -- all, diagrams_only, skip
    ocr_quality             VARCHAR(50) DEFAULT 'balanced', -- fast, balanced, high

    -- Hierarchy Settings
    hierarchy_detection     VARCHAR(50) DEFAULT 'auto',     -- auto, manual, skip
    auto_detect_chapters    BOOLEAN DEFAULT TRUE,
    auto_detect_topics      BOOLEAN DEFAULT TRUE,

    -- Partial Processing
    partial_processing_enabled BOOLEAN DEFAULT FALSE,       -- Process only first N pages?
    partial_processing_pages   INTEGER,                     -- How many pages (if enabled)

    -- Advanced OCR Settings
    ocr_retry_enabled       BOOLEAN DEFAULT TRUE,           -- Enable 3-attempt retry?
    ocr_retry_max_attempts  INTEGER DEFAULT 3,              -- Max OCR attempts
    ocr_zoom_factor         NUMERIC(3,2) DEFAULT 2.0,       -- Zoom for retry (e.g., 2.0 = 200%)

    -- Image Settings
    image_max_width         INTEGER DEFAULT 800,            -- Max stored image width
    image_max_height        INTEGER DEFAULT 600,            -- Max stored image height
    image_compression       VARCHAR(20) DEFAULT 'lz4',      -- lz4, none
    thumbnail_size          INTEGER DEFAULT 200,            -- Thumbnail size (square)

    -- Performance Settings
    checkpoint_frequency    INTEGER DEFAULT 50,             -- Save checkpoint every N pages
    batch_insert_size       INTEGER DEFAULT 50,             -- Insert N records at once

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Insert default settings on table creation
INSERT INTO book1_ml_fundamentals_settings (id) VALUES (1);

-- Trigger
CREATE TRIGGER update_book1_settings_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
UPDATE book1_ml_fundamentals_settings
SET special_instructions = 'Focus on extracting code examples and mathematical formulas.',
    language_setting = 'english',
    extraction_sensitivity = 'aggressive',
    partial_processing_enabled = TRUE,
    partial_processing_pages = 10
WHERE id = 1;
```

---

### 8. book{N}_{name}_hierarchy

**Purpose:** Store document structure (chapters, topics, sub-topics)

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_hierarchy (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Hierarchy Level
    level                   INTEGER NOT NULL,               -- 1=chapter, 2=topic, 3=sub_topic
    parent_id               INTEGER,                        -- Parent hierarchy ID (NULL for root)

    -- Hierarchy Data
    name                    VARCHAR(255) NOT NULL,          -- Chapter/Topic/Sub-topic name
    page_start              INTEGER NOT NULL,               -- First page of this section
    page_end                INTEGER,                        -- Last page (NULL if unknown)

    -- Metadata
    order_index             INTEGER NOT NULL,               -- Order within parent (1, 2, 3, ...)
    auto_detected           BOOLEAN DEFAULT TRUE,           -- Detected by AI or manual?

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    -- Foreign Key
    FOREIGN KEY (parent_id) REFERENCES book1_ml_fundamentals_hierarchy(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_book1_hierarchy_level ON book1_ml_fundamentals_hierarchy(level);
CREATE INDEX idx_book1_hierarchy_parent ON book1_ml_fundamentals_hierarchy(parent_id);
CREATE INDEX idx_book1_hierarchy_page_start ON book1_ml_fundamentals_hierarchy(page_start);

-- Trigger
CREATE TRIGGER update_book1_hierarchy_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_hierarchy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
-- Chapter 1
INSERT INTO book1_ml_fundamentals_hierarchy (level, parent_id, name, page_start, page_end, order_index)
VALUES (1, NULL, 'Chapter 1: Introduction to Machine Learning', 1, 50, 1);

-- Topic 1.1
INSERT INTO book1_ml_fundamentals_hierarchy (level, parent_id, name, page_start, page_end, order_index)
VALUES (2, 1, '1.1 What is Machine Learning?', 5, 15, 1);

-- Sub-topic 1.1.1
INSERT INTO book1_ml_fundamentals_hierarchy (level, parent_id, name, page_start, page_end, order_index)
VALUES (3, 2, '1.1.1 Supervised Learning', 6, 10, 1);
```

---

### 9. book{N}_{name}_attribute_keys

**Purpose:** Store book-level attribute key names (80 attributes, keys stored here, values in knowledge_units)

**Schema:**
```sql
CREATE TABLE book1_ml_fundamentals_attribute_keys (
    -- Primary Key
    id                      SERIAL PRIMARY KEY,

    -- Attribute Number (1-40)
    attr_number             INTEGER NOT NULL UNIQUE,        -- 1, 2, 3, ..., 40
    CONSTRAINT attr_number_range CHECK (attr_number BETWEEN 1 AND 40),

    -- Attribute Key Name
    key_name                VARCHAR(100) NOT NULL,          -- e.g., "related_image", "Difficulty Level"

    -- Metadata
    is_system_reserved      BOOLEAN DEFAULT FALSE,          -- TRUE for attributes 1-8 (system-reserved)
    is_editable             BOOLEAN DEFAULT TRUE,           -- FALSE for attributes 1-8
    description             TEXT,                           -- Optional description of attribute
    placeholder_example     VARCHAR(255),                   -- Example value

    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Insert 40 default attribute keys on table creation
INSERT INTO book1_ml_fundamentals_attribute_keys (attr_number, key_name, is_system_reserved, is_editable, description)
VALUES
-- System-Reserved Attributes (1-8)
(1, 'related_image', TRUE, FALSE, 'System-reserved: Links to related images (format: image_id:IMG-XX, page:XX, figure:X.X)'),
(2, 'ocr_text_paddleocr', TRUE, FALSE, 'System-reserved: OCR text result from PaddleOCR'),
(3, 'ocr_text_surya', TRUE, FALSE, 'System-reserved: OCR text result from Surya'),
(4, 'ocr_text_tesseract', TRUE, FALSE, 'System-reserved: OCR text result from Tesseract'),
(5, 'ocr_confidence_paddleocr', TRUE, FALSE, 'System-reserved: OCR confidence score from PaddleOCR'),
(6, 'ocr_confidence_surya', TRUE, FALSE, 'System-reserved: OCR confidence score from Surya'),
(7, 'ocr_confidence_tesseract', TRUE, FALSE, 'System-reserved: OCR confidence score from Tesseract'),
(8, 'record_status', TRUE, FALSE, 'System-reserved: Record status (enabled or disabled for merge/split tracking)'),

-- User-Defined Attributes (9-40) - 32 available
(9, 'Difficulty Level', FALSE, TRUE, 'Difficulty: Beginner, Intermediate, Advanced'),
(10, 'Topic Category', FALSE, TRUE, 'Category: Theory, Practice, Example, Exercise'),
(11, 'Importance', FALSE, TRUE, 'Importance: High, Medium, Low'),
(12, 'Keywords', FALSE, TRUE, 'Comma-separated keywords'),
(13, 'Author Opinion', FALSE, TRUE, 'Is this author opinion or fact?'),
(14, 'Code Example', FALSE, TRUE, 'Does this contain code? Yes/No'),
(15, 'Mathematical', FALSE, TRUE, 'Contains math formulas? Yes/No'),
(16, 'Prerequisite', FALSE, TRUE, 'Requires prior knowledge?'),
(17, 'Summary', FALSE, TRUE, 'Is this a summary section?'),
(18, '', FALSE, TRUE, 'Custom attribute 18'),
(19, '', FALSE, TRUE, 'Custom attribute 19'),
(20, '', FALSE, TRUE, 'Custom attribute 20'),
(21, '', FALSE, TRUE, 'Custom attribute 21'),
(22, '', FALSE, TRUE, 'Custom attribute 22'),
(23, '', FALSE, TRUE, 'Custom attribute 23'),
(24, '', FALSE, TRUE, 'Custom attribute 24'),
(25, '', FALSE, TRUE, 'Custom attribute 25'),
(26, '', FALSE, TRUE, 'Custom attribute 26'),
(27, '', FALSE, TRUE, 'Custom attribute 27'),
(28, '', FALSE, TRUE, 'Custom attribute 28'),
(29, '', FALSE, TRUE, 'Custom attribute 29'),
(30, '', FALSE, TRUE, 'Custom attribute 30'),
(31, '', FALSE, TRUE, 'Custom attribute 31'),
(32, '', FALSE, TRUE, 'Custom attribute 32'),
(33, '', FALSE, TRUE, 'Custom attribute 33'),
(34, '', FALSE, TRUE, 'Custom attribute 34'),
(35, '', FALSE, TRUE, 'Custom attribute 35'),
(36, '', FALSE, TRUE, 'Custom attribute 36'),
(37, '', FALSE, TRUE, 'Custom attribute 37'),
(38, '', FALSE, TRUE, 'Custom attribute 38'),
(39, '', FALSE, TRUE, 'Custom attribute 39'),
(40, '', FALSE, TRUE, 'Custom attribute 40');

-- Indexes
CREATE UNIQUE INDEX idx_book1_attr_keys_number ON book1_ml_fundamentals_attribute_keys(attr_number);

-- Trigger
CREATE TRIGGER update_book1_attr_keys_updated_at
    BEFORE UPDATE ON book1_ml_fundamentals_attribute_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Sample Data:**
```sql
-- User edits attribute 18 key name (user-defined attributes start at 9)
UPDATE book1_ml_fundamentals_attribute_keys
SET key_name = 'Source Reference', description = 'Citation or source reference'
WHERE attr_number = 18;

-- System-reserved attributes cannot be edited (constraint enforced in application)
-- This would fail in application logic:
-- UPDATE book1_ml_fundamentals_attribute_keys SET key_name = 'custom_name' WHERE attr_number = 8;
```

---

## 🔧 Database Functions & Triggers

### 1. Update Timestamp Trigger Function

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Usage:** Automatically update `updated_at` column on any UPDATE

---

### 2. Calculate Verified Percentage Function

```sql
CREATE OR REPLACE FUNCTION calculate_verified_percentage(p_book_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_table_prefix VARCHAR(100);
    v_total INTEGER;
    v_verified INTEGER;
    v_percentage NUMERIC(5,2);
BEGIN
    -- Get table prefix
    SELECT table_prefix INTO v_table_prefix
    FROM books_metadata WHERE book_id = p_book_id;

    -- Dynamic SQL to count records
    EXECUTE format('SELECT COUNT(*) FROM %I', v_table_prefix || '_knowledge_units')
    INTO v_total;

    EXECUTE format('SELECT COUNT(*) FROM %I WHERE verified = TRUE', v_table_prefix || '_knowledge_units')
    INTO v_verified;

    -- Calculate percentage
    IF v_total > 0 THEN
        v_percentage := (v_verified::NUMERIC / v_total::NUMERIC) * 100;
    ELSE
        v_percentage := 0;
    END IF;

    -- Update books_metadata
    UPDATE books_metadata
    SET verified_percentage = v_percentage,
        verified_units = v_verified,
        total_knowledge_units = v_total
    WHERE book_id = p_book_id;

    RETURN v_percentage;
END;
$$ LANGUAGE plpgsql;
```

**Usage:**
```sql
SELECT calculate_verified_percentage(1);  -- Returns 65.50 (percentage)
```

---

### 3. Create Book Tables Function

```sql
CREATE OR REPLACE FUNCTION create_book_tables(
    p_book_id INTEGER,
    p_sanitized_name VARCHAR(100),
    p_total_pages INTEGER
)
RETURNS VOID AS $$
DECLARE
    v_table_prefix VARCHAR(100);
BEGIN
    v_table_prefix := 'book' || p_book_id || '_' || p_sanitized_name;

    -- Create knowledge_units table
    EXECUTE format('
        CREATE TABLE %I (
            id SERIAL PRIMARY KEY,
            text_content TEXT NOT NULL,
            text_length INTEGER NOT NULL,
            line_count INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            position_x INTEGER,
            position_y INTEGER,
            position_width INTEGER,
            position_height INTEGER,
            language VARCHAR(50) NOT NULL,
            confidence_score NUMERIC(5,2) NOT NULL,
            extraction_method VARCHAR(50),
            chapter VARCHAR(255),
            topic VARCHAR(255),
            sub_topic VARCHAR(255),
            verified BOOLEAN DEFAULT FALSE,
            verified_at TIMESTAMP,
            verified_by VARCHAR(100),
            attr1_value TEXT, attr2_value TEXT, attr3_value TEXT, attr4_value TEXT, attr5_value TEXT,
            attr6_value TEXT, attr7_value TEXT, attr8_value TEXT DEFAULT ''enabled'', attr9_value TEXT, attr10_value TEXT,
            attr11_value TEXT, attr12_value TEXT, attr13_value TEXT, attr14_value TEXT, attr15_value TEXT,
            attr16_value TEXT, attr17_value TEXT, attr18_value TEXT, attr19_value TEXT, attr20_value TEXT,
            attr21_value TEXT, attr22_value TEXT, attr23_value TEXT, attr24_value TEXT, attr25_value TEXT,
            attr26_value TEXT, attr27_value TEXT, attr28_value TEXT, attr29_value TEXT, attr30_value TEXT,
            attr31_value TEXT, attr32_value TEXT, attr33_value TEXT, attr34_value TEXT, attr35_value TEXT,
            attr36_value TEXT, attr37_value TEXT, attr38_value TEXT, attr39_value TEXT, attr40_value TEXT,
            merged_into_record_id INTEGER,
            original_record_ids TEXT[],
            notes TEXT,
            tags TEXT[],
            linked_image_ids TEXT[],
            embedding vector(384),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )', v_table_prefix || '_knowledge_units');

    -- Create indexes for knowledge_units
    EXECUTE format('CREATE INDEX %I ON %I(page_number)',
        'idx_' || v_table_prefix || '_ku_page', v_table_prefix || '_knowledge_units');
    EXECUTE format('CREATE INDEX %I ON %I(verified)',
        'idx_' || v_table_prefix || '_ku_verified', v_table_prefix || '_knowledge_units');
    EXECUTE format('CREATE INDEX %I ON %I(attr8_value)',
        'idx_' || v_table_prefix || '_ku_record_status', v_table_prefix || '_knowledge_units');
    EXECUTE format('CREATE INDEX %I ON %I(merged_into_record_id)',
        'idx_' || v_table_prefix || '_ku_merged_into', v_table_prefix || '_knowledge_units');

    -- Create images table (similar structure as above)
    -- Create pages table
    -- Create processing_state table
    -- Create settings table
    -- Create hierarchy table
    -- Create attribute_keys table

    -- (Full implementation in actual deployment script)
END;
$$ LANGUAGE plpgsql;
```

**Usage:**
```sql
SELECT create_book_tables(1, 'ml_fundamentals', 450);
```

---

## 🔍 Indexes Summary

### Purpose of Indexes
- **Performance:** Speed up queries on frequently accessed columns
- **Foreign Keys:** Improve join performance
- **Filtering:** Optimize WHERE clauses
- **Sorting:** Speed up ORDER BY operations

### Index Strategy

1. **Primary Keys:** Automatic B-tree index
2. **Page Numbers:** Indexed on all tables (frequent filtering)
3. **Status Fields:** Indexed for dashboard queries
4. **Verification:** Indexed for filtering unverified records
5. **Arrays:** GIN indexes for tag/array searches
6. **Vectors:** IVFFlat indexes for similarity search

---

## 📊 Storage Estimates

### Per Book (500-page book)

| Component | Estimated Size |
|-----------|---------------|
| **Raw Data Tables** | |
| **raw_pages** (compressed) | 500 pages × 100KB = 50 MB |
| **raw_knowledge_units** | 1,500 records (3 OCR engines × 500 pages) × 2KB = 3 MB |
| **Processed Data Tables** | |
| **knowledge_units** | ~5,000 records × 3.5KB = 17.5 MB (80 attributes + merge tracking) |
| **pages** (rectangles only) | 500 pages × 5KB = 2.5 MB (JSONB rectangles, no images) |
| **images** (compressed) | ~200 images × 50KB = 10 MB |
| **processing_state** | 1 row = 5 KB |
| **settings** | 1 row = 3 KB |
| **hierarchy** | ~50 records × 500B = 25 KB |
| **attribute_keys** | 40 rows = 20 KB |
| **Total per book** | **~78 MB** |

### Database Growth

- 10 books: ~780 MB
- 50 books: ~3.9 GB
- 100 books: ~7.8 GB

**Recommendation:** Plan for at least 50 GB database storage for future growth.

**Storage Benefits:**
- Page images stored **once** in raw_pages (referenced by both raw_knowledge_units and pages)
- Can re-split records without re-running OCR (raw data preserved)
- Merge/split operations minimal storage impact (disabled records have empty text_content)

---

## 🔐 Database Security

### User Roles

```sql
-- Admin user (application use)
CREATE USER knowledge_app WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE knowledge_extraction TO knowledge_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO knowledge_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO knowledge_app;

-- Read-only user (for reporting/analysis)
CREATE USER knowledge_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE knowledge_extraction TO knowledge_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO knowledge_readonly;
```

### Connection String

```python
# Configuration for SQLAlchemy
DATABASE_URL = "postgresql://knowledge_app:secure_password_here@db-server-ip:5432/knowledge_extraction"
```

---

## 🚀 Initialization Script

### Complete Setup (PostgreSQL)

```sql
-- 1. Create database
CREATE DATABASE knowledge_extraction
    WITH ENCODING 'UTF8'
    LC_COLLATE='en_US.UTF-8'
    LC_CTYPE='en_US.UTF-8'
    TEMPLATE=template0;

-- 2. Connect to database
\c knowledge_extraction

-- 3. Enable extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search

-- 4. Create trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Create shared books_metadata table
CREATE TABLE books_metadata ( ... );  -- Full schema above

-- 6. Create helper functions
CREATE OR REPLACE FUNCTION create_book_tables(...) ...;  -- Full function above
CREATE OR REPLACE FUNCTION calculate_verified_percentage(...) ...;  -- Full function above

-- 7. Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO knowledge_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO knowledge_app;
```

---

## 📦 Chroma Vector Database Schema

**Purpose:** Unified cross-book vector database for advanced semantic search across all text and images

### Architecture Overview

The system uses **dual storage** for embeddings:

1. **PostgreSQL with pgvector:** Primary database for structured data + basic vector search
2. **Chroma DB:** Specialized vector database for advanced semantic search and cross-book queries

### Why Dual Storage?

| Feature | PostgreSQL + pgvector | Chroma DB |
|---------|---------------------|-----------|
| **Primary Use** | Structured relational data + basic vector search | Advanced semantic search across ALL books |
| **Storage** | Full knowledge unit records with 80 attributes | Embeddings + minimal metadata only |
| **Search Type** | Single-book similarity, exact matches | Cross-book semantic search, clustering |
| **Performance** | Optimized for CRUD operations | Optimized for vector similarity |
| **Query Patterns** | SQL joins, filtering, aggregation | Nearest neighbor search, semantic similarity |
| **Embedding Storage** | 384-dim vectors in `vector(384)` column | 384-dim vectors in Chroma collections |
| **Index Type** | HNSW or IVFFlat indexes | Chroma's native HNSW indexes |
| **Collection Strategy** | One table per book | **Single unified collection for ALL books** |

### Unified Collection Strategy

**Collection Name:** `knowledge_base_unified`

All books, all text, and all images are stored in a **single Chroma collection** for:
- Cross-book semantic search
- Unified query interface
- Simpler architecture
- Better performance for multi-book queries

### Chroma DB Record Structure

Every Chroma record has **4 components**:

```python
collection.add(
    ids=["..."],           # 1. UNIQUE IDENTIFIER
    documents=["..."],     # 2. ORIGINAL TEXT (what gets embedded)
    embeddings=[[...]],    # 3. VECTOR EMBEDDING (computed from document)
    metadatas=[{...}]      # 4. METADATA (searchable attributes)
)
```

#### Component Breakdown

| Component | Purpose | Example | Embedded? |
|-----------|---------|---------|-----------|
| **ID** | Unique identifier | `"book1_text_487"` or `"book1_image_68"` | No |
| **DOCUMENT** | Text to be semantically searched | Full text or AI description | **YES** |
| **EMBEDDING** | 384-dim vector | `[0.123, -0.456, ..., 0.234]` | N/A |
| **METADATA** | Structured filters and display info | `{"verified": true, "chapter": "..."}` | No |

**KEY DISTINCTION:**
- **DOCUMENT** = The actual content that gets embedded and semantically searched
- **METADATA** = Structured attributes for filtering and display (NOT embedded)

### What Gets Stored as DOCUMENT vs METADATA

#### For Text Records (from `knowledge_units` table):

**DOCUMENT (Main Record - Gets Embedded):**
```python
document = "Each connection has a weight that adjusts during training through backpropagation to minimize prediction errors. The learning rate controls how quickly the network learns from mistakes."
# Full text from knowledge_units.text column (500+ characters)
```

**METADATA (Structured Attributes - NOT Embedded):**
```python
metadata = {
    # Critical fields
    "record_status": "enabled",          # MUST filter out "disabled" records
    "entity_type": "text",               # Distinguish text vs image
    "table_name": "book1_ml_fundamentals_knowledge_units",
    "postgresql_id": 487,                # FK to PostgreSQL
    "text_preview": "Each connection has a weight that adjusts...",  # First 200 chars

    # Search enablement
    "page_number": 142,
    "chapter": "Chapter 5: Neural Networks",
    "topic": "Backpropagation",
    "sub_topic": "Gradient Descent",
    "verified": True,
    "language": "english",
    "tags": ["neural-networks", "backpropagation"],

    # Cross-entity linking
    "has_images": False,
    "linked_image_ids": [],

    # Book identification
    "book_id": 1,
    "book_name": "ML Fundamentals"
}
```

#### For Image Records (from `images` table):

**DOCUMENT (Main Record - Gets Embedded):**
```python
document = "A neural network architecture diagram showing three layers: input layer with 3 nodes, hidden layer with 4 nodes, and output layer with 2 nodes. Connections show weighted edges between all nodes in adjacent layers. Activation functions are applied at each hidden and output node."
# Full AI description from images.ai_description column
```

**METADATA (Structured Attributes - NOT Embedded):**
```python
metadata = {
    # Critical fields
    "entity_type": "image",
    "table_name": "book1_ml_fundamentals_images",
    "postgresql_id": 68,
    "ai_description_preview": "A neural network architecture diagram showing three layers...",  # First 200 chars

    # Image-specific
    "image_id": "IMG-068",
    "image_type": "diagram",             # diagram, chart, table, equation, photo
    "figure_number": "Figure 5.3",
    "caption": "Three-layer feedforward neural network",

    # Search enablement
    "page_number": 136,
    "chapter": "Chapter 5: Neural Networks",
    "topic": "Network Architecture",
    "verified": True,
    "language": "english",
    "tags": ["neural-network", "architecture", "diagram"],

    # Cross-entity linking
    "has_text_links": True,
    "linked_text_ids": ["book1_text_456", "book1_text_487"],

    # Book identification
    "book_id": 1,
    "book_name": "ML Fundamentals"
}
```

### Complete Metadata Field Specification

#### Critical Metadata Fields (Required)

| Field | Type | Purpose | Text | Image |
|-------|------|---------|------|-------|
| **record_status** | string | Filter out disabled/merged records | ✅ | ❌ |
| **entity_type** | string | Distinguish "text" vs "image" | ✅ | ✅ |
| **table_name** | string | PostgreSQL table to fetch full record | ✅ | ✅ |
| **postgresql_id** | integer | Primary key in PostgreSQL table | ✅ | ✅ |
| **text_preview** / **ai_description_preview** | string | First 200 chars for quick display | ✅ | ✅ |

#### Search Enablement Metadata

| Field | Type | Purpose | Text | Image |
|-------|------|---------|------|-------|
| **page_number** | integer | Filter by page range | ✅ | ✅ |
| **chapter** | string | Hierarchical filtering | ✅ | ✅ |
| **topic** | string | Topic filtering | ✅ | ✅ |
| **sub_topic** | string | Sub-topic filtering | ✅ | ✅ |
| **verified** | boolean | Filter verified content only | ✅ | ✅ |
| **language** | string | Multi-language filtering | ✅ | ✅ |
| **image_type** | string | Filter diagrams, charts, tables | ❌ | ✅ |
| **tags** | array | Flexible tag-based filtering | ✅ | ✅ |

#### Cross-Entity Linking Metadata

| Field | Type | Purpose | Text | Image |
|-------|------|---------|------|-------|
| **has_images** | boolean | Does text reference images? | ✅ | ❌ |
| **linked_image_ids** | array | Which images does text reference? | ✅ | ❌ |
| **has_text_links** | boolean | Is image referenced by text? | ❌ | ✅ |
| **linked_text_ids** | array | Which text units reference image? | ❌ | ✅ |

#### Book Identification Metadata

| Field | Type | Purpose | Text | Image |
|-------|------|---------|------|-------|
| **book_id** | integer | Numeric book identifier | ✅ | ✅ |
| **book_name** | string | Human-readable book name | ✅ | ✅ |

### Unified Collection Schema

#### Collection: `knowledge_base_unified`

**Single collection containing ALL books, ALL text, and ALL images.**

**ID Format:**
- Text records: `book{N}_text_{postgresql_id}` (e.g., `"book1_text_487"`)
- Image records: `book{N}_image_{postgresql_id}` (e.g., `"book1_image_68"`)

**Document Content:**
- Text records: Full text from `knowledge_units.text` column
- Image records: Full AI description from `images.ai_description` column

**Metadata Fields:** See "Complete Metadata Field Specification" section above (14 fields total)

### Dual Storage Synchronization Strategy

#### When Data is Synced to Both Databases

Data is stored in BOTH PostgreSQL and Chroma DB when:

1. **New knowledge unit created** (after OCR split) → Sync text to Chroma
2. **Knowledge unit text updated** (user edits verified text) → Update Chroma
3. **Knowledge unit verified** (user confirms OCR accuracy) → Update Chroma metadata
4. **New image processed** (AI description generated) → Sync image to Chroma
5. **Image AI description updated** → Update Chroma

#### Synchronization Workflow for Text

```python
# Pseudo-code for text record sync
def save_text_to_chroma(text, book_id, book_name, table_name, metadata):
    # 1. SAVE TO POSTGRESQL (Primary storage - already done)
    pg_id = metadata['postgresql_id']

    # 2. GENERATE EMBEDDING
    embedding = generate_embedding(text)  # MiniLM 384-dim

    # 3. SAVE TO CHROMA DB (Unified collection)
    collection = chroma_client.get_collection("knowledge_base_unified")
    collection.add(
        ids=[f"book{book_id}_text_{pg_id}"],
        documents=[text],  # FULL TEXT (gets embedded)
        metadatas=[{
            # Critical fields
            "record_status": metadata.get("record_status", "enabled"),
            "entity_type": "text",
            "table_name": table_name,
            "postgresql_id": pg_id,
            "text_preview": text[:200],

            # Search enablement
            "page_number": metadata["page_number"],
            "chapter": metadata.get("chapter"),
            "topic": metadata.get("topic"),
            "sub_topic": metadata.get("sub_topic"),
            "verified": metadata.get("verified", False),
            "language": metadata.get("language", "english"),
            "tags": metadata.get("tags", []),

            # Cross-entity linking
            "has_images": metadata.get("has_images", False),
            "linked_image_ids": metadata.get("linked_image_ids", []),

            # Book identification
            "book_id": book_id,
            "book_name": book_name
        }]
    )
```

#### Synchronization Workflow for Images

```python
# Pseudo-code for image record sync
def save_image_to_chroma(ai_description, book_id, book_name, table_name, metadata):
    # 1. SAVE TO POSTGRESQL (Primary storage - already done)
    pg_id = metadata['postgresql_id']

    # 2. GENERATE EMBEDDING
    embedding = generate_embedding(ai_description)  # MiniLM 384-dim

    # 3. SAVE TO CHROMA DB (Unified collection)
    collection = chroma_client.get_collection("knowledge_base_unified")
    collection.add(
        ids=[f"book{book_id}_image_{pg_id}"],
        documents=[ai_description],  # FULL AI DESCRIPTION (gets embedded)
        metadatas=[{
            # Critical fields
            "entity_type": "image",
            "table_name": table_name,
            "postgresql_id": pg_id,
            "ai_description_preview": ai_description[:200],

            # Image-specific
            "image_id": metadata["image_id"],
            "image_type": metadata.get("image_type"),
            "figure_number": metadata.get("figure_number"),
            "caption": metadata.get("caption"),

            # Search enablement
            "page_number": metadata["page_number"],
            "chapter": metadata.get("chapter"),
            "topic": metadata.get("topic"),
            "verified": metadata.get("verified", False),
            "language": metadata.get("language", "english"),
            "tags": metadata.get("tags", []),

            # Cross-entity linking
            "has_text_links": metadata.get("has_text_links", False),
            "linked_text_ids": metadata.get("linked_text_ids", []),

            # Book identification
            "book_id": book_id,
            "book_name": book_name
        }]
    )
```

#### Update Synchronization

```python
def update_record_in_chroma(chroma_id, new_document, updated_metadata):
    collection = chroma_client.get_collection("knowledge_base_unified")

    # Generate new embedding
    new_embedding = generate_embedding(new_document)

    # Update in Chroma
    collection.update(
        ids=[chroma_id],
        documents=[new_document],
        embeddings=[new_embedding],
        metadatas=[updated_metadata]
    )
```

#### Merge Synchronization

```python
def merge_knowledge_units(source_ids, merged_text, book_id):
    """
    Merge multiple knowledge units into one.
    Source records are disabled, new merged record is created.

    IMPORTANT: Merged text is NEW text (combination of sources),
    so it requires a NEW EMBEDDING (not reusing any source embedding).
    """
    # 1. CREATE MERGED RECORD IN POSTGRESQL
    merged_id = postgresql.execute("""
        INSERT INTO book{book_id}_{name}_knowledge_units
        (text, page_number, chapter, topic, original_record_ids, ...)
        VALUES (%s, %s, %s, %s, %s, ...)
        RETURNING id
    """, [merged_text, page_number, chapter, topic, source_ids, ...])

    # 2. DISABLE SOURCE RECORDS IN POSTGRESQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET attr8_value = 'disabled',
            merged_into_record_id = %s
        WHERE id = ANY(%s)
    """, [merged_id, source_ids])

    # 3. ADD TO SYNC QUEUE: Create merged record (generates NEW embedding)
    sync_queue.add({
        'action': 'create',  # 'create' triggers fresh embedding generation
        'entity_type': 'text',
        'book_id': book_id,
        'postgresql_id': merged_id,
        'document': merged_text,  # NEW merged text → NEW embedding
        'metadata': {...}
    })

    # 4. ADD TO SYNC QUEUE: Delete source records from Chroma
    for source_id in source_ids:
        sync_queue.add({
            'action': 'delete',
            'entity_type': 'text',
            'book_id': book_id,
            'postgresql_id': source_id
        })
```

#### Split Synchronization

```python
def split_knowledge_unit(original_id, split_texts, book_id):
    """
    Split one knowledge unit into multiple.
    Original record is disabled, new split records are created.

    IMPORTANT: Each split text is NEW text (portion of original),
    so each requires a NEW EMBEDDING (not reusing original embedding).
    """
    split_ids = []

    # 1. CREATE SPLIT RECORDS IN POSTGRESQL
    for split_text in split_texts:
        split_id = postgresql.execute("""
            INSERT INTO book{book_id}_{name}_knowledge_units
            (text, page_number, chapter, topic, original_record_ids, ...)
            VALUES (%s, %s, %s, %s, %s, ...)
            RETURNING id
        """, [split_text, page_number, chapter, topic, [original_id], ...])
        split_ids.append(split_id)

    # 2. DISABLE ORIGINAL RECORD IN POSTGRESQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET attr8_value = 'disabled',
            merged_into_record_id = %s  -- Points to first split record
        WHERE id = %s
    """, [split_ids[0], original_id])

    # 3. ADD TO SYNC QUEUE: Create split records (each generates NEW embedding)
    for i, split_id in enumerate(split_ids):
        sync_queue.add({
            'action': 'create',  # 'create' triggers fresh embedding generation
            'entity_type': 'text',
            'book_id': book_id,
            'postgresql_id': split_id,
            'document': split_texts[i],  # NEW split text → NEW embedding
            'metadata': {...}
        })

    # 4. ADD TO SYNC QUEUE: Delete original record from Chroma
    sync_queue.add({
        'action': 'delete',
        'entity_type': 'text',
        'book_id': book_id,
        'postgresql_id': original_id
    })
```

#### Metadata Update Synchronization

```python
def update_metadata_only(ku_id, book_id, updated_fields):
    """
    Update metadata fields that are stored in Chroma (chapter, topic, verified, tags, etc.)
    NO text change, so no re-embedding needed.
    """
    # 1. UPDATE POSTGRESQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET chapter = %s, topic = %s, sub_topic = %s,
            verified = %s, tags = %s, updated_at = NOW()
        WHERE id = %s
    """, [chapter, topic, sub_topic, verified, tags, ku_id])

    # 2. ADD TO SYNC QUEUE: Update metadata only
    sync_queue.add({
        'action': 'update_metadata',
        'entity_type': 'text',
        'book_id': book_id,
        'postgresql_id': ku_id,
        'metadata_updates': {
            'chapter': chapter,
            'topic': topic,
            'sub_topic': sub_topic,
            'verified': verified,
            'tags': tags
        }
    })
```

#### Delete Synchronization (Disabled Records)

```python
def disable_text_record(book_id, ku_id):
    """
    Soft delete in PostgreSQL, hard delete in Chroma.
    Used when record is permanently disabled (not merged/split).
    """
    # 1. UPDATE POSTGRESQL (soft delete via record_status)
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET attr8_value = 'disabled'  -- record_status
        WHERE id = %s
    """, [ku_id])

    # 2. ADD TO SYNC QUEUE: Delete from Chroma
    sync_queue.add({
        'action': 'delete',
        'entity_type': 'text',
        'book_id': book_id,
        'postgresql_id': ku_id
    })
```

### Async Queue Sync Strategy (Recommended)

#### Complete Sync Triggers

Data is synced to Chroma DB in these scenarios:

| Trigger | PostgreSQL Action | Chroma Action | Queue Event | Re-embed? |
|---------|------------------|---------------|-------------|-----------|
| **New knowledge unit created** | INSERT text | ADD document + metadata | `'create'` | ✅ Yes |
| **Text content updated** | UPDATE text | UPDATE document + re-embed | `'update'` | ✅ Yes |
| **Metadata updated** | UPDATE chapter/topic/tags | UPDATE metadata only | `'update_metadata'` | ❌ No |
| **Record verified** | UPDATE verified=true | UPDATE metadata (verified) | `'update_metadata'` | ❌ No |
| **Record merged** | INSERT merged + disable sources | ADD merged (NEW embedding) + DELETE sources | `'create'` + N×`'delete'` | ✅ Yes (merged text) |
| **Record split** | INSERT splits + disable original | ADD splits (NEW embeddings) + DELETE original | N×`'create'` + `'delete'` | ✅ Yes (each split) |
| **Record disabled** | UPDATE record_status='disabled' | DELETE from collection | `'delete'` | N/A |
| **New image processed** | INSERT image | ADD document + metadata | `'create'` | ✅ Yes |
| **AI description updated** | UPDATE ai_description | UPDATE document + re-embed | `'update'` | ✅ Yes |
| **Image metadata updated** | UPDATE image_type/tags/caption | UPDATE metadata only | `'update_metadata'` | ❌ No |

#### Queue Implementation

```python
import asyncio
from queue import Queue
from typing import Dict, Any
import logging

# Initialize sync queue
sync_queue = Queue()

# Sync event structure
class SyncEvent:
    def __init__(self, action: str, entity_type: str, book_id: int,
                 postgresql_id: int, **kwargs):
        self.action = action  # 'create', 'update', 'update_metadata', 'delete'
        self.entity_type = entity_type  # 'text' or 'image'
        self.book_id = book_id
        self.postgresql_id = postgresql_id
        self.document = kwargs.get('document')  # For create/update
        self.metadata = kwargs.get('metadata')  # For create
        self.metadata_updates = kwargs.get('metadata_updates')  # For update_metadata
        self.timestamp = datetime.now()

# Background worker - runs continuously
async def chroma_sync_worker():
    """
    Background worker that processes sync queue.
    Runs in separate thread/process.
    """
    collection = chroma_client.get_collection("knowledge_base_unified")

    while True:
        try:
            # Get event from queue (blocking)
            event = sync_queue.get(timeout=1)

            chroma_id = f"book{event.book_id}_{event.entity_type}_{event.postgresql_id}"

            if event.action == 'create':
                # Add new record to Chroma
                collection.add(
                    ids=[chroma_id],
                    documents=[event.document],
                    metadatas=[event.metadata]
                )
                logging.info(f"✓ Created {chroma_id} in Chroma")

            elif event.action == 'update':
                # Update document (re-embedding required)
                new_embedding = generate_embedding(event.document)
                collection.update(
                    ids=[chroma_id],
                    documents=[event.document],
                    embeddings=[new_embedding],
                    metadatas=[event.metadata]
                )
                logging.info(f"✓ Updated {chroma_id} in Chroma (re-embedded)")

            elif event.action == 'update_metadata':
                # Update metadata only (no re-embedding)
                # Fetch existing record to preserve other metadata
                existing = collection.get(ids=[chroma_id])

                if existing and len(existing['metadatas']) > 0:
                    # Merge existing metadata with updates
                    updated_metadata = {**existing['metadatas'][0], **event.metadata_updates}

                    collection.update(
                        ids=[chroma_id],
                        metadatas=[updated_metadata]
                    )
                    logging.info(f"✓ Updated metadata for {chroma_id} in Chroma")
                else:
                    logging.warning(f"⚠ Record {chroma_id} not found in Chroma for metadata update")

            elif event.action == 'delete':
                # Delete from Chroma
                collection.delete(ids=[chroma_id])
                logging.info(f"✓ Deleted {chroma_id} from Chroma")

            # Mark task as done
            sync_queue.task_done()

        except queue.Empty:
            # No events in queue, continue waiting
            await asyncio.sleep(0.1)

        except Exception as e:
            # Log error and add to failed sync log for daily reconciliation
            logging.error(f"✗ Chroma sync failed for {chroma_id}: {e}")
            log_failed_sync(event, str(e))
            sync_queue.task_done()

# Helper: Add event to queue
def queue_chroma_sync(action: str, entity_type: str, book_id: int,
                      postgresql_id: int, **kwargs):
    """
    Add sync event to queue (non-blocking).
    Called after every PostgreSQL write.
    """
    event = SyncEvent(
        action=action,
        entity_type=entity_type,
        book_id=book_id,
        postgresql_id=postgresql_id,
        **kwargs
    )
    sync_queue.put(event)
    logging.debug(f"→ Queued {action} for book{book_id}_{entity_type}_{postgresql_id}")

# Start worker on application startup
def start_sync_worker():
    """
    Start background worker thread.
    Call this when application starts.
    """
    worker_thread = threading.Thread(target=asyncio.run, args=(chroma_sync_worker(),), daemon=True)
    worker_thread.start()
    logging.info("🚀 Chroma sync worker started")
```

#### Usage Examples

**Example 1: Create New Knowledge Unit**
```python
def create_knowledge_unit(text, book_id, metadata):
    # 1. Save to PostgreSQL
    pg_id = postgresql.execute("""
        INSERT INTO book{book_id}_{name}_knowledge_units
        (text, page_number, chapter, verified, ...)
        VALUES (%s, %s, %s, %s, ...)
        RETURNING id
    """, [text, metadata['page_number'], metadata['chapter'], False, ...])

    # 2. Queue sync to Chroma (non-blocking)
    queue_chroma_sync(
        action='create',
        entity_type='text',
        book_id=book_id,
        postgresql_id=pg_id,
        document=text,
        metadata={
            'record_status': 'enabled',
            'entity_type': 'text',
            'table_name': f'book{book_id}_{name}_knowledge_units',
            'postgresql_id': pg_id,
            'text_preview': text[:200],
            'page_number': metadata['page_number'],
            'chapter': metadata['chapter'],
            'verified': False,
            'book_id': book_id,
            'book_name': metadata['book_name'],
            # ... other metadata fields
        }
    )

    return pg_id  # Returns immediately, sync happens in background
```

**Example 2: User Edits Text (Re-embedding Required)**
```python
def update_knowledge_unit_text(ku_id, new_text, book_id, metadata):
    # 1. Update PostgreSQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET text = %s, updated_at = NOW()
        WHERE id = %s
    """, [new_text, ku_id])

    # 2. Queue sync to Chroma (re-embedding)
    queue_chroma_sync(
        action='update',
        entity_type='text',
        book_id=book_id,
        postgresql_id=ku_id,
        document=new_text,
        metadata={
            'text_preview': new_text[:200],
            'verified': True,  # Usually verified after edit
            # ... full metadata
        }
    )
```

**Example 3: User Updates Chapter (Metadata Only)**
```python
def update_chapter_assignment(ku_id, book_id, new_chapter, new_topic):
    # 1. Update PostgreSQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET chapter = %s, topic = %s, updated_at = NOW()
        WHERE id = %s
    """, [new_chapter, new_topic, ku_id])

    # 2. Queue metadata update to Chroma (no re-embedding)
    queue_chroma_sync(
        action='update_metadata',
        entity_type='text',
        book_id=book_id,
        postgresql_id=ku_id,
        metadata_updates={
            'chapter': new_chapter,
            'topic': new_topic
        }
    )
```

**Example 4: User Adds Tags (Metadata Only)**
```python
def add_tags(ku_id, book_id, new_tags):
    # 1. Update PostgreSQL
    postgresql.execute("""
        UPDATE book{book_id}_{name}_knowledge_units
        SET tags = %s, updated_at = NOW()
        WHERE id = %s
    """, [new_tags, ku_id])

    # 2. Queue metadata update
    queue_chroma_sync(
        action='update_metadata',
        entity_type='text',
        book_id=book_id,
        postgresql_id=ku_id,
        metadata_updates={'tags': new_tags}
    )
```

### Operations and Usage

#### Initialization

```python
import chromadb
from chromadb.config import Settings

# Initialize persistent Chroma client
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="/data/chroma_db"
))

# Create unified collection (ONE collection for ALL books)
collection = client.get_or_create_collection(
    name="knowledge_base_unified",
    metadata={
        "description": "Unified collection for all books, text, and images",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384
    }
)
```

#### Bulk Sync: Text Records

```python
def sync_book_text_to_chroma(book_id, book_name, table_name):
    """Sync all text records from one book to Chroma"""
    collection = chroma_client.get_collection("knowledge_base_unified")

    # Fetch from PostgreSQL
    rows = postgresql.execute(f"""
        SELECT id, text, page_number, chapter, topic, sub_topic,
               verified, language, tags, attr8_value
        FROM {table_name}
        WHERE attr8_value = 'enabled'  -- Only active records
    """)

    # Prepare for Chroma
    ids = [f"book{book_id}_text_{row.id}" for row in rows]
    documents = [row.text for row in rows]  # Full text (gets embedded)
    metadatas = [{
        "record_status": row.attr8_value,
        "entity_type": "text",
        "table_name": table_name,
        "postgresql_id": row.id,
        "text_preview": row.text[:200],
        "page_number": row.page_number,
        "chapter": row.chapter,
        "topic": row.topic,
        "sub_topic": row.sub_topic,
        "verified": row.verified,
        "language": row.language,
        "tags": row.tags or [],
        "has_images": False,  # Update based on linked_image_ids
        "linked_image_ids": [],
        "book_id": book_id,
        "book_name": book_name
    } for row in rows]

    # Bulk insert to Chroma (Chroma auto-generates embeddings from documents)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
```

#### Bulk Sync: Image Records

```python
def sync_book_images_to_chroma(book_id, book_name, table_name):
    """Sync all image records from one book to Chroma"""
    collection = chroma_client.get_collection("knowledge_base_unified")

    # Fetch from PostgreSQL
    rows = postgresql.execute(f"""
        SELECT id, ai_description, image_id, image_type, figure_number, caption,
               page_number, chapter, topic, verified, language, tags, linked_text_ids
        FROM {table_name}
        WHERE ai_description IS NOT NULL  -- Only images with AI descriptions
    """)

    # Prepare for Chroma
    ids = [f"book{book_id}_image_{row.id}" for row in rows]
    documents = [row.ai_description for row in rows]  # Full AI description (gets embedded)
    metadatas = [{
        "entity_type": "image",
        "table_name": table_name,
        "postgresql_id": row.id,
        "ai_description_preview": row.ai_description[:200],
        "image_id": row.image_id,
        "image_type": row.image_type,
        "figure_number": row.figure_number,
        "caption": row.caption,
        "page_number": row.page_number,
        "chapter": row.chapter,
        "topic": row.topic,
        "verified": row.verified,
        "language": row.language,
        "tags": row.tags or [],
        "has_text_links": bool(row.linked_text_ids),
        "linked_text_ids": row.linked_text_ids or [],
        "book_id": book_id,
        "book_name": book_name
    } for row in rows]

    # Bulk insert to Chroma
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
```

#### Query Examples

**Example 1: Cross-Book Semantic Search (Text Only)**
```python
collection = chroma_client.get_collection("knowledge_base_unified")

results = collection.query(
    query_texts=["explain backpropagation algorithm"],
    n_results=10,
    where={
        "entity_type": "text",
        "verified": True,
        "record_status": "enabled"  # CRITICAL: Filter out disabled records
    }
)

# Display results (no PostgreSQL fetch needed!)
for i, metadata in enumerate(results['metadatas'][0]):
    print(f"{i+1}. [{metadata['book_name']}] {metadata['text_preview']}...")
```

**Example 2: Find Diagrams Across All Books**
```python
results = collection.query(
    query_texts=["neural network architecture diagram"],
    n_results=10,
    where={
        "entity_type": "image",
        "image_type": "diagram",
        "verified": True
    }
)

# Display image results
for metadata in results['metadatas'][0]:
    print(f"[{metadata['book_name']}] Figure {metadata['figure_number']}: {metadata['ai_description_preview']}...")
```

**Example 3: Unified Search (Text + Images)**
```python
# Search both text and images about "gradient descent"
results = collection.query(
    query_texts=["gradient descent optimization"],
    n_results=20,
    where={
        "verified": True,
        "$or": [
            {"entity_type": "text", "record_status": "enabled"},
            {"entity_type": "image"}
        ]
    }
)

# Results include both text snippets and image descriptions
for metadata in results['metadatas'][0]:
    if metadata['entity_type'] == 'text':
        print(f"[TEXT] {metadata['text_preview']}...")
    else:
        print(f"[IMAGE] {metadata['ai_description_preview']}...")
```

**Example 4: Filter by Chapter + Page Range**
```python
results = collection.query(
    query_texts=["convolutional layers"],
    n_results=5,
    where={
        "book_id": 1,
        "chapter": {"$contains": "Chapter 5"},
        "page_number": {"$gte": 100, "$lte": 150}
    }
)
```

### Data Consistency Guarantees

1. **PostgreSQL is Source of Truth:** Chroma DB is a read-optimized replica for vector search
2. **Eventual Consistency:** Chroma updates happen asynchronously after PostgreSQL commits (via queue)
3. **Async Queue:** Non-blocking sync ensures user operations return immediately (no waiting for Chroma)
4. **Reconciliation:** Daily job compares PostgreSQL and Chroma, syncs missing/stale records
5. **Failure Handling:** If Chroma write fails, PostgreSQL transaction still commits (logged for retry)
6. **Metadata Sync:** Metadata changes (chapter, tags, verified) always trigger Chroma updates
7. **Merge/Split Support:** Merge and split operations properly sync (delete old, create new records)

### Storage Estimates

**Per Book (1000 knowledge units):**
- PostgreSQL: ~7 MB (full records with 80 attributes)
- Chroma DB: ~1.5 MB (embeddings + minimal metadata)

**10 Books:**
- PostgreSQL: ~50 MB
- Chroma DB: ~15 MB

### Future Enhancements

1. **Cross-Book Collection:** Aggregate all books into single `cross_book_embeddings` collection
2. **Topic Clustering:** Use Chroma for automatic topic discovery across books
3. **Semantic Deduplication:** Find duplicate content across different books
4. **Image Embeddings:** Add CLIP embeddings (512-dim) for image similarity search

---

## ✅ Schema Validation Checklist

- [x] All 9 book-specific tables defined (2 raw + 7 processed)
- [x] 1 shared table (books_metadata) defined
- [x] Raw data tables: raw_pages and raw_knowledge_units
- [x] Processed data tables: knowledge_units, pages, images, processing_state, settings, hierarchy, attribute_keys
- [x] Two-tier architecture: Raw OCR data separate from processed/split data
- [x] Foreign key chain: raw_pages → raw_knowledge_units → knowledge_units
- [x] Foreign key: raw_pages → pages (image stored once)
- [x] 40 attribute value columns in knowledge_units table (attr1_value through attr40_value)
- [x] Separate attribute_keys table for book-level key names (40 rows)
- [x] Attributes 1-8 reserved as system-reserved (7 OCR + 1 record_status)
- [x] Attributes 9-40 available for user-defined attributes (32 total)
- [x] Attribute 8 (record_status) for merge/split tracking with default 'enabled'
- [x] Merge/split tracking columns (merged_into_record_id, original_record_ids)
- [x] All indexes created for performance (including merge/split indexes and FK indexes)
- [x] Triggers for updated_at columns
- [x] Helper functions for common operations
- [x] Vector columns for future similarity search
- [x] Storage estimates calculated (updated for raw tables)
- [x] Security considerations addressed
- [x] Initialization script provided
- [x] Chroma vector database structure defined
- [x] Foreign key constraints for raw → processed data flow

---

**Database Schema Design Complete:** ✅
**Total Tables per Book:** 10 (1 shared + 9 book-specific)
**Architecture:** Two-Tier (Raw → Processed)
**Ready for:** Data Model Detailed Specification + Technology Stack

