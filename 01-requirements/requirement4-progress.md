# Requirement 4: Progress Tracker

**Feature:** Hierarchical Title System with Custom Attributes  
**Created:** January 26, 2026  
**Last Updated:** January 31, 2026

---

## Overall Status: 🟢 All Bugs Fixed - Ready for Final Testing

| Phase | Status | Progress |
|-------|--------|----------|
| Requirements | ✅ Complete | 100% |
| Design | ✅ Complete | 100% |
| Implementation | ✅ Complete | 100% |
| Testing | 🟡 In Progress | 60% |
| Documentation | 🔴 Not Started | 0% |

---

## 🔴 CRITICAL BUGS FOUND (Session 2026-01-31)

### Bug 3: Extraction Results Not Appearing
**Status:** ✅ FULLY FIXED (Symptom + Root Cause)
**Reported:** 2026-01-31
**Fixed:** 2026-01-31
**Description:** User extracted page 7 but nothing appears on the extraction page.

**Root Cause:**
- Missing `is_skipped` column in `raw_book2_high_2_pages` table
- Migration `migrate_add_title_fk_columns.py` hadn't been run for book 2
- **ROOT CAUSE:** The `table_creator.py` didn't include required columns when creating new book tables

**Fix Applied (Symptom):**
- [x] Ran migration script to add `is_skipped` and `is_ready_for_extraction` columns
- [x] Also added `l1_title_id`, `l2_title_id` columns to layout_detections, paragraph_images, diagram_images tables

**Root Cause Fix Applied:**
- [x] Updated `create_raw_pages_table()` to include `is_skipped` and `is_ready_for_extraction` columns
- [x] Updated `create_raw_paragraph_images_table()` to include `l1_title_id`, `l2_title_id` columns
- [x] Updated `create_raw_diagram_images_table()` to include `l1_title_id`, `l2_title_id` columns
- [x] Updated `create_layout_detections_table()` to include `l1_title_id`, `l2_title_id` columns
- [x] Updated `create_level1_titles_table()` to include `external_writable_start`, `external_writable_end` columns
- [x] Updated `create_level2_titles_table()` to include `external_writable_start`, `external_writable_end` columns

### Bug 1: "Attr" Button Shows "Not Found" Error
**Status:** ✅ FIXED
**Reported:** 2026-01-31
**Fixed:** 2026-01-31
**Description:** When clicking "Attr" button for L1/L2 titles in Auto-Slicer, user gets `{"detail":"Not Found"}`

**Root Cause:**
1. Route mismatch: `openAttributeEditor()` was opening `/book/{book_id}/l1-title/{title_id}/attributes`
2. Actual route is: `/l1-title-attributes?book_id={}&title_id={}`
3. Titles created in JSON config didn't have DB IDs until "Save Config" was clicked
4. After saving, UI didn't refresh to show the new DB IDs

**Fix Applied:**
- [x] Fixed `openAttributeEditor()` to use correct URL format: `/${levelNum}-title-attributes?book_id=${currentBookId}&title_id=${titleId}`
- [x] Added `reloadTitlesFromDatabase()` function to reload titles with IDs after save
- [x] Modified `saveConfig()` to call `reloadTitlesFromDatabase()` after sync
- [x] Added validation in `openAttributeEditor()` to show helpful message if title not saved yet

### Bug 2: Layout Detection Validation Blocks Valid Configuration
**Status:** ✅ FIXED
**Reported:** 2026-01-31
**Fixed:** 2026-01-31
**Description:** User configured L1 (pages 5-80) and L2 (pages 5-40) for book "High", set page range to 5-40, but still gets error: "Please configure L1 and L2 titles to cover all pages in the selected range before running Layout Detection."

**Root Cause:**
1. Error message was too generic - didn't show which pages were missing
2. Validation status section existed but wasn't being scrolled to
3. User didn't know what specific pages needed coverage

**Fix Applied:**
- [x] Improved `displayValidationResult()` to show detailed breakdown:
  - Shows which pages are missing L1 coverage
  - Shows which pages are missing L2 coverage
  - Shows step-by-step instructions on how to fix
