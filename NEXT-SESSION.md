# Next Session - Bug Fixes Required

**Last Updated:** 2026-01-23
**Session:** Continuation of Session 15 (KU Creation Feature)

---

## Outstanding Bugs to Fix

### Bug 1: Extraction Page - "Start Extraction" Button Shows Claude Warning
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issue:** When clicking "Start Extraction", user sees a warning about "Batch mode 50% discount of Claude"
**Expected:** The Extraction page should ONLY run Surya OCR to extract text from paragraphs and store images in raw tables. Claude analysis should NOT be triggered here.
**Root Cause:** The extraction-dashboard.js still has the API mode selector and references to Claude batch/direct modes
**Fix Required:** 
- Remove the API mode selector from extraction page
- Extraction should ONLY call `/api/extraction/{book_id}/extract` which runs Surya OCR
- Claude analysis ("Execute Diagram Analysis") should be a separate button on the Pipeline page

**Reference:** Per requirements Q17-Q18:
- Q17: Keep extraction service unchanged (Surya OCR only)
- Q18: "Execute Diagram Analysis" processes all types in raw_diagram_images (this is Claude)

---

### Bug 2: Pipeline Page - Missing "Execute Diagram Analysis" Button
**Location:** Pipeline Dashboard (`/pipeline-dashboard`)
**Issue:** Cannot find the button to execute Claude analysis on diagrams
**Expected:** Per requirements Q18 and Q19, Pipeline page should have:
1. "Create Knowledge Units" button (exists) - creates KU records from raw tables
2. "Execute Diagram Analysis" button (MISSING) - sends diagrams to Claude for text extraction
**Fix Required:** Add "Execute Diagram Analysis" button to Pipeline page that:
- Processes ALL types in raw_diagram_images (diagram, table, equation, list_*, question, answer)
- Retrieves images from raw tables using attr12_value references
- Sends to Claude for analysis
- Stores results in knowledge_units table

---

### Bug 3: Pipeline Page - Missing Header Navigation
**Location:** Pipeline Dashboard (`/pipeline-dashboard`)
**Issue:** The Pipeline page has no top navigation header like other pages
**Expected:** All pages should have consistent header with navigation links:
- Upload → Auto-Slicer → Extraction → Pipeline → Library → etc.
**Fix Required:** Add the standard top-nav header to pipeline-dashboard.html

---

### Bug 4: Pipeline Page - Should Remember Last Selected Book
**Location:** Pipeline Dashboard (`/pipeline-dashboard`)
**Issue:** When navigating to Pipeline page, no book is selected by default
**Expected:** Pipeline page should remember the last selected book (from URL parameter or localStorage)
**Fix Required:**
- Check URL for `?book_id=X` parameter
- If present, auto-select that book and load its data
- Optionally store last selected book in localStorage

---

## Files to Modify

1. **03-code/src/frontend/templates/extraction-dashboard.html**
   - Remove API mode selector (batch/direct dropdown)
   - Update button text to clarify it's OCR extraction only

2. **03-code/src/frontend/static/js/extraction-dashboard.js**
   - Remove Claude-related code from startExtraction()
   - Remove API mode references

3. **03-code/src/frontend/templates/pipeline-dashboard.html**
   - Add top navigation header
   - Add "Execute Diagram Analysis" button

4. **03-code/src/frontend/static/js/pipeline-dashboard.js** (or inline script)
   - Add function for Execute Diagram Analysis
   - Add URL parameter handling for book_id
   - Auto-select book from URL

---

## Requirements Reference

From `02-architecture/KNOWLEDGE-UNIT-CREATION-REQUIREMENTS.md`:

**Q17:** Keep extraction service unchanged, add NEW separate service for "Create Knowledge Units"
- Extraction = Surya OCR only
- KU Creation = separate step

**Q18:** "Execute Diagram Analysis" should process ALL types in raw_diagram_images:
- diagram, table, equation, list_bulleted, list_numbered, list_lettered, question, answer

**Q19:** Pipeline page should show table with:
- Checkbox, Page Number, Thumbnails with layout overlay, Status columns
- Action buttons: "Create Knowledge Units" and "Execute Diagram Analysis"

---

## Current State

- Server running at http://localhost:8888
- KU Creation feature 100% complete (backend)
- UI issues need fixing (bugs above)
- Git commits up to: `6e6c264`

---

## Quick Commands

```powershell
# Start server
cd H:\13-extractor2
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Test pages
# Extraction: http://localhost:8888/extraction-dashboard?book_id=1
# Pipeline: http://localhost:8888/pipeline-dashboard?book_id=1
```
