# Requirement 5: Multi-PDF Upload & Cross-Book Attribute Access

**Created:** January 26, 2026  
**Status:** Requirements Complete  
**Priority:** High  
**Last Updated:** January 26, 2026

---

## 1. Overview

This requirement introduces two major features:
1. **Multi-PDF Upload**: Allow multiple PDF files to be uploaded for the same book (e.g., file 1 covers pages 1-200, file 2 covers pages 201-400)
2. **Cross-Book Attribute Access**: Allow books to read/write custom attributes of L1/L2 titles from other books
3. **Template Reference UI**: Enhanced pipeline-config UI with autocomplete for referencing book attributes

---

## 2. Clarification Questions & Answers

### Batch 1: Multi-PDF Upload

**Q1. When uploading a second PDF for the same book, should the system:**
- a) Automatically detect the page range based on existing pages
- b) Require user to specify the starting page number
- **✅ c) Allow both options (auto-detect with manual override)**
- d) Other approach

**Answer:** C - Auto-detect with manual override. System suggests starting page based on existing pages, but user can change it.

**Q2. If there's a page overlap between PDFs (e.g., PDF1 has pages 1-200, PDF2 has pages 195-400), should the system:**
- a) Reject the upload with an error
- b) Overwrite the overlapping pages with the new PDF
- c) Keep the original pages and skip duplicates
- **✅ d) Ask the user which version to keep**
- e) Other approach

**Answer:** D - Ask user which version to keep, with checkbox "Apply same choice for all duplicates" to batch-apply the decision.

---

### Batch 2: Cross-Book Attribute Access

**Q3. For cross-book attribute access, should the "last 50 attributes" writable rule apply to:**
- a) Attributes 151-200 for L1 (total 200) and 101-150 for L2 (total 150) - fixed positions
- **✅ b) A configurable range that can be set per book/title**
- c) A fixed range that's the same for all books
- d) Other approach

**Answer:** B - Configurable per title. User specifies writable range in Auto-Slicer when defining titles (alongside page numbers). Default is last 50 attributes, but user can change it per title.

**Q4. When Book B writes to Book A's attributes, should there be:**
- a) No audit trail (just overwrite)
- **✅ b) A simple log of who wrote what and when**
- c) Full version history with ability to revert
- d) Other approach

**Answer:** B - Simple log including:
- Which book wrote
- Which pipeline rule (name and number) initiated the write
- Timestamp
- Old value → New value

**Additional Feature:** Pipeline configurator should support a "counter increment" operation that reads existing value and increases by 1.

---

### Batch 3: Template Reference UI

**Q5. For the template reference syntax (e.g., `$$book1.L1.ChapterName.attribute22`), should the trigger be:**
- a) `$$` (double dollar sign)
- b) `{{` (double curly braces)
- **✅ c) `@` (at sign)**
- d) `#` (hash)
- e) Other symbol you prefer

**Answer:** C - Use `@` as trigger symbol. Example: `@BookA.L1.Chapter1.attr22`

**Q6. When the user types the trigger symbol, should the autocomplete:**
- a) Show a hierarchical dropdown (Book → Level → Title → Attribute)
- b) Show a flat searchable list with all options
- c) Show a modal dialog with a tree view
- **✅ d) Combination: inline dropdown + modal for full browsing**
- e) Other approach

**Answer:** D - Combination approach:
- Inline dropdown appears immediately when user types `@`
- User can type to filter results in the dropdown
- Button/link to open full modal with tree view for comprehensive browsing
- Both support typing to filter

---

### Batch 4: Additional Clarifications

**Q7. For multi-PDF upload, should the system support:**
- a) Only sequential page ranges (no gaps)
- b) Any page ranges (gaps allowed)
- c) Overlapping ranges with merge strategy
- **✅ d) All of the above (sequential, gaps, and overlaps)**

**Answer:** D - All supported with advanced page mapping:
- User specifies "PDF page to start counting from" (e.g., 4 = skip first 3 pages of PDF)
- User specifies "Book page number to assign" (e.g., 88)
- Example: PDF page 4 → Book page 88, PDF page 5 → Book page 89, etc.
- This mapping is critical for L1/L2 title page ranges to work correctly

