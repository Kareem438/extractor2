# CRITICAL: Architecture vs Implementation Discrepancy

**Discovered:** 2025-11-13
**Severity:** CRITICAL
**Impact:** Database schema does not match architecture design
**Reporter:** User investigation

---

## 🚨 Problem Summary

The **database schema design documents** describe a two-tier architecture with **RAW and PROCESSED tables**, but the **actual implementation** only creates **PROCESSED tables**. This is a fundamental architecture mismatch.

---

## 📋 What the Architecture Document Says

**File:** `/mnt/h/12-extractor/02-architecture/database-schema.md`

### Designed Schema (Lines 126-247)

**Total: 9 tables per book (2 raw + 7 processed)**

#### Raw Data Tables (2 tables) - SHOULD EXIST
```
1. raw_book{N}_{name}_pages
   Purpose: Store original page images extracted from PDF (no rectangles)
   Key fields:
   - original_image_data BYTEA
   - original_format VARCHAR(20)
   - original_width, original_height INTEGER

2. raw_book{N}_{name}_knowledge_units
   Purpose: Store raw OCR extractions (full page text per OCR run, BEFORE splitting)
   Key fields:
   - raw_page_id INTEGER (FK to raw_pages)
   - ocr_engine VARCHAR(50) (paddleocr, surya, tesseract)
   - full_page_text TEXT (UNSPLIT)
   - confidence_score NUMERIC(5,2)
   - extracted_image_ids TEXT[]  ← CRITICAL: Where images should be linked!
   - FK: raw_page_id → raw_pages
```

#### Processed Data Tables (7 tables)
```
3. book{N}_{name}_knowledge_units
   - FK: raw_knowledge_unit_id → raw_knowledge_units (parent OCR extraction)
   - Contains SPLIT semantic units (3-5 lines each)
   - Inherits OCR data from raw parent

4. book{N}_{name}_pages
   - FK: raw_page_id → raw_pages (for image data)
   - Stores marking rectangles ONLY (no image data)

5. book{N}_{name}_images
   - Stores extracted images with AI analysis
   - Linked via extracted_image_ids in raw_knowledge_units

6-9. processing_state, settings, hierarchy, attribute_keys
```

### Data Flow (As Designed)

```
PDF Upload
    ↓
1. Extract page images → Store in raw_pages table
    ↓
2. Run 3 OCR engines on each page
    ↓
3. Store FULL PAGE TEXT in raw_knowledge_units table
   - One record per page per OCR engine (3 records per page)
   - Extract embedded images → Store IDs in extracted_image_ids[]
   - Store image binary in images table
    ↓
4. User clicks "Evaluate, Split & Mark"
    ↓
5. Select best OCR text → Split into semantic chunks
    ↓
6. Store in knowledge_units table (with FK to raw_knowledge_units)
    ↓
7. Generate marking rectangles → Store in pages table (with FK to raw_pages)
```

**KEY BENEFIT:** Can re-split text without re-running expensive OCR (raw data preserved)

---

## 🔧 What the Implementation Actually Does

**File:** `/mnt/h/12-extractor/03-code/src/database/table_creator.py`

### Actual Schema (Function: create_book_tables, Line 363)

**Total: 7 tables per book (0 raw + 7 processed)**

#### Tables Created

```python
def create_book_tables(book_id: int, sanitized_name: str, total_pages: int):
    # Only creates 7 processed tables:
    1. create_knowledge_units_table(table_prefix)      # NO FK to raw_knowledge_units
    2. create_pages_table(table_prefix)                # NO FK to raw_pages
    3. create_images_table(table_prefix)               # Direct storage
    4. create_processing_state_table(table_prefix)
    5. create_settings_table(table_prefix)
    6. create_hierarchy_table(table_prefix)
    7. create_attribute_keys_table(table_prefix)

    # MISSING:
    ❌ raw_pages table NOT created
    ❌ raw_knowledge_units table NOT created
```

### Actual Data Flow (As Implemented)

