# Urgent Requirements - Phase 3: Enhanced Layout Review

**Created:** 2026-01-15
**Status:** COMPLETED
**Priority:** URGENT
**Estimated Effort:** ~20-30 hours

---

## Overview

This phase implements critical enhancements to the Layout Review system including:
- GPU-only YOLO enforcement
- Improved region manipulation (move/resize)
- Multi-selection with Ctrl+click
- Region merging and linking features
- Auto-slicer page reorganization
- Auto-save with change history tracking

---

## Implementation Progress Tracking

**IMPORTANT:** Update this section every ~50 lines of code.

| Task | Status | Lines Written | Last Updated |
|------|--------|---------------|--------------|
| 3.1 GPU-Only YOLO | DONE | ~25 | 2026-01-15 |
| 3.2 Region Move (Corner Only) | DONE | ~80 | 2026-01-15 |
| 3.3 Region Resize Fix | DONE | ~50 | 2026-01-15 |
| 3.4 Multi-Select (Ctrl+Click) | DONE | ~130 | 2026-01-15 |
| 3.5 Merge Regions | DONE | ~170 | 2026-01-15 |
| 3.6 Link to L3 Title | DONE | ~180 | 2026-01-15 |
| 3.7 Diagram-Paragraph Linking | DONE | ~50 | 2026-01-15 |
| 3.8 L1/L2 Title Display | DONE | ~80 | 2026-01-15 |
| 3.9 Auto-Slicer Reorganization | DONE | ~130 | 2026-01-15 |
| 3.10 Auto-Save + History | DONE (existing) | ~0 | 2026-01-15 |
| 3.11 Ready for Extraction | DONE | ~120 | 2026-01-15 |

**Total Lines Written:** ~1015
**Last Session:** 2026-01-15

---

## Detailed Requirements

### 3.1 GPU-Only YOLO Enforcement

**Priority:** HIGH
**Estimated Lines:** ~50

**Requirement:**
- YOLO model MUST run on GPU only, never on CPU
- If GPU is occupied by another model (Surya, EasyOCR), show error message
- Error message should instruct user to free GPU via Library page or new GPU section
- Do NOT auto-unload other models - let user decide

**Implementation:**
1. Modify `layout_detection_service.py`:
   - Remove CPU fallback in `load_model()` method (lines 253-256)
   - If GPU not available or insufficient memory, return False with clear error
2. Modify `layout_detection.py` API:
   - Return HTTP 503 with message: "GPU not available. Please unload other models from the GPU Management section."

**Files to Modify:**
- `03-code/src/services/layout_detection_service.py`
- `03-code/src/api/routes/layout_detection.py`

---

### 3.2 Region Move - Corner Only with Icon

**Priority:** HIGH
**Estimated Lines:** ~100

**Requirement:**
- RESTRICT region movement to ONLY work when clicking top-left corner
- Add a visual move icon (e.g., 4-arrow icon) in the top-left corner of each region
- Clicking anywhere else on the region should NOT initiate move
- Icon should be visible on hover or always visible (small, non-intrusive)

**Implementation:**
1. Modify `layout-review.js`:
   - Update `handleCanvasMouseDown()` to check if click is near top-left corner
   - Define "corner zone" as ~20px from top-left corner
   - Only set `state.isDragging = true` if click is in corner zone
2. Modify `drawRegion()` function:
   - Draw a small move icon (4-arrow or grip icon) at top-left corner
   - Icon size: ~16x16 pixels
   - Use contrasting color for visibility

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`

---

### 3.3 Region Resize Fix

**Priority:** HIGH
**Estimated Lines:** ~80

**Requirement:**
- Investigate and fix resize functionality (currently may be broken)
- Keep resize handles on ALL 4 corners
- User must click NEAR a corner (within ~15px) to initiate resize
- Provide visual feedback when hovering near resize corners (cursor change + highlight)
- Resize should STOP when user releases mouse button

**Implementation:**
1. Investigate current resize code in `layout-review.js`:
   - Check `getResizeHandle()` function
   - Check `handleCanvasMouseMove()` for resize logic
   - Check `handleCanvasMouseUp()` for resize completion
2. Fix issues found:
   - Ensure resize handles are drawn clearly
   - Ensure cursor changes to resize cursor when near corners
   - Ensure mouseup properly ends resize operation
3. Add visual feedback:
   - Highlight corner on hover (small circle or square)
   - Change cursor to appropriate resize cursor (nwse-resize, nesw-resize, etc.)

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`