**Q8. For cross-book access, should there be a permission system:**
- **✅ a) All books can access all other books by default (Phase 1)**
- b) Explicit permission must be granted per book pair
- c) Books in the same "project" can access each other
- d) Read open, write requires permission (Future enhancement)

**Answer:** A for Phase 1 (open access), with D as future enhancement (read open, write requires permission).

---

### Batch 5: UI/UX Details

**Q9. In the template editor, when a reference is inserted, should it:**
- a) Show the full path (e.g., `$$Book1.L1.Chapter1.attr22`)
- b) Show a shortened version with tooltip (e.g., `$$[Book1.attr22]`)
- c) Show a visual chip/tag that can be clicked to edit
- **✅ d) Full path with syntax highlighting**

**Answer:** D - Full path with syntax highlighting. Different colors for each component:
- Book name: one color
- Level (L1/L2): another color
- Title name: another color
- Attribute: another color
This makes complex references easy to read and understand at a glance.

**Q10. For the attribute reference, should the syntax use:**
- a) Attribute number (e.g., `attr22`)
- b) Attribute name if defined (e.g., `EnergyLevel`)
- c) Both options (name preferred, number as fallback)
- **✅ d) Show `attr22(EnergyLevel)` format**

**Answer:** D - Always show attribute number, with name in parentheses if defined.
- Example: `attr22(EnergyLevel)` when name is defined
- Example: `attr22` when no name is defined
- This ensures clarity (number is always visible) while providing context (name when available)

---

## 3. Feature Details

### 3.1 Multi-PDF Upload

**Purpose:** Allow users to upload multiple PDF files for a single book, supporting various page range scenarios.

**Key Features:**
1. **Page Mapping System**
   - User specifies "PDF page to start counting from" (skip cover pages, etc.)
   - User specifies "Book page number to assign" (the actual book page number)
   - Example: PDF page 4 → Book page 88, PDF page 5 → Book page 89, etc.

2. **Auto-Detection with Override**
   - System auto-detects suggested starting page based on existing pages
   - User can manually override the suggestion

3. **Overlap Handling**
   - When pages overlap between PDFs, prompt user to choose which version to keep
   - "Apply same choice for all duplicates" checkbox for batch decisions

4. **Supported Scenarios**
   - Sequential ranges (no gaps)
   - Ranges with gaps
   - Overlapping ranges with user-controlled merge

### 3.2 Cross-Book Attribute Access

**Purpose:** Allow books to read and write custom attributes of L1/L2 titles from other books.

**Key Features:**
1. **Access Model (Phase 1)**
   - All books can read all attributes from all other books
   - All books can write to other books' attributes (within writable range)
   - Open access by default

2. **Writable Range Configuration**
   - Configurable per title in Auto-Slicer
   - Default: last 50 attributes are writable by other books
   - User can change the writable range per title

3. **Audit Logging**
   - Simple log for cross-book writes
   - Logged data: source book, pipeline rule name/number, timestamp, old value → new value

4. **Counter Increment Operation**
   - Pipeline can read existing attribute value and increment by 1
   - Useful for tracking counts across books

5. **Future Enhancement (Phase 2)**
   - Read: open access
   - Write: requires explicit permission

### 3.3 Template Reference UI

**Purpose:** Enhanced pipeline-config UI with autocomplete for referencing book attributes.

**Key Features:**
1. **Trigger Symbol**
   - `@` triggers the autocomplete
   - Example: `@BookA.L1.Chapter1.attr22(EnergyLevel)`

2. **Autocomplete UI**
   - Inline dropdown appears when user types `@`
   - User can type to filter results
   - Button to open full modal with tree view for comprehensive browsing

3. **Reference Display**
   - Full path with syntax highlighting
   - Different colors for: Book name, Level (L1/L2), Title name, Attribute
   - Attribute format: `attr22(EnergyLevel)` - number always shown, name in parentheses if defined