```
PDF Upload
    ↓
1. Extract images → Store directly in images table
   (File: ocr_sequential.py, Line 158)
    ↓
2. Run OCR → Store directly in knowledge_units table
   (No raw storage layer!)
    ↓
3. Cannot re-split without re-running OCR
   (Raw data NOT preserved!)
```

---

## 📊 Side-by-Side Comparison

| Feature | Architecture Design | Actual Implementation |
|---------|-------------------|----------------------|
| **Tables per book** | 9 (2 raw + 7 processed) | 7 (0 raw + 7 processed) |
| **raw_pages table** | ✅ YES | ❌ NO |
| **raw_knowledge_units table** | ✅ YES | ❌ NO |
| **Image storage** | raw_knowledge_units.extracted_image_ids[] | Direct to images table |
| **OCR storage** | raw_knowledge_units (full page text, unsplit) | Direct to knowledge_units |
| **Re-split capability** | ✅ YES (raw data preserved) | ❌ NO (must re-run OCR) |
| **FK relationships** | knowledge_units → raw_knowledge_units<br>pages → raw_pages | ❌ NO FK (no raw tables) |
| **Page images** | raw_pages (stored once, referenced) | ❌ Not stored |
| **Data tier separation** | ✅ YES (Raw → Processed) | ❌ NO (single tier) |

---

## 🔍 Specific Code Locations

### Issue 1: Images Stored Directly (Not Through Raw Tables)

**File:** `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py`

**Line 158:**
```python
# WRONG: Images inserted directly into images table
db.execute(
    text(f"""
    INSERT INTO {table_prefix}_images
    (image_identifier, page_number, image_data, image_type, analyzed_during_ocr)
    VALUES (:id, :page, :data, :type, 'easyocr')
    """),
    {...}
)
```

**Should be:**
```python
# 1. Store image binary in images table
# 2. Store image ID in raw_knowledge_units.extracted_image_ids[]
# 3. Link knowledge_units to images via raw_knowledge_units
```

### Issue 2: OCR Text Stored Directly (Not in Raw Table)

**File:** `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py`

OCR results are stored directly in `knowledge_units` table attributes (attr2_value, attr3_value, attr4_value).

**Should be:**
```python
# 1. Store FULL PAGE TEXT in raw_knowledge_units table (one record per page per OCR engine)
# 2. User triggers "Evaluate, Split & Mark"
# 3. Select best OCR → Split text → Store in knowledge_units with FK to raw_knowledge_units
```

### Issue 3: Missing Raw Table Creation

**File:** `/mnt/h/12-extractor/03-code/src/database/table_creator.py`

**Line 363-396:**
```python
def create_book_tables(book_id: int, sanitized_name: str, total_pages: int):
    # ❌ Missing: create_raw_pages_table(table_prefix)
    # ❌ Missing: create_raw_knowledge_units_table(table_prefix)

    create_knowledge_units_table(table_prefix)  # No FK to raw
    create_pages_table(table_prefix)            # No FK to raw_pages
    create_images_table(table_prefix)
    # ... other tables
```

**Should be:**
```python
def create_book_tables(book_id: int, sanitized_name: str, total_pages: int):
    # Raw data tables (create first)
    create_raw_pages_table(table_prefix)
    create_raw_knowledge_units_table(table_prefix)

    # Processed data tables (with FKs to raw)
    create_knowledge_units_table(table_prefix)  # With FK to raw_knowledge_units
    create_pages_table(table_prefix)            # With FK to raw_pages
    create_images_table(table_prefix)
    # ... other tables
```

---

## ⚠️ Impact Analysis

### Critical Impacts

1. **❌ Cannot Re-Split Text Without Re-OCR**
   - Architecture benefit: Re-split without expensive OCR
   - Current reality: Must re-run OCR to re-split

2. **❌ No Raw Data Preservation**
   - All 3 OCR results not preserved as full-page text
   - Cannot go back to original extraction

3. **❌ Image Linkage Incorrect**
   - Images should be linked via raw_knowledge_units.extracted_image_ids[]
   - Currently stored directly without proper parent linkage

4. **❌ No Foreign Key Integrity**
   - Processed tables should have FK to raw tables
   - Missing referential integrity

### Data Loss Risk

