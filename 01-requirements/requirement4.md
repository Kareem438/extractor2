# Requirement 4: Hierarchical Title System with Custom Attributes

**Created:** January 26, 2026  
**Status:** Requirements Complete - Ready for Implementation  
**Priority:** High  
**Last Updated:** January 26, 2026

---

## 1. Overview

This requirement introduces a comprehensive hierarchical title system with custom attributes for Level 1 and Level 2 titles, mandatory linking enforcement during Layout Review, and validation gates before Layout Detection.

### 1.1 Goals
- Enable rich metadata capture at the title level (L1: 200 attributes, L2: 150 attributes)
- Enforce complete document hierarchy: L1 → L2 → L3 → Paragraph → (Diagrams/Lists/Q&A)
- Ensure all content regions are properly linked to their parent L3 titles
- Validate title configuration before Layout Detection execution

---

## 2. PENDING CLARIFICATION - Session 2026-01-26

### 2.1 Current State
The implementation has two systems that need to be merged:

**Legacy System (Currently Active):**
- Stores titles in `auto_slicer_config` JSON field in `books_metadata` table
- UI in Auto-Slicer page with "Title Configuration" section
- Features:
  - Page Viewer with rectangle selection for OCR text extraction
  - "Add Title from Extracted Text" button to create titles from scanned text
  - Title levels: level1, level2, level3
  - Each title has: title_text, start_page, end_page
  - No custom attributes support
  - Used by Layout Review to display L1/L2 in title bar

**New System (Partially Implemented):**
- Database tables: `{prefix}_level1_titles` (200 attributes), `{prefix}_level2_titles` (150 attributes)
- API endpoints in `title_hierarchy.py`
- Attribute editor pages: `l1-title-attributes.html`, `l2-title-attributes.html`
- UI section was removed due to confusion about duplication

### 2.2 User Requirements (To Be Clarified)
The user wants to:
1. **Save to DB**: Modify legacy system to save L1/L2 titles to database tables instead of JSON
2. **Page ranges**: Keep page_from and page_to for L1 and L2 titles
3. **Custom attributes**: Add ability to define 200 attributes per L1 title, 150 per L2 title
4. **Auto-linking**: Automatically link L1/L2 titles to L3 titles based on page number

### 2.3 Clarification Questions & Answers

**Batch 1: ✅ ANSWERED**

Q1. For the Page Viewer OCR extraction feature, should it:
   - ~~a) Create titles directly in the database (new system)~~
   - **✅ b) Keep creating titles in JSON config, then migrate to DB on save**
   - ~~c) Other approach~~

Q2. For L3 titles (detected by YOLO), should they:
   - ~~a) Automatically inherit L1/L2 based on page number (no explicit link stored)~~
   - **✅ b) Store explicit l1_title_id and l2_title_id foreign keys**
   - ~~c) Other approach~~
   - **Note:** L1/L2 title IDs must also be passed to generated KUs (paragraphs and diagrams) during extraction

**Code Validation for Q2:** ✅ VALIDATED
- ✅ `extraction_service.py` passes `l1_title`, `l2_title` TEXT values to KUs (lines 217-218 for paragraphs, 268-269 for diagrams)
- ❌ Missing: `l1_title_id`, `l2_title_id` INTEGER foreign keys in:
  - `raw_{prefix}_layout_detections` table (for L3 titles)
  - `raw_{prefix}_paragraph_images` table (for KUs)
  - `raw_{prefix}_diagram_images` table (for KUs)
- **Action Required:** 
  1. Add `l1_title_id` and `l2_title_id` columns to these tables
  2. Modify `save_paragraph()` and `save_diagram()` functions to accept and store FK IDs
  3. Modify `get_titles_for_page()` to return IDs in addition to text values

**Batch 2: ✅ ANSWERED**

Q3. For the attribute editor, should it be:
   - **✅ a) A separate page** (opened via "Attribute Names" button next to each title)
   - ~~b) An inline expandable section in the Auto-Slicer page~~
   - ~~c) A modal dialog~~
   - ~~d) Other approach~~

Q4. Should the legacy "Title Configuration" section be:
   - ~~a) Completely replaced with the new database-backed system~~
   - **✅ b) Kept as-is but modified to save to database (hybrid approach)**
   - ~~c) Kept for backward compatibility alongside new system~~
   - ~~d) Other approach~~

**Batch 3: ✅ ANSWERED**