4. **Reference Syntax**
   - Format: `@BookName.Level.TitleName.attrN(AttributeName)`
   - Example: `@Physics101.L1.EnergyChapter.attr22(EnergyLevel)`

---

## 4. Database Schema Changes

### 4.1 New Tables

#### 4.1.1 `pdf_uploads` - Track Multiple PDF Files per Book
```sql
CREATE TABLE pdf_uploads (
    id                      SERIAL PRIMARY KEY,
    book_id                 INTEGER NOT NULL REFERENCES books_metadata(book_id),
    
    -- File Information
    filename                VARCHAR(255) NOT NULL,
    file_path               TEXT NOT NULL,
    file_size_bytes         BIGINT NOT NULL,
    
    -- Page Mapping
    pdf_start_page          INTEGER NOT NULL DEFAULT 1,     -- First page in PDF to count from
    book_start_page         INTEGER NOT NULL,               -- Book page number for pdf_start_page
    total_pdf_pages         INTEGER NOT NULL,               -- Total pages in this PDF
    
    -- Calculated Range (for quick lookups)
    book_page_start         INTEGER NOT NULL,               -- First book page covered
    book_page_end           INTEGER NOT NULL,               -- Last book page covered
    
    -- Status
    upload_order            INTEGER NOT NULL DEFAULT 1,     -- Order of upload (1, 2, 3...)
    status                  VARCHAR(50) DEFAULT 'active',   -- active, replaced, deleted
    
    -- Timestamps
    uploaded_at             TIMESTAMP DEFAULT NOW(),
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pdf_uploads_book ON pdf_uploads(book_id);
CREATE INDEX idx_pdf_uploads_range ON pdf_uploads(book_id, book_page_start, book_page_end);
```

#### 4.1.2 `cross_book_access_log` - Audit Trail for Cross-Book Writes
```sql
CREATE TABLE cross_book_access_log (
    id                      SERIAL PRIMARY KEY,
    
    -- Source (who wrote)
    source_book_id          INTEGER NOT NULL REFERENCES books_metadata(book_id),
    source_pipeline_rule    VARCHAR(255),                   -- Pipeline rule name
    source_pipeline_number  INTEGER,                        -- Pipeline rule number
    
    -- Target (where written)
    target_book_id          INTEGER NOT NULL REFERENCES books_metadata(book_id),
    target_level            VARCHAR(10) NOT NULL,           -- 'L1' or 'L2'
    target_title_id         INTEGER NOT NULL,
    target_attribute        VARCHAR(20) NOT NULL,           -- e.g., 'attr22'
    
    -- Values
    old_value               TEXT,
    new_value               TEXT,
    operation               VARCHAR(20) NOT NULL,           -- 'write', 'increment'
    
    -- Timestamps
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cross_book_log_source ON cross_book_access_log(source_book_id);
CREATE INDEX idx_cross_book_log_target ON cross_book_access_log(target_book_id, target_level, target_title_id);
CREATE INDEX idx_cross_book_log_time ON cross_book_access_log(created_at DESC);
```

### 4.2 Modified Tables

#### 4.2.1 `books_metadata` - Add Multi-PDF Support
```sql
ALTER TABLE books_metadata ADD COLUMN IF NOT EXISTS
    has_multiple_pdfs       BOOLEAN DEFAULT FALSE;
    
ALTER TABLE books_metadata ADD COLUMN IF NOT EXISTS
    pdf_count               INTEGER DEFAULT 1;
```

#### 4.2.2 `{prefix}_level1_titles` - Add Writable Range
```sql
ALTER TABLE {prefix}_level1_titles ADD COLUMN IF NOT EXISTS
    external_writable_start INTEGER DEFAULT 151;            -- First attr writable by other books
    
ALTER TABLE {prefix}_level1_titles ADD COLUMN IF NOT EXISTS
    external_writable_end   INTEGER DEFAULT 200;            -- Last attr writable by other books
```