---

### 3.4 Multi-Select with Ctrl+Click

**Priority:** HIGH
**Estimated Lines:** ~150

**Requirement:**
- Allow selecting multiple regions by holding Ctrl and clicking
- Similar to PowerPoint multi-selection behavior
- Visual indicator: Selected regions get thicker/different colored border (bright yellow or white dashed)
- Clicking without Ctrl deselects all and selects only clicked region
- Clicking on empty space deselects all

**Implementation:**
1. Modify `layout-review.js`:
   - Add `state.selectedRegions = []` array (instead of single `state.selectedRegion`)
   - Update `handleCanvasMouseDown()`:
     - If Ctrl held: add/toggle region in `selectedRegions` array
     - If Ctrl not held: clear array, select only clicked region
   - Update `drawRegion()`:
     - Check if region is in `selectedRegions` array
     - If selected: draw with thicker border (4px) and different color (yellow #FFD700)
2. Update right-click context menu:
   - Show count in header: "3 regions selected"
   - Enable/disable menu options based on selection

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/frontend/templates/layout-review.html`

---

### 3.5 Merge Regions

**Priority:** HIGH
**Estimated Lines:** ~120

**Requirement:**
- "Merge" option in right-click menu
- Only appears when ALL selected regions have the SAME class
- Merging creates ONE new region with bounding box containing all selected regions
- Original regions are deleted, replaced by merged region
- Merged region inherits the common class

**Implementation:**
1. Modify right-click menu in `layout-review.html`:
   - Add "Merge Regions" option
   - Show/hide based on selection validity
2. Modify `layout-review.js`:
   - Add `canMergeRegions()` function:
     - Returns true if 2+ regions selected AND all same class
   - Add `mergeSelectedRegions()` function:
     - Calculate bounding box: min(x), min(y), max(x+width), max(y+height)
     - Create new region with bounding box dimensions
     - Delete original regions from DB
     - Add merged region to DB
     - Update UI
3. Add API endpoint (if needed):
   - POST `/api/auto-slicer/{book_id}/merge-regions`
   - Body: `{ region_ids: [1, 2, 3], merged_class: "paragraph" }`

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/frontend/templates/layout-review.html`
- `03-code/src/api/routes/layout_detection.py`

---

### 3.6 Link to L3 Title

**Priority:** HIGH
**Estimated Lines:** ~150

**Requirement:**
- "Link to L3 Title" option in right-click menu
- Appears for any selection (single or multiple regions)
- L3 titles come from:
  - YOLO-detected regions with class "Title L3"
  - User-created regions manually set to "Title L3" class
- Selection flow:
  1. User selects region(s)
  2. Right-click → "Link to L3 Title"
  3. Cursor changes to "linking mode"
  4. User clicks on a "Title L3" region on canvas
  5. Link is created and saved to DB
- Visual indicator: Show link with line or badge

**Implementation:**
1. Modify `layout-review.js`:
   - Add `state.linkingToL3 = false` flag
   - Add `state.regionsToLinkToL3 = []` array
   - Update context menu handler for "Link to L3 Title"
   - Update `handleCanvasMouseDown()` to handle L3 linking mode
   - Add `linkRegionsToL3Title()` function
2. Modify DB schema:
   - Add `l3_title_id` column to layout_detections table (foreign key to another region)
   - Or use separate linking table
3. Add API endpoint:
   - POST `/api/auto-slicer/{book_id}/link-to-l3`
   - Body: `{ region_ids: [1, 2, 3], l3_title_id: 5 }`

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/frontend/templates/layout-review.html`
- `03-code/src/api/routes/layout_detection.py`
- `03-code/src/database/` (if schema change needed)

---

### 3.7 Diagram-Paragraph Linking Enhancement

**Priority:** HIGH
**Estimated Lines:** ~100

**Requirement:**
- Multiple diagrams (up to 5) can be linked to ONE paragraph
- Each paragraph can have 0-5 diagrams linked
- Each diagram can be linked to only ONE paragraph
- Existing linking system should be enhanced to support this cardinality
- Visual indicator: Show links clearly on canvas

**Implementation:**
1. Review existing linking code in `layout-review.js`
2. Modify `linkRegions()` function:
   - Check if paragraph already has 5 diagrams → show error
   - Check if diagram is already linked → ask to re-link or cancel
3. Modify DB schema if needed:
   - Ensure `layout_reference_links` table supports multiple diagrams per paragraph
4. Update visual indicators:
   - Show count badge on paragraph: "D:3" (3 diagrams linked)
   - Show "L" badge on linked diagrams

**Files to Modify:**
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/api/routes/layout_detection.py`

---

### 3.8 L1/L2 Title Display in Layout Review

**Priority:** MEDIUM
**Estimated Lines:** ~80

**Requirement:**
- Show L1/L2 titles from auto-slicer config in Layout Review page
- Display in fixed header bar at top of page
- Read-only display (user cannot edit from Layout Review)
- Format: "L1: [Title] | L2: [Title]" based on current page number
- Store L1/L2 info with regions when extracting to knowledge units

**Implementation:**
1. Modify `layout-review.html`:
   - Add header bar section for title display
   - Style: fixed position, full width, dark background
2. Modify `layout-review.js`:
   - Fetch auto-slicer config on page load
   - Extract L1/L2 titles for current page based on page ranges
   - Update title display when navigating pages
3. Modify API:
   - Ensure `/api/auto-slicer/{book_id}/config` returns title information

**Files to Modify:**
- `03-code/src/frontend/templates/layout-review.html`
- `03-code/src/frontend/static/js/layout-review.js`

---

### 3.9 Auto-Slicer Page Reorganization

**Priority:** MEDIUM
**Estimated Lines:** ~200

**Requirement:**
- Reorganize auto-slicer page sections in this order:
  1. Book Selection
  2. L1/L2/L3 Titles Configuration
  3. GPU Model Management (moved from Library page)
  4. Layout Detection (page range + YOLO classes + Detect button)
  5. Run OCR

- Move page range controls from top to Layout Detection section
- GPU Model Management should show:
  - Load/Unload buttons for Surya, EasyOCR, YOLO
  - Status indicators (loaded/not loaded)
  - VRAM usage display

**Implementation:**
1. Modify `auto-slicer.html`:
   - Reorder sections as specified
   - Add GPU Model Management section (copy from library.html)
   - Move page range inputs to Layout Detection section
2. Modify `auto-slicer.js`:
   - Add GPU management functions (copy from library.js)
   - Update section toggle logic if needed

**Files to Modify:**
- `03-code/src/frontend/templates/auto-slicer.html`
- `03-code/src/frontend/static/js/auto-slicer.js`

---

### 3.10 Auto-Save with Change History

**Priority:** HIGH
**Estimated Lines:** ~200

**Requirement:**
- ALL changes auto-save immediately (no confirm buttons needed)
- Remove "Confirm Classes" and "Confirm Regions" buttons
- Save FULL change history for fine-tuning:
  - Every move, resize, class change, delete, merge, link operation
  - Store in separate history table
- History record format:
  - region_id, change_type, old_value, new_value, timestamp, user_session

**Implementation:**
1. Create new DB table `layout_change_history`:
   ```sql
   CREATE TABLE layout_change_history (
     id SERIAL PRIMARY KEY,
     book_id INTEGER NOT NULL,
     region_id INTEGER,
     change_type VARCHAR(50),  -- 'move', 'resize', 'class_change', 'delete', 'merge', 'link'
     old_value JSONB,
     new_value JSONB,
     page_number INTEGER,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```
2. Modify `layout-review.js`:
   - Remove confirm button logic
   - Every operation calls API immediately
   - Add `saveChangeHistory()` function that logs changes
3. Add API endpoint:
   - POST `/api/auto-slicer/{book_id}/log-change`

**Files to Modify:**
- `03-code/migrate_add_change_history.py` (new file)
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/frontend/templates/layout-review.html`
- `03-code/src/api/routes/layout_detection.py`

---

### 3.11 Ready for Extraction Button

**Priority:** HIGH
**Estimated Lines:** ~100

**Requirement:**
- Add "Ready for Extraction" button per page
- When clicked, marks page as ready in DB
- Extraction system will ONLY process regions from "ready" pages
- Visual indicator: Button turns green when page is marked ready
- Can toggle: click again to un-mark

**Implementation:**
1. Modify DB:
   - Add `ready_for_extraction` boolean column to page tracking
   - Or add to `layout_detection_config` JSON
2. Modify `layout-review.html`:
   - Add "Ready for Extraction" button in page controls
3. Modify `layout-review.js`:
   - Add `toggleReadyForExtraction()` function
   - Update button state based on DB value
4. Add API endpoint:
   - POST `/api/auto-slicer/{book_id}/set-page-ready`
   - Body: `{ page_number: 5, ready: true }`

**Files to Modify:**
- `03-code/src/frontend/templates/layout-review.html`
- `03-code/src/frontend/static/js/layout-review.js`
- `03-code/src/api/routes/layout_detection.py`

---

## UI Changes Summary

### Layout Review Page - Header Redesign

**Current:** Single toolbar row with buttons
**New:** Two-row header:

```
Row 1: [L1: Title Here] | [L2: Subtitle Here] | Page: 5/100 | [< Prev] [Next >]
Row 2: [Select] [Draw] [Link] | Zoom: [10%] | [Ready for Extraction ✓]
```

### Layout Review Page - Sidebar Changes

**Current:** Shows class dropdown and region details
**New:** Minimize or remove sidebar (classes shown on canvas)
- Keep only essential buttons if needed
- Or move all controls to header rows

### Right-Click Context Menu

**New Options:**
```
[3 regions selected]
─────────────────────
Change Class      →  [submenu with classes]
─────────────────────
Merge Regions        (only if same class)
Link to L3 Title
Link Diagram to Paragraph  (only if diagram+paragraph selected)
─────────────────────
Delete Region
Permanently Ignore Similar
```

---

## Database Changes Summary

### New Table: `layout_change_history`

```sql
CREATE TABLE layout_change_history (
  id SERIAL PRIMARY KEY,
  book_id INTEGER NOT NULL,
  region_id INTEGER,
  change_type VARCHAR(50),
  old_value JSONB,
  new_value JSONB,
  page_number INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Modified: `layout_detections` table

Add columns:
- `l3_title_id INTEGER` - FK to another region (L3 title)
- `ready_for_extraction BOOLEAN DEFAULT FALSE` - per-page flag (or store in config)

---

## Files to Create

| File | Purpose |
|------|---------|
| `migrate_add_change_history.py` | Database migration for history table |

## Files to Modify

| File | Changes |
|------|---------|
| `layout_detection_service.py` | GPU-only enforcement |
| `layout_detection.py` | New API endpoints, error handling |
| `layout-review.js` | Multi-select, merge, linking, auto-save |
| `layout-review.html` | Header redesign, new buttons |
| `auto-slicer.html` | Page reorganization |
| `auto-slicer.js` | GPU management functions |

---

## Testing Checklist

- [ ] YOLO fails gracefully when GPU occupied
- [ ] Region move only works from top-left corner
- [ ] Region resize works from all 4 corners
- [ ] Ctrl+click adds to selection
- [ ] Merge creates correct bounding box
- [ ] Link to L3 title works with click-to-select
- [ ] Diagram-paragraph linking respects 5-diagram limit
- [ ] L1/L2 titles display correctly
- [ ] Auto-slicer page sections in correct order
- [ ] Changes auto-save without confirm buttons
- [ ] Change history is recorded
- [ ] Ready for Extraction button works per-page

---

## Session Resume Instructions

1. Read this file first
2. Check "Implementation Progress Tracking" table for current status
3. Continue from last incomplete task
4. Update progress every ~50 lines of code
5. If context runs out, new session should read this file to continue

---

## NEXT: Phase 3B - Extract Knowledge Units

This phase (3A) is **COMPLETE**.

The next phase is **Phase 3B: Extract Knowledge Units** which builds on this work.

**See:**
- Requirements: `02-architecture/PHASE3-EXTRACTION-URGENT.md`
- Progress: `02-architecture/PHASE3-EXTRACTION-PROGRESS.md`

---