Q5. For validation before Layout Detection, should it:
   - ~~a) Require ALL pages in range to have both L1 and L2 coverage~~
   - ~~b) Require only L1 coverage (L2 optional)~~
   - ~~c) Be configurable per book~~
   - **✅ d) Other approach - Skip Pages + Validation on "Ready for Extraction"**
   
   **User's Answer:**
   - Add "Skip Pages" concept - pages that will NOT be processed for text extraction
   - Add "Skip Page" button similar to "Ready for Extraction" button
   - When user clicks "Ready for Extraction" on a page:
     - Check if page falls within L1 title page range
     - Check if page falls within L2 title page range
     - If page is outside either range → show error message and block the action
     - User must update L1/L2 title page ranges to include the page before marking it ready

Q6. When displaying L1/L2 in Layout Review title bar, should it:
   - **✅ a) Read from database tables (new system)**
   - ~~b) Read from JSON config (legacy system)~~
   - ~~c) Support both with preference for database~~
   - ~~d) Other approach~~
   - **Note:** Both JSON config and database must stay in sync

---

## 2.4 New Feature: Skip Pages

Based on Q5 clarification, a new "Skip Pages" feature is required:

### Concept
- Pages can be marked as "Skip" - meaning they will NOT be processed for text extraction
- This is useful for pages like table of contents, index, blank pages, etc.
- Skip pages are excluded from L1/L2 coverage validation

### UI Changes
- Add "Skip Page" button in Layout Review (similar to "Ready for Extraction")
- Visual indicator for skipped pages (e.g., grayed out, strikethrough)
- Skip status stored in database

### Validation Logic
When user clicks "Ready for Extraction" on a page:
1. Check if page number falls within ANY L1 title's page range
2. Check if page number falls within ANY L2 title's page range
3. If EITHER check fails:
   - Show error message: "Page X is outside L1/L2 title coverage. Please update title page ranges."
   - Block the "Ready for Extraction" action
4. If both checks pass:
   - Allow marking page as "Ready for Extraction"

---

## 3. Legacy System Features to Preserve

### 3.1 Page Viewer with OCR Extraction
- Browse pages with Previous/Next navigation
- Draw rectangle on page to select text region
- OCR extracts text from selected region
- "Add Title from Extracted Text" button creates title entry
- Dropdown to select title level (L1, L2, L3)
- Current page auto-fills as start_page

### 3.2 Title Configuration UI
- Three sections: Level 1, Level 2, Level 3 titles
- Each title row: Title Text | Start Page | End Page | Delete button
- Add button for each level
- Titles stored in `auto_slicer_config.titles` JSON

### 3.3 Integration with Layout Review
- `loadTitleConfigs()` fetches from `/api/auto-slicer/{book_id}/config`
- `updateTitleDisplay(pageNumber)` shows L1/L2 in title bar
- Searches title arrays to find matching page range

---

## 2. Title Hierarchy Structure

### 2.1 Level 1 Titles (Chapters/Units)
- **Definition:** Top-level document divisions (e.g., "Chapter 1", "Unit A")
- **Page Range:** Each L1 title covers a range of pages (start_page to end_page)
- **Attributes:** 200 custom text attributes with user-definable names
- **Configuration:** Defined in Auto-Slicer page before Layout Detection

### 2.2 Level 2 Titles (Sections/Topics)
- **Definition:** Sub-divisions within L1 titles (e.g., "Section 1.1", "Topic A.1")
- **Page Range:** Each L2 title covers a range of pages within its parent L1
- **Attributes:** 150 custom text attributes with user-definable names
- **Configuration:** Defined in Auto-Slicer page before Layout Detection
- **Inheritance:** Automatically inherits parent L1 based on page number

### 2.3 Level 3 Titles (Sub-sections)
- **Definition:** Detected as regions during Layout Detection (YOLO model)
- **Storage:** Stored in `raw_{prefix}_layout_detections` table with class_name='title_level_3'
- **OCR:** Text extracted via Surya OCR during extraction phase
- **Inheritance:** Automatically inherits L1/L2 based on page number

---

## 3. User Stories

### US-4.1: Configure L1/L2 Titles Before Layout Detection
**As a** user processing a new book  
**I want to** define Level 1 and Level 2 titles with their page ranges in the Auto-Slicer page  
**So that** all detected content can be properly categorized in the document hierarchy

