# Next Session - Bug Fixes

**Last Updated:** 2026-01-23
**Session:** Continuation of Session 15 (KU Creation Feature)

---

## Previous Bugs - ALL FIXED ✓

### Bug 1-4: All Fixed (Previous Session)
- Bug 1: Extraction page Claude warning - FIXED
- Bug 2: Pipeline page missing Execute Diagram Analysis button - FIXED
- Bug 3: Pipeline page missing header navigation - FIXED
- Bug 4: Pipeline page should remember last selected book - FIXED

---

## New Bugs - ALL FIXED ✓ (This Session)

### Bug 5: Extraction Page - Left Sidebar Needs Scroll ✓ FIXED
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issue:** The left sidebar with page thumbnails doesn't have a scroll bar when there are many pages
**Fix:** Changed `.sidebar` from `overflow: hidden` to `overflow-y: auto`

---

### Bug 6: Extraction Page - Page-Level Extraction Button ✓ FIXED
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issue:** The "Start OCR Extraction" button only works for all pages, not individual pages
**Fix:** Added "Extract This Page" button in the page preview section (right panel)

---

### Bug 7: Extraction Page - Infinite Loop & Results Display ✓ FIXED
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issues Fixed:**
1. **Infinite Loop:** WebSocket was reconnecting indefinitely. Fixed by only reconnecting when extraction is in progress.
2. **Results Display:** Added new page preview section with:
   - Page image preview on the left
   - Two columns on the right: Paragraphs and Other Classes (diagrams, tables, etc.)
   - Data loaded from raw tables (raw_paragraph_images, raw_diagram_images)
3. **Statistics Moved:** All statistics sections moved to collapsible section at bottom

---

## Files Modified

### HTML Changes (extraction-dashboard.html):
1. Fixed sidebar scroll: `overflow-y: auto`
2. Added new CSS styles for:
   - Page preview section
   - Extraction results columns
   - Collapsible statistics section
   - Extract page button
3. Added new HTML structure:
   - Page preview section with image and results columns
   - Wrapped statistics in collapsible section

### JavaScript Changes (extraction-dashboard.js):
1. Fixed WebSocket reconnection logic (only reconnect during extraction)
2. Added new functions:
   - `toggleStatsSection()` - toggle collapsible statistics
   - `showPagePreview(pageNumber)` - show page image preview
   - `loadPageExtractionResults(pageNumber)` - load results from raw tables
   - `extractSelectedPage()` - extract single page from button

### API Changes (extraction.py):
1. Added `GET /extraction/{book_id}/page/{page_number}/results` - fetch extraction results
2. Added `GET /extraction/{book_id}/paragraph-image/{paragraph_id}` - get paragraph image

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

---

## Testing Checklist

- [ ] Left sidebar scrolls when many pages
- [ ] "Extract This Page" button appears when page selected
- [ ] Page preview shows page image
- [ ] Extraction results show paragraphs and diagrams from raw tables
- [ ] Statistics section is collapsible
- [ ] No infinite loop when extraction completes