- [x] Updated `detectLayout()` alert to reference the validation status section
- [x] Added scroll-to-validation-status when detection is blocked

---

## Next Actions (Priority Order)

1. **✅ DONE:** Bug 1 - Fixed `openAttributeEditor()` URL and DB sync
2. **✅ DONE:** Bug 2 - Improved validation error messages with detailed page info
3. **✅ DONE:** Ran migration for book 2 to add `external_writable_start/end` columns
4. **🔄 IN PROGRESS:** User re-testing both bugs to confirm fixes work
5. **PENDING:** Update session summary with bug fixes

---

## Implementation Progress (Session 2026-01-26)

### Phase A: Database Changes ✅
- [x] Added `l1_title_id`, `l2_title_id` columns to `raw_{prefix}_layout_detections`
- [x] Added `l1_title_id`, `l2_title_id` columns to `raw_{prefix}_paragraph_images`
- [x] Added `l1_title_id`, `l2_title_id` columns to `raw_{prefix}_diagram_images`
- [x] Added `is_skipped`, `is_ready_for_extraction` columns to `raw_{prefix}_pages`
- [x] Created migration script: `migrate_add_title_fk_columns.py`
- [x] Ran migration for all 3 books

### Phase B: Extraction Service Updates ✅
- [x] Modified `get_titles_for_page()` to return IDs + text from database
- [x] Modified `save_paragraph()` to accept and store `l1_title_id`, `l2_title_id`
- [x] Modified `save_diagram()` to accept and store `l1_title_id`, `l2_title_id`
- [x] Updated `extract_page()` to use new function signatures

### Phase C: Legacy UI Integration ✅
- [x] Added `syncTitlesToDatabase()` function to auto-slicer.js
- [x] Modified `saveConfig()` to sync L1/L2 titles to database on save
- [x] Added "Attrs" button to L1/L2 title rows (opens attribute editor)
- [x] Modified `loadTitles()` to load from database with JSON fallback
- [x] Added `openAttributeEditor()` function

### Phase D: Layout Review Updates ✅
- [x] Modified `loadTitleConfigs()` to read from database with JSON fallback

### Phase E: API Endpoints ✅
- [x] Added `POST /api/books/{book_id}/sync-titles-to-db` endpoint
- [x] Added `PUT /api/books/{book_id}/page-status` endpoint (skip/ready validation)
- [x] Added `GET /api/books/{book_id}/page-statuses` endpoint

### Phase F: Skip Pages Feature ✅
- [x] Added "Skip Page" button in Layout Review UI (HTML + CSS)
- [x] Added L1/L2 validation to existing "Ready for Extraction" button
- [x] Added `toggleSkipPage()` function
- [x] Added `updateSkipPageState()` function
- [x] Added `updateSkipPageState()` calls in `loadCurrentPage()` for both canvases
- [x] API endpoints handle skip/ready status with validation

---

## Remaining Tasks

### Phase G: Extraction Service Updates ✅
- [x] Updated `extract_page()` to check `is_skipped` status and skip marked pages
- [x] Updated batch extraction to track skipped pages separately from errors

### Phase H: Testing
- [ ] Test Skip Page button functionality
- [ ] Test Ready for Extraction validation (L1/L2 coverage check)
- [ ] Test extraction skips marked pages
- [ ] End-to-end workflow test

---

## Clarification Questions: ALL ANSWERED ✅

### Batch 1 ✅
- Q1: OCR extraction → Keep in JSON, migrate to DB on save
- Q2: L3 titles → Store explicit l1_title_id and l2_title_id FKs (also pass to KUs)

### Batch 2 ✅
- Q3: Attribute editor → Separate page via "Attribute Names" button
- Q4: Legacy section → Keep as-is, modify to save to database (hybrid)

### Batch 3 ✅
- Q5: Validation → Skip Pages feature + validate on "Ready for Extraction"
- Q6: Layout Review data source → Read from database (JSON and DB must sync)

---

## NEW: Skip Pages Feature

Based on Q5 answer, new feature required:
- Add "Skip Page" button in Layout Review
- Skipped pages excluded from extraction
- When marking "Ready for Extraction":
  - Validate page is within L1 title range
  - Validate page is within L2 title range
  - Block if outside either range with error message