**Acceptance Criteria:**
- [ ] AC-4.1.1: Auto-Slicer page displays L1 title configuration section
- [ ] AC-4.1.2: Auto-Slicer page displays L2 title configuration section
- [ ] AC-4.1.3: Each title entry includes: title text, start_page, end_page
- [ ] AC-4.1.4: User can add, edit, and delete L1/L2 titles
- [ ] AC-4.1.5: Page ranges are validated (no gaps, no overlaps within same level)
- [ ] AC-4.1.6: Each title has a link to open attribute editor page

### US-4.2: Enforce Title Configuration Before Layout Detection
**As a** system  
**I want to** block Layout Detection if L1/L2 titles are not configured for the selected page range  
**So that** users don't process pages without proper hierarchy setup

**Acceptance Criteria:**
- [ ] AC-4.2.1: Before starting Layout Detection, system checks if all pages in range have L1 coverage
- [ ] AC-4.2.2: Before starting Layout Detection, system checks if all pages in range have L2 coverage
- [ ] AC-4.2.3: If validation fails, show error message listing uncovered pages
- [ ] AC-4.2.4: Layout Detection button is disabled until validation passes
- [ ] AC-4.2.5: Clear visual indicator shows which pages lack title coverage

### US-4.3: Define Custom Attributes for L1 Titles
**As a** user  
**I want to** define names for the 200 custom attributes on each L1 title  
**So that** I can capture book-specific metadata at the chapter level

**Acceptance Criteria:**
- [ ] AC-4.3.1: Clicking "Edit Attributes" on L1 title opens dedicated attribute editor page
- [ ] AC-4.3.2: Attribute editor shows 200 attribute slots (attr1 through attr200)
- [ ] AC-4.3.3: User can set custom name for each attribute
- [ ] AC-4.3.4: User can set value for each attribute
- [ ] AC-4.3.5: Attribute names are stored per-book (not global)
- [ ] AC-4.3.6: Changes are saved and persisted to database

### US-4.4: Define Custom Attributes for L2 Titles
**As a** user  
**I want to** define names for the 150 custom attributes on each L2 title  
**So that** I can capture book-specific metadata at the section level

**Acceptance Criteria:**
- [ ] AC-4.4.1: Clicking "Edit Attributes" on L2 title opens dedicated attribute editor page
- [ ] AC-4.4.2: Attribute editor shows 150 attribute slots (attr1 through attr150)
- [ ] AC-4.4.3: User can set custom name for each attribute
- [ ] AC-4.4.4: User can set value for each attribute
- [ ] AC-4.4.5: Attribute names are stored per-book (not global)
- [ ] AC-4.4.6: Changes are saved and persisted to database

### US-4.5: Auto-Link Paragraphs to L3 Titles
**As a** system  
**I want to** automatically link detected paragraphs to the nearest L3 title above them  
**So that** the document hierarchy is established without manual effort

**Acceptance Criteria:**
- [ ] AC-4.5.1: After Layout Detection, paragraphs are auto-linked to nearest L3 title (by Y position)
- [ ] AC-4.5.2: Auto-linking considers only L3 titles on the same page
- [ ] AC-4.5.3: If multiple L3 titles exist, paragraph links to the one immediately above it
- [ ] AC-4.5.4: Auto-link results are visible in Layout Review page

### US-4.6: Manual Override of Paragraph-L3 Links
**As a** user reviewing detected regions  
**I want to** manually change which L3 title a paragraph is linked to  
**So that** I can correct any auto-linking errors

**Acceptance Criteria:**
- [ ] AC-4.6.1: Layout Review page shows current L3 link for each paragraph
- [ ] AC-4.6.2: User can click to change the L3 link
- [ ] AC-4.6.3: Dropdown shows all L3 titles on the current page
- [ ] AC-4.6.4: Changes are saved immediately
- [ ] AC-4.6.5: Visual indicator shows manually-overridden links

### US-4.7: Block Extraction for Pages Without L3 Titles
**As a** system  
**I want to** prevent extraction on pages that have paragraphs but no L3 title  
**So that** all content maintains proper hierarchy

**Acceptance Criteria:**
- [ ] AC-4.7.1: Before extraction, validate each page has at least one L3 title if it has paragraphs
- [ ] AC-4.7.2: If validation fails, show error message listing affected pages
- [ ] AC-4.7.3: Error message instructs user to add L3 title regions manually
- [ ] AC-4.7.4: Extraction is blocked until all pages pass validation
- [ ] AC-4.7.5: User can add L3 title regions manually in Layout Review

### US-4.8: Ensure Complete Linking Chain
**As a** system  
**I want to** ensure all regions are linked through the hierarchy  
**So that** every piece of content can be traced to L1/L2/L3 titles