#### 4.2.3 `{prefix}_level2_titles` - Add Writable Range
```sql
ALTER TABLE {prefix}_level2_titles ADD COLUMN IF NOT EXISTS
    external_writable_start INTEGER DEFAULT 101;            -- First attr writable by other books
    
ALTER TABLE {prefix}_level2_titles ADD COLUMN IF NOT EXISTS
    external_writable_end   INTEGER DEFAULT 150;            -- Last attr writable by other books
```

### 4.3 Page Number Resolution

When accessing a page, the system will:
1. Query `pdf_uploads` to find which PDF contains the book page
2. Calculate the actual PDF page: `pdf_page = (book_page - book_start_page) + pdf_start_page`
3. Load the image from the correct PDF file

---

## 5. API Endpoints

### 5.1 Multi-PDF Upload Endpoints

#### `POST /api/books/{book_id}/upload-pdf`
Upload additional PDF to existing book.
```json
Request:
{
    "file": <PDF file>,
    "pdf_start_page": 4,        // Skip first 3 pages of PDF
    "book_start_page": 88       // PDF page 4 = Book page 88
}

Response:
{
    "upload_id": 2,
    "book_id": 1,
    "pages_added": 150,
    "book_page_range": [88, 237],
    "overlaps": [
        {"page": 88, "existing_pdf_id": 1}
    ]
}
```

#### `POST /api/books/{book_id}/resolve-overlaps`
Resolve page overlaps between PDFs.
```json
Request:
{
    "resolutions": [
        {"page": 88, "keep_pdf_id": 2},
        {"page": 89, "keep_pdf_id": 1}
    ],
    "apply_to_all": true,       // Apply same choice to all
    "default_choice": "new"     // "new" or "existing"
}
```

#### `GET /api/books/{book_id}/pdf-uploads`
List all PDFs for a book.
```json
Response:
{
    "pdfs": [
        {
            "id": 1,
            "filename": "book_part1.pdf",
            "book_page_range": [1, 200],
            "status": "active"
        },
        {
            "id": 2,
            "filename": "book_part2.pdf",
            "book_page_range": [88, 237],
            "status": "active"
        }
    ]
}
```

### 5.2 Cross-Book Attribute Access Endpoints

#### `GET /api/cross-book/books`
List all books available for cross-book access.
```json
Response:
{
    "books": [
        {
            "book_id": 1,
            "book_name": "Physics 101",
            "l1_titles": [...],
            "l2_titles": [...]
        }
    ]
}
```

#### `GET /api/cross-book/books/{book_id}/titles/{level}/{title_id}/attributes`
Get attributes from another book's title.
```json
Response:
{
    "book_id": 1,
    "level": "L1",
    "title_id": 5,
    "title_text": "Energy Chapter",
    "attributes": {
        "attr1": {"name": "...", "value": "..."},
        ...
    },
    "writable_range": [151, 200]
}
```

#### `PUT /api/cross-book/books/{book_id}/titles/{level}/{title_id}/attributes`
Write to another book's attributes (within writable range).
```json
Request:
{
    "source_book_id": 2,
    "source_pipeline_rule": "Rule 3: Cross-reference",
    "source_pipeline_number": 3,
    "attributes": {
        "attr155": {"value": "new value"},
        "attr160": {"operation": "increment"}  // Read and +1
    }
}
```

#### `GET /api/cross-book/audit-log`
Get cross-book write audit log.
```json
Request params: ?source_book_id=2&target_book_id=1&limit=100

Response:
{
    "logs": [
        {
            "id": 1,
            "source_book": "Book B",
            "target_book": "Book A",
            "target_title": "L1: Energy Chapter",
            "attribute": "attr155",
            "operation": "write",
            "old_value": null,
            "new_value": "5",
            "pipeline_rule": "Rule 3: Cross-reference",
            "timestamp": "2026-01-26T10:30:00Z"
        }
    ]
}
```

### 5.3 Template Reference Endpoints