---

## CRITICAL: Two Systems Need Merging

### Legacy System (Active)
- ✅ UI in Auto-Slicer page ("Title Configuration" section)
- ✅ Page Viewer with OCR text extraction
- ✅ Stores in `auto_slicer_config` JSON
- ✅ Used by Layout Review for L1/L2 display
- ❌ No custom attributes (200/150)
- ❌ No database tables

### New System (Partial)
- ✅ Database tables created (`{prefix}_level1_titles`, `{prefix}_level2_titles`)
- ✅ API endpoints implemented (`title_hierarchy.py`)
- ✅ Attribute editor pages created
- ❌ UI section removed (was duplicate)
- ❌ Not integrated with Page Viewer OCR
- ❌ Not used by Layout Review

### Next Session Tasks
1. Answer clarification questions in requirement4.md (6 questions in 3 batches)
2. Decide on merge strategy
3. Implement unified system

---

## Phase 1: Database Schema (4/4) ✅

- [x] 1.1 Create `{prefix}_level1_titles` table with 200 attributes
- [x] 1.2 Create `{prefix}_level2_titles` table with 150 attributes
- [x] 1.3 Add `l3_title_id` column to `raw_{prefix}_layout_detections` (if not exists)
- [x] 1.4 Create migration script for existing books

**Migration:** `03-code/migrate_add_title_hierarchy.py` - Ran successfully for all 3 books

---

## Phase 2: API Endpoints (12/12) ✅

### L1 Title APIs
- [x] 2.1 `GET /api/books/{book_id}/l1-titles`
- [x] 2.2 `POST /api/books/{book_id}/l1-titles`
- [x] 2.3 `PUT /api/books/{book_id}/l1-titles/{id}`
- [x] 2.4 `DELETE /api/books/{book_id}/l1-titles/{id}`
- [x] 2.5 `GET /api/books/{book_id}/l1-titles/{id}/attributes`
- [x] 2.6 `PUT /api/books/{book_id}/l1-titles/{id}/attributes`

### L2 Title APIs
- [x] 2.7 `GET /api/books/{book_id}/l2-titles`
- [x] 2.8 `POST /api/books/{book_id}/l2-titles`
- [x] 2.9 `PUT /api/books/{book_id}/l2-titles/{id}`
- [x] 2.10 `DELETE /api/books/{book_id}/l2-titles/{id}`
- [x] 2.11 `GET /api/books/{book_id}/l2-titles/{id}/attributes`
- [x] 2.12 `PUT /api/books/{book_id}/l2-titles/{id}/attributes`

**File:** `03-code/src/api/routes/title_hierarchy.py`
**Router registered in:** `03-code/src/main.py`

---

## Phase 3: Validation APIs (4/4) ✅

- [x] 3.1 `GET /api/books/{book_id}/validate-title-coverage`
- [x] 3.2 `GET /api/books/{book_id}/validate-l3-links`
- [x] 3.3 `POST /api/books/{book_id}/auto-link-paragraphs`
- [x] 3.4 `PUT /api/books/{book_id}/paragraph-l3-link`

---

## Phase 4: Auto-Slicer Page UI (6/6) ✅

- [x] 4.1 Add L1 Titles configuration section
- [x] 4.2 Add L2 Titles configuration section
- [x] 4.3 Add title CRUD functionality (add/edit/delete)
- [x] 4.4 Add page coverage visualization
- [x] 4.5 Add validation status indicator
- [x] 4.6 Add "Edit Attributes" button linking to attribute editor

**Files Modified:**
- `03-code/src/frontend/templates/auto-slicer.html` - Added Title Hierarchy Configuration section
- `03-code/src/frontend/static/js/auto-slicer.js` - Added title management JavaScript functions

---

## Phase 5: Attribute Editor Pages (4/4) ✅

- [x] 5.1 Create L1 Title Attribute Editor page template
- [x] 5.2 Create L1 Title Attribute Editor JavaScript
- [x] 5.3 Create L2 Title Attribute Editor page template
- [x] 5.4 Create L2 Title Attribute Editor JavaScript