**Acceptance Criteria:**
- [ ] AC-4.8.1: Diagrams must be linked to a parent Paragraph (existing requirement)
- [ ] AC-4.8.2: Questions/Answers must be linked to a parent Paragraph (existing requirement)
- [ ] AC-4.8.3: Lists must be linked to a parent Paragraph (existing requirement)
- [ ] AC-4.8.4: Paragraphs must be linked to an L3 Title (new requirement)
- [ ] AC-4.8.5: L3 Titles inherit L2 based on page number (automatic)
- [ ] AC-4.8.6: L2 Titles inherit L1 based on page number (automatic)
- [ ] AC-4.8.7: Validation report shows any broken links in the chain

### US-4.9: Skip Pages Feature
**As a** user processing a book  
**I want to** mark certain pages as "Skip" (not for extraction)  
**So that** I can exclude pages like table of contents, index, or blank pages from processing

**Acceptance Criteria:**
- [ ] AC-4.9.1: Layout Review page has "Skip Page" button for each page
- [ ] AC-4.9.2: Skipped pages are visually distinct (grayed out or strikethrough)
- [ ] AC-4.9.3: Skip status is stored in database
- [ ] AC-4.9.4: Skipped pages are excluded from extraction processing
- [ ] AC-4.9.5: Skipped pages are excluded from L1/L2 coverage validation

### US-4.10: Validate L1/L2 Coverage Before Ready for Extraction
**As a** system  
**I want to** validate that a page falls within L1 and L2 title ranges before allowing "Ready for Extraction"  
**So that** users cannot process pages without proper hierarchy coverage

**Acceptance Criteria:**
- [ ] AC-4.10.1: When user clicks "Ready for Extraction", check if page is within L1 title range
- [ ] AC-4.10.2: When user clicks "Ready for Extraction", check if page is within L2 title range
- [ ] AC-4.10.3: If page is outside L1 range, show error message with specific L1 coverage gap
- [ ] AC-4.10.4: If page is outside L2 range, show error message with specific L2 coverage gap
- [ ] AC-4.10.5: Block "Ready for Extraction" action until page is covered by both L1 and L2
- [ ] AC-4.10.6: Error message instructs user to update title page ranges in Auto-Slicer

---

## 4. Database Schema Changes