#### `GET /api/template-reference/search`
Search for attribute references (for autocomplete).
```json
Request params: ?query=Physics.L1.Energy&current_book_id=2

Response:
{
    "results": [
        {
            "reference": "@Physics101.L1.EnergyChapter.attr22(EnergyLevel)",
            "book_id": 1,
            "book_name": "Physics 101",
            "level": "L1",
            "title_id": 5,
            "title_text": "Energy Chapter",
            "attribute_num": 22,
            "attribute_name": "EnergyLevel",
            "is_writable": true
        }
    ]
}
```

#### `GET /api/template-reference/tree`
Get full tree structure for modal browser.
```json
Response:
{
    "books": [
        {
            "book_id": 1,
            "book_name": "Physics 101",
            "levels": {
                "L1": [
                    {
                        "title_id": 5,
                        "title_text": "Energy Chapter",
                        "attributes": [
                            {"num": 1, "name": "Type"},
                            {"num": 22, "name": "EnergyLevel"},
                            ...
                        ],
                        "writable_range": [151, 200]
                    }
                ],
                "L2": [...]
            }
        }
    ]
}
```

---

## 6. UI Changes

### 6.1 Upload Page Changes

#### Multi-PDF Upload Section
- Add "Upload Additional PDF" button (visible after first upload)
- Page mapping form:
  - "Skip first N pages of PDF" input (default: 0)
  - "Starting book page number" input (auto-suggested based on existing pages)
- Overlap resolution modal:
  - Shows list of overlapping pages
  - Radio buttons: "Keep existing" / "Use new"
  - Checkbox: "Apply same choice to all"

### 6.2 Auto-Slicer Changes

#### Writable Range Configuration
- Add "External Writable Range" section when defining titles
- Two inputs per title:
  - "Writable Start" (default: 151 for L1, 101 for L2)
  - "Writable End" (default: 200 for L1, 150 for L2)
- Help text explaining cross-book write permissions

### 6.3 Pipeline Dashboard Changes

#### Template Reference Autocomplete
- Trigger: `@` symbol in template editor
- Inline dropdown:
  - Shows filtered results as user types
  - Format: `BookName > Level > Title > attr#(Name)`
  - Keyboard navigation support
- "Browse All" button opens modal

#### Reference Browser Modal
- Tree view structure:
  - Books (expandable)
    - L1 Titles (expandable)
      - Attributes list
    - L2 Titles (expandable)
      - Attributes list
- Search/filter box at top
- Click to insert reference
- Shows writable indicator for each attribute

#### Syntax Highlighting
- Color scheme for references:
  - Book name: Blue (#3498db)
  - Level (L1/L2): Purple (#9b59b6)
  - Title name: Green (#27ae60)
  - Attribute: Orange (#e67e22)
- Example: `@Physics101.L1.EnergyChapter.attr22(EnergyLevel)`

#### Counter Increment Operation
- New operation type in pipeline rule editor
- Dropdown: "Set Value" / "Increment Counter"
- When "Increment Counter" selected:
  - Reads current value
  - Adds 1
  - Writes new value
  - Logs operation in audit trail

### 6.4 New Pages

#### Cross-Book Access Log Page
- Table showing all cross-book writes
- Filters: Source book, Target book, Date range
- Columns: Timestamp, Source, Target, Attribute, Operation, Old→New
- Export to CSV option

---

## 7. Dependencies

- Existing upload system (`03-code/src/api/routes/upload.py`)
- Existing books management (`03-code/src/api/routes/books.py`)
- Existing title hierarchy system (`03-code/src/api/routes/title_hierarchy.py`)
- Existing pipeline configuration (`03-code/src/frontend/templates/pipeline-dashboard.html`)
- Existing KU creation service (`03-code/src/services/ku_creation_service.py`)

---

## 8. Out of Scope

### Phase 1 (Current Implementation)
- Permission-based write access (all books can write to all books)
- Version history/rollback for cross-book writes
- Real-time collaboration notifications
- Batch PDF upload (one at a time)

### Future Enhancements (Phase 2+)
- Permission system: Read open, write requires explicit permission
- Version history with rollback capability
- Notifications when another book writes to your attributes
- Batch upload multiple PDFs at once
- PDF merge/split tools
- Cross-book search functionality