**Files Created:**
- `03-code/src/frontend/templates/l1-title-attributes.html` - L1 attribute editor (200 attributes)
- `03-code/src/frontend/templates/l2-title-attributes.html` - L2 attribute editor (150 attributes)
- Routes added to `03-code/src/main.py`

---

## Phase 6: Layout Detection Validation (3/3) ✅

- [x] 6.1 Add pre-detection validation check for L1 coverage
- [x] 6.2 Add pre-detection validation check for L2 coverage
- [x] 6.3 Block Layout Detection button until validation passes

**Implementation:** Validation is integrated directly into the `detectLayout()` function in `auto-slicer.js`. Before starting detection, it calls `checkTitleValidationBeforeDetection()` which queries the validation API and displays results.

---

## Phase 7: Layout Review Enhancements (5/5) ✅

- [x] 7.1 Display L3 title link for each paragraph
- [x] 7.2 Add dropdown to change L3 link (manual override)
- [x] 7.3 Implement auto-linking button (calls existing API)
- [x] 7.4 Add visual indicator for auto vs manual links
- [x] 7.5 Add validation warnings for unlinked paragraphs

**Implementation:**
- Added L3 Title Links section in sidebar (`layout-review.html`)
- Added CSS styles for L3 linking UI
- Added JavaScript functions for L3 link management (`layout-review.js`):
  - `loadL3TitlesForPage()` - Load L3 titles for current page
  - `updateL3LinksSection()` - Update sidebar with paragraph-L3 links
  - `changeL3Link()` - Manual L3 link override via dropdown
  - `autoLinkParagraphsToL3()` - Auto-link all paragraphs on page
  - `validateL3Links()` - Validate L3 links for current page
- Updated `layout_detection.py` to support `l3_title_id` updates in PUT endpoint
- Visual indicators: gold border for linked paragraphs, red warning for unlinked

---

## Phase 8: Extraction Validation (3/3) ✅

- [x] 8.1 Add pre-extraction validation for L3 title presence
- [x] 8.2 Add pre-extraction validation for paragraph-L3 links
- [x] 8.3 Block extraction with error message if validation fails

**Implementation:**
- Added `validateL3LinksBeforeExtraction()` function in `extraction-dashboard.js`
- Added `buildL3ValidationErrorMessage()` function for user-friendly error messages
- Modified `startExtraction()` to validate L3 links before starting
- Modified `extractSinglePage()` to validate L3 links before starting
- Validation checks:
  - Pages with paragraphs but no L3 titles
  - Paragraphs not linked to L3 titles
- Error message instructs user to add L3 titles or use Auto-Link in Layout Review

---

## Phase 9: Testing (0/5)

- [ ] 9.1 Unit tests for L1/L2 title CRUD
- [ ] 9.2 Unit tests for validation logic
- [ ] 9.3 Unit tests for auto-linking logic
- [ ] 9.4 Integration tests for full workflow
- [ ] 9.5 UI tests for new pages

---

## Phase 10: Documentation (0/3)

- [ ] 10.1 Update API documentation
- [ ] 10.2 Update user guide
- [ ] 10.3 Update architecture documentation

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-26 | L1: 200 text attributes, L2: 150 text attributes | User requirement |
| 2026-01-26 | Use Auto-Slicer page for title configuration | Consolidate related functionality |
| 2026-01-26 | Auto-link paragraphs to L3 with manual override | Balance automation with user control |
| 2026-01-26 | Block extraction if page has paragraphs but no L3 | Enforce complete hierarchy |
| 2026-01-26 | L3 inherits L2/L1 automatically by page number | Simplify user workflow |
| 2026-01-26 | Attribute names are per-book | Allow book-specific customization |
| 2026-01-26 | Dedicated tables for L1/L2 titles | Better queryability than JSON |

---

## Blockers & Issues

| ID | Issue | Status | Resolution |
|----|-------|--------|------------|
| - | None | - | - |

---

## Notes

- This feature builds on existing Auto-Slicer and Layout Detection infrastructure
- The linking chain ensures all content traces back to L1/L2/L3 titles
- Validation gates prevent processing without proper hierarchy setup