### 4.1 New Table: `{prefix}_level1_titles`
```sql
CREATE TABLE {prefix}_level1_titles (
    id SERIAL PRIMARY KEY,
    title_text VARCHAR(500) NOT NULL,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    
    -- 200 custom attributes
    attr1_name VARCHAR(100),
    attr1_value TEXT,
    attr2_name VARCHAR(100),
    attr2_value TEXT,
    ... (up to attr200_name, attr200_value)
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 New Table: `{prefix}_level2_titles`
```sql
CREATE TABLE {prefix}_level2_titles (
    id SERIAL PRIMARY KEY,
    title_text VARCHAR(500) NOT NULL,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    parent_l1_id INTEGER REFERENCES {prefix}_level1_titles(id),
    
    -- 150 custom attributes
    attr1_name VARCHAR(100),
    attr1_value TEXT,
    attr2_name VARCHAR(100),
    attr2_value TEXT,
    ... (up to attr150_name, attr150_value)
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 Modified Table: `raw_{prefix}_layout_detections`
Add column if not exists:
- `l3_title_id INTEGER` - Links paragraph to L3 title region

---

## 5. UI Changes

### 5.1 Auto-Slicer Page Enhancements
- Add "Level 1 Titles" configuration section
- Add "Level 2 Titles" configuration section
- Each title row shows: Title Text | Start Page | End Page | [Edit Attributes] button
- Add/Edit/Delete buttons for title management
- Visual coverage indicator showing which pages have L1/L2 coverage
- Validation status indicator before Layout Detection

### 5.2 New Page: L1 Title Attribute Editor
- URL: `/book/{book_id}/l1-title/{title_id}/attributes`
- Shows all 200 attributes in a scrollable/paginated list
- Each row: Attribute Name input | Attribute Value input
- Save button to persist changes
- Back button to return to Auto-Slicer

### 5.3 New Page: L2 Title Attribute Editor
- URL: `/book/{book_id}/l2-title/{title_id}/attributes`
- Shows all 150 attributes in a scrollable/paginated list
- Each row: Attribute Name input | Attribute Value input
- Save button to persist changes
- Back button to return to Auto-Slicer

### 5.4 Layout Review Page Enhancements
- Show L3 title link for each paragraph region
- Dropdown to change L3 link (manual override)
- Visual indicator for auto-linked vs manually-linked
- Validation warnings for unlinked paragraphs

---

## 6. API Endpoints

### 6.1 L1 Title Management
- `GET /api/books/{book_id}/l1-titles` - List all L1 titles
- `POST /api/books/{book_id}/l1-titles` - Create L1 title
- `PUT /api/books/{book_id}/l1-titles/{id}` - Update L1 title
- `DELETE /api/books/{book_id}/l1-titles/{id}` - Delete L1 title
- `GET /api/books/{book_id}/l1-titles/{id}/attributes` - Get attributes
- `PUT /api/books/{book_id}/l1-titles/{id}/attributes` - Update attributes

### 6.2 L2 Title Management
- `GET /api/books/{book_id}/l2-titles` - List all L2 titles
- `POST /api/books/{book_id}/l2-titles` - Create L2 title
- `PUT /api/books/{book_id}/l2-titles/{id}` - Update L2 title
- `DELETE /api/books/{book_id}/l2-titles/{id}` - Delete L2 title
- `GET /api/books/{book_id}/l2-titles/{id}/attributes` - Get attributes
- `PUT /api/books/{book_id}/l2-titles/{id}/attributes` - Update attributes

### 6.3 Validation
- `GET /api/books/{book_id}/validate-title-coverage?start_page={}&end_page={}` - Check L1/L2 coverage
- `GET /api/books/{book_id}/validate-l3-links?page_numbers=[]` - Check paragraph-L3 links

### 6.4 Linking
- `POST /api/auto-slicer/{book_id}/auto-link-paragraphs` - Run auto-linking
- `PUT /api/auto-slicer/{book_id}/paragraph-l3-link` - Manual link override

---

## 7. Validation Rules

### 7.1 Pre-"Ready for Extraction" Validation (Per Page)
When user clicks "Ready for Extraction" on a page:
1. Check if page is marked as "Skip" → if yes, show error "Skipped pages cannot be marked ready"
2. Check if page falls within ANY L1 title's page range → if no, show error with gap details
3. Check if page falls within ANY L2 title's page range → if no, show error with gap details
4. If all checks pass → allow marking as "Ready for Extraction"

### 7.2 Pre-Extraction Validation (Batch)
1. All pages marked "Ready for Extraction" must have at least one L3 title (if they have paragraphs)
2. All paragraphs must be linked to an L3 title
3. All diagrams/lists/Q&A must be linked to a paragraph

### 7.3 Skip Pages Rules
1. Skipped pages are excluded from extraction processing
2. Skipped pages are excluded from L1/L2 coverage validation
3. Skipped pages cannot be marked as "Ready for Extraction"
4. Skip status is stored in `raw_{prefix}_layout_detections` or page-level config

---

## 8. Linking Chain Confirmation

Based on the existing system and new requirements, the complete linking chain is:

```
L1 Title (Chapter)
  └── L2 Title (Section) [inherits L1 by page number]
        └── L3 Title (Sub-section) [inherits L2 by page number, detected as region]
              └── Paragraph [must link to L3, auto-linked with manual override]
                    ├── Diagram [must link to Paragraph - existing]
                    ├── Table [must link to Paragraph - existing]
                    ├── Equation [must link to Paragraph - existing]
                    ├── List [must link to Paragraph - existing]
                    ├── Question [must link to Paragraph - existing]
                    └── Answer [must link to Question - existing]
```

**Confirmation:** If paragraphs are enforced to link to L3 titles, and diagrams/tables/equations/lists/Q&A are already enforced to link to paragraphs, then **all regions will be linked to L3 titles** (either directly for paragraphs, or indirectly through their parent paragraph for other region types).

---

## 9. Migration Considerations

### 9.1 Existing Books
- Existing books will need L1/L2 titles configured before further Layout Detection
- Existing detected regions without L3 links will need manual linking
- Migration script to create new tables for existing books

### 9.2 Backward Compatibility
- Existing extraction results remain valid
- New validation only applies to new Layout Detection runs
- Gradual enforcement allows users to update existing books

---

## 10. Dependencies

- Existing Auto-Slicer page and configuration
- Existing Layout Detection (YOLO) system
- Existing Layout Review page
- Existing Extraction service
- Existing paragraph-diagram linking system

---

## 11. Out of Scope

- L4/L5 title levels (may be added in future)
- Attribute templates across books
- Bulk attribute import/export
- Attribute validation rules (required, format, etc.)
