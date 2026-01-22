# Next Session - Bug Fixes

**Last Updated:** 2026-01-23
**Session:** Session 17 - Extraction Dashboard Fixes

---

## Bugs Fixed This Session (8-11)

| Bug | Description | Status |
|-----|-------------|--------|
| 8 | Extract This Page causes system freeze | ✓ Fixed |
| 9 | Preview image not available | ✓ Fixed |
| 10 | Page preview layout - full width | ✓ Fixed |
| 11 | Missing vertical scroll | ✓ Fixed |

---

## Outstanding Bugs for Next Session (12-13)

### Bug 12: Page Preview Should Show Regions
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issue:** The page preview shows only the raw page image without the detected regions (colored rectangles)
**Expected:** Page preview should display the page WITH region overlays (like Layout Review page)
**Fix Required:** 
- Reuse the existing code from Layout Review page (`layout-review.js`)
- Use canvas to draw the page image with region boxes overlaid
- Reference: `03-code/src/frontend/static/js/layout-review.js` has the region drawing code

---

### Bug 13: Extraction Results Not Displayed
**Location:** Extraction Dashboard (`/extraction-dashboard`)
**Issue:** After extraction completes, no paragraphs or classes are shown in the results columns
**Root Cause:** The API endpoint `/api/extraction/{book_id}/page/{page_number}/results` may not be returning data correctly, or the raw tables don't have data
**Fix Required:**
1. Debug the API endpoint to verify it returns data
2. Check if raw_paragraph_images and raw_diagram_images tables have data after extraction
3. Verify the loadPageExtractionResults() function is parsing the response correctly

**API Endpoint:** `GET /api/extraction/{book_id}/page/{page_number}/results`
**Tables to Check:**
- `raw_{prefix}_paragraph_images`
- `raw_{prefix}_diagram_images`

---

## Files to Modify for Next Session

1. **03-code/src/frontend/static/js/extraction-dashboard.js**
   - Add canvas-based region drawing (copy from layout-review.js)
   - Debug loadPageExtractionResults() function

2. **03-code/src/frontend/templates/extraction-dashboard.html**
   - Change page preview from `<img>` to `<canvas>` for region overlay support

3. **03-code/src/api/routes/extraction.py**
   - Debug get_page_extraction_results() endpoint
   - Verify SQL queries return correct data

---

## Reference Code from Layout Review

The Layout Review page (`layout-review.js`) has working code for drawing regions on a canvas. Key functions to reuse:
- Region drawing with colored rectangles
- Class-based color coding
- Canvas scaling and positioning

---

## Quick Commands

```powershell
# Start server
cd H:\13-extractor2
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Test page
http://localhost:8888/extraction-dashboard?book_id=1

# Check raw tables (PostgreSQL)
SELECT COUNT(*) FROM raw_book1_paragraph_images;
SELECT COUNT(*) FROM raw_book1_diagram_images;
```

---

## Session Summary

**Bugs Fixed:** 4 (Bugs 8-11)
**Bugs Remaining:** 2 (Bugs 12-13)
**Files Modified:** 
- extraction-dashboard.html (layout, scroll)
- extraction-dashboard.js (image URL, extract function)
- NEXT-SESSION.md (documentation)
