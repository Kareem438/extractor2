# Critical Issues Found - Knowledge Extraction System

## Date: 2025-11-12
## Status: Multiple Critical Bugs Preventing System Operation

---

## Summary

The verification page error "Failed to load knowledge units" is a **symptom** of several upstream critical bugs in the upload and OCR processing flow. The system is currently **non-functional** for the complete workflow.

---

## Critical Issues Identified

### 1. **Knowledge Units Table Not Created** ⛔ CRITICAL
**Error**: `relation "book1_01wessam_explanation_2026_knowledge_units" does not exist`

**Root Cause**: When a book is uploaded, the system should create book-specific tables including:
- `{table_prefix}_knowledge_units`
- `{table_prefix}_pages`
- `{table_prefix}_images`
- `{table_prefix}_processing_state`

**Current State**: These tables are never created during upload

**Location**: `/mnt/h/12-extractor/03-code/src/api/routes/upload.py`

**Expected Behavior** (from architecture):
```python
# After creating books_metadata entry:
1. Call table_creator.create_book_tables(table_prefix, book_id, attr_keys)
2. Create knowledge_units table
3. Create pages table
4. Create images table
5. Create processing_state table
6. Create attribute_keys table
```

**Evidence from Logs**:
```
2025-11-12 16:07:55,530 - ERROR - Failed to get knowledge units:
(psycopg2.errors.UndefinedTable) relation "book1_01wessam_explanation_2026_knowledge_units" does not exist
```

---

### 2. **SQLAlchemy `text()` Function Error** ⛔ CRITICAL
**Error**: `UnboundLocalError: cannot access local variable 'text' where it is not associated with a value`

**Root Cause**: In `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py` line 45:
```python
text("SELECT table_prefix, total_pages FROM books_metadata WHERE book_id = :book_id"),
```

The `text()` function is being called but it's not imported correctly or there's a naming conflict.

**Location**: `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py:45`

**Current Code**:
```python
from sqlalchemy import text  # Import at top
# ... later in code:
result = db.execute(
    text("SELECT ..."),  # ← This fails
    {"book_id": book_id}
).first()
```

**Evidence from Logs**:
```
2025-11-12 16:02:21,804 - ERROR - PaddleOCR processing failed for book_id=1:
cannot access local variable 'text' where it is not associated with a value
```

---

### 3. **PostgreSQL Vector Extension Missing** ⚠️ HIGH
**Error**: `psycopg2.errors.UndefinedObject) type "vector" does not exist`

**Root Cause**: The pgvector extension is not installed in PostgreSQL database

**Location**: Table creation in `table_creator.py` uses `VECTOR(384)` type

**Fix Required**:
```sql
-- Run in PostgreSQL:
CREATE EXTENSION IF NOT EXISTS vector;
```

**Evidence from Logs**:
```
2025-11-12 13:30:00,096 - ERROR - Upload error: type "vector" does not exist
LINE 74:         embedding_vector VECTOR(384),
```

---

### 4. **Duplicate Book Name Constraint** ⚠️ MEDIUM
**Error**: `duplicate key value violates unique constraint "books_metadata_sanitized_name_key"`

**Root Cause**: User tried to upload the same book multiple times, system doesn't handle gracefully

**Expected Behavior**:
- Either allow duplicate names with auto-incremented suffix
- Or show clear error message to user
- Or allow user to select existing book and continue processing

**Evidence from Logs**:
```
2025-11-11 02:18:03,108 - ERROR - Upload error: duplicate key value violates
unique constraint "books_metadata_sanitized_name_key"
Key (sanitized_name)=(01wessam_explanation_2026) already exists.
```

---

## Impact Analysis

### User Journey Breakdown:

1. **Step 1: Upload File** ❌ FAILS
   - Vector extension error prevents table creation
   - Book metadata may be created, but tables are not

2. **Step 2: Click "Start with PaddleOCR"** ❌ FAILS
   - `text()` function error prevents OCR processing
   - No knowledge units are created

3. **Step 3: Click "Evaluate, Split and Mark"** ❌ FAILS
   - Table doesn't exist error
   - Cannot process non-existent records

4. **Step 4: Go to Verification Page** ❌ FAILS
   - API call to load knowledge units fails
   - Table doesn't exist
   - Error: "Failed to load knowledge units"

**Result**: Complete workflow is broken. No part of the sequential OCR pipeline works.

---

## Architecture vs Implementation Gap

### As Designed (from `/02-architecture/sequential-ocr-svg-processing.md`):

```
Upload → Create Tables → OCR (Sequential) → Evaluate/Split/Mark → Verification
```

### Current Reality:

```
Upload → ❌ Tables Not Created → ❌ OCR Fails → ❌ Evaluate Fails → ❌ Verification Fails
```

---

## Immediate Actions Required (Priority Order)

### Priority 1: Fix PostgreSQL Vector Extension
```bash
# Connect to PostgreSQL
psql -U postgres -d knowledge_extraction

# Install extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
\dx vector
```

### Priority 2: Fix Table Creation in Upload Flow
**File**: `/mnt/h/12-extractor/03-code/src/api/routes/upload.py`

**Required Changes**:
1. Ensure `create_book_tables()` is called after books_metadata insert
2. Ensure all 5 tables are created successfully
3. Handle table creation errors gracefully
4. Add logging for each table creation step

### Priority 3: Fix SQLAlchemy text() Import Bug
**File**: `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py`

**Investigate**:
- Is `text` function properly imported?
- Is there a variable name collision?
- Is the import statement correct?

### Priority 4: Add Duplicate Book Handling
**File**: `/mnt/h/12-extractor/03-code/src/api/routes/upload.py`

**Options**:
1. Auto-append suffix (e.g., `book_name_2`, `book_name_3`)
2. Return 409 Conflict with clear message
3. Allow user to choose: "Continue with existing" or "Upload new version"

---

## Testing Checklist (After Fixes)

- [ ] PostgreSQL vector extension installed
- [ ] Upload completes successfully
- [ ] All 5 book tables created (verify with `\dt` in psql)
- [ ] PaddleOCR processing completes
- [ ] Knowledge units inserted successfully
- [ ] Evaluate/Split/Mark completes
- [ ] Verification page loads without error
- [ ] Knowledge units display in verification interface

---

## Database Diagnostic Commands

```bash
# Connect to database
psql -U postgres -d knowledge_extraction

# Check if vector extension exists
\dx

# Check what tables exist
\dt

# Check books_metadata
SELECT book_id, book_name, table_prefix, processing_status FROM books_metadata;

# Check if book tables exist (replace with actual prefix)
\dt book1_*

# Check knowledge_units structure (if exists)
\d book1_01wessam_explanation_2026_knowledge_units
```

---

## Next Steps

1. **Fix vector extension** (5 minutes)
2. **Fix table creation** (30-60 minutes)
3. **Fix text() import bug** (15 minutes)
4. **Test complete workflow** (30 minutes)
5. **Add duplicate handling** (30 minutes)

**Estimated Total Time**: 2-3 hours for complete fix

---

## Contact

If you need help with any of these fixes, please provide:
1. PostgreSQL version
2. Current database schema (`\dt` output)
3. Any additional error messages

---

*This document will be updated as issues are resolved.*