If user wants to re-split knowledge units:
- **As Designed:** Use preserved raw_knowledge_units data
- **Current Implementation:** Must re-run expensive OCR (hours of processing)

---

## 🛠️ Required Fixes

### Priority 1: Add Raw Tables to table_creator.py

**File:** `/mnt/h/12-extractor/03-code/src/database/table_creator.py`

Add these functions:

```python
def create_raw_pages_table(table_prefix: str):
    """Create raw_pages table for original page images"""
    table_name = f"raw_{table_prefix}_pages"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL UNIQUE,

        -- Original Page Image (INPUT for OCR)
        original_image_data BYTEA NOT NULL,
        original_format VARCHAR(20) NOT NULL,  -- PNG, JPEG
        original_width INTEGER NOT NULL,
        original_height INTEGER NOT NULL,
        original_size_bytes INTEGER NOT NULL,

        -- Hierarchy
        chapter VARCHAR(255),
        topic VARCHAR(255),
        sub_topic VARCHAR(255),

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)
    # ... execute


def create_raw_knowledge_units_table(table_prefix: str):
    """Create raw_knowledge_units table for unsplit OCR results"""
    table_name = f"raw_{table_prefix}_knowledge_units"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Pages
        raw_page_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,

        -- OCR Metadata
        ocr_engine VARCHAR(50) NOT NULL,  -- easyocr, surya, tesseract
        ocr_run_timestamp TIMESTAMP DEFAULT NOW(),

        -- Full Page Text (UNSPLIT)
        full_page_text TEXT NOT NULL,
        text_length INTEGER NOT NULL,

        -- OCR Quality Metrics
        confidence_score NUMERIC(5,2) NOT NULL,
        language VARCHAR(50) NOT NULL,

        -- Extracted Images on this Page
        extracted_image_ids TEXT[],  -- ← CRITICAL FIELD!

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        -- Foreign Key Constraint
        FOREIGN KEY (raw_page_id) REFERENCES raw_{table_prefix}_pages(id) ON DELETE CASCADE
    )
    """)
    # ... execute


# Update create_book_tables to include raw tables
def create_book_tables(book_id: int, sanitized_name: str, total_pages: int):
    table_prefix = generate_table_prefix(book_id, sanitized_name)

    # Create raw tables FIRST
    create_raw_pages_table(table_prefix)
    create_raw_knowledge_units_table(table_prefix)

    # Create processed tables with FK references
    create_knowledge_units_table(table_prefix)  # Add FK to raw_knowledge_units
    create_pages_table(table_prefix)            # Add FK to raw_pages
    # ... rest
```

### Priority 2: Update knowledge_units Table Schema

Add FK to raw_knowledge_units:

```python
def create_knowledge_units_table(table_prefix: str):
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_prefix}_knowledge_units (
        unit_id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Knowledge Units
        raw_knowledge_unit_id INTEGER NOT NULL,

        -- Rest of fields...
        text_content TEXT NOT NULL,
        # ...

        -- Foreign Key Constraint
        FOREIGN KEY (raw_knowledge_unit_id)
            REFERENCES raw_{table_prefix}_knowledge_units(id)
            ON DELETE RESTRICT
    )
    """)
```

### Priority 3: Update pages Table Schema

Add FK to raw_pages:

```python
def create_pages_table(table_prefix: str):
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_prefix}_pages (
        page_id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL UNIQUE,

        -- Foreign Key to Raw Pages (for image data)
        raw_page_id INTEGER NOT NULL,

        -- Marker rectangles only (no image data stored here)
        marked_rectangles JSONB,
        marker_generated BOOLEAN DEFAULT FALSE,

        -- Foreign Key Constraint
        FOREIGN KEY (raw_page_id)
            REFERENCES raw_{table_prefix}_pages(id)
            ON DELETE CASCADE
    )
    """)
```

### Priority 4: Update OCR Workflow

**File:** `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py`

Change from:
```python
# Current: Store directly in knowledge_units
db.execute(text(f"INSERT INTO {table_prefix}_knowledge_units ..."))
```

To:
```python
# Step 1: Store page image in raw_pages
raw_page_id = db.execute(text(f"""
    INSERT INTO raw_{table_prefix}_pages
    (page_number, original_image_data, original_format, ...)
    VALUES (:page, :image, :format, ...)
    RETURNING id
"""), {...}).scalar()

# Step 2: Run 3 OCR engines, store full page text in raw_knowledge_units
for ocr_engine in ['easyocr', 'surya', 'tesseract']:
    full_page_text = run_ocr(ocr_engine, page_image)
    extracted_images = extract_images_from_page(page)

    db.execute(text(f"""
        INSERT INTO raw_{table_prefix}_knowledge_units
        (raw_page_id, page_number, ocr_engine, full_page_text,
         confidence_score, language, extracted_image_ids)
        VALUES (:raw_page_id, :page, :engine, :text, :conf, :lang, :img_ids)
    """), {
        "raw_page_id": raw_page_id,
        "page": page_num,
        "engine": ocr_engine,
        "text": full_page_text,
        "conf": confidence,
        "lang": language,
        "img_ids": extracted_images  # Array of image IDs
    })

# Step 3: Store images in images table
for image_id in extracted_images:
    db.execute(text(f"""
        INSERT INTO {table_prefix}_images
        (image_identifier, page_number, image_data, ...)
        VALUES (:id, :page, :data, ...)
    """), {...})

# Step 4: Evaluation/Split happens LATER (separate user action)
# This creates records in knowledge_units table with FK to raw_knowledge_units
```

### Priority 5: Implement Evaluation/Split/Mark Pipeline

Create a NEW function that:
1. Compares all 3 OCR results from raw_knowledge_units
2. Selects best text (highest confidence)
3. Splits into semantic chunks (3-5 lines)
4. Stores in knowledge_units with FK to raw_knowledge_units

---

## 📝 Migration Strategy

### For Existing Database (Book 1 Already Processed)

**Option A: Full Migration (Recommended)**
1. Create raw tables
2. Backfill from existing data (if possible)
3. Update all code to use new workflow

**Option B: Fresh Start (Easier)**
1. Drop all book1_* tables
2. Implement correct schema
3. Re-upload and re-process Book 1

**Recommendation:** Option B (Fresh Start) since Book 1 only has sample data

---

## 🎯 Action Items

- [x] **Task 1:** Document discrepancy (this file) ✅
- [ ] **Task 2:** Update START-HERE.md with todo for this fix
- [ ] **Task 3:** Add raw table creation functions to table_creator.py
- [ ] **Task 4:** Update knowledge_units schema with FK
- [ ] **Task 5:** Update pages schema with FK
- [ ] **Task 6:** Refactor OCR workflow to use raw tables
- [ ] **Task 7:** Implement separate evaluation/split/mark pipeline
- [ ] **Task 8:** Test complete workflow with raw → processed flow
- [ ] **Task 9:** Update all architecture docs if needed

---

## 📚 References

**Architecture Documentation:**
- `/mnt/h/12-extractor/02-architecture/database-schema.md` (Lines 126-247)
- `/mnt/h/12-extractor/02-architecture/system-design.md`
- `/mnt/h/12-extractor/02-architecture/sequential-ocr-svg-processing.md`

**Implementation Files:**
- `/mnt/h/12-extractor/03-code/src/database/table_creator.py` (Lines 363-396)
- `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py` (Lines 158-173)

---

## 💬 User Quote

> "I noticed another error in the documentation, the extracted images should go to the raw_knowledge units table, not the actual knowledge units table"

**User is CORRECT.** The architecture documents specify that:
1. Images extracted during OCR should have their IDs stored in `raw_knowledge_units.extracted_image_ids[]`
2. The processed `knowledge_units` table should link to images through the raw table
3. This enables the two-tier architecture benefits (re-split without re-OCR)

---

**Status:** CRITICAL - Must fix before project is considered production-ready
**Estimated Fix Time:** 4-6 hours (add tables + refactor OCR workflow + test)
**Priority:** HIGH (blocks architecture benefits)

---

*Document created: 2025-11-13*
*Next action: Update START-HERE.md to prioritize this fix*
