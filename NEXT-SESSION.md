# Next Session Task Priority

## Last Updated: 2026-01-21

---

## CRITICAL: Read First Every Session

**Current Feature:** Phase 3D - Extraction Dashboard (COMPLETE)
**Phase 1:** COMPLETE - DocLayout-YOLO Core Detection
**Phase 2:** COMPLETE - Review Interface
**Phase 3A:** COMPLETE - Enhanced Layout Review
**Phase 3B:** ~85% COMPLETE - Extract Knowledge Units
**Phase 3D:** COMPLETE - Extraction Dashboard
**Status:** Dashboard implemented, bug fixes applied

**Progress Tracking:** `02-architecture/PHASE3D-DASHBOARD-PROGRESS.md`
**Phase 3D Requirements:** `02-architecture/PHASE3D-DASHBOARD-REQUIREMENTS.md`

---

## Session 10 Completed (2026-01-21) - Bug Fixes and New Features

### New Features Implemented:

| Feature | Description | Files Modified |
|---------|-------------|----------------|
| Question/Answer Classes | Added to YOLO Detection Classes dropdown | `auto-slicer.html`, `auto-slicer.js` |
| Back to Extraction Button | Navigation link in Layout Review | `layout-review.html`, `layout-review.js` |

### Bug Fixes:

| Bug | Root Cause | Fix |
|-----|------------|-----|
| Link mode not returning to SELECT | `cancelLinkMode()` didn't reset mode | Use `setMode('select')` which calls `cancelLinkMode()` internally |
| Infinite recursion (stack overflow) | `cancelLinkMode()` called `setMode()` which called `cancelLinkMode()` | Removed `setMode()` from `cancelLinkMode()`, updated all callers |
| Deleted region still blocking extraction | Type mismatch in ID comparison (string vs number) | Added `Number()` conversion for all ID comparisons in filter operations |

### Files Modified:

| File | Changes |
|------|---------|
| `auto-slicer.html` | Added Question/Answer checkboxes to YOLO Detection Classes |
| `auto-slicer.js` | Added question/answer to classMap and toggleAllYoloClasses |
| `layout-review.html` | Added "Back to Extraction" navigation link |
| `layout-review.js` | Fixed link mode, delete type safety, added debug logging |

### Commits:

| Hash | Message |
|------|---------|
| `14be4e3` | feat: Add Question/Answer classes, Back to Extraction button, and fix link mode |
| `0267674` | fix: Resolve infinite recursion in cancelLinkMode and setMode |

### Technical Details:

**Link Mode Fix:**
- `setMode()` already calls `cancelLinkMode()` when switching away from link mode
- Removed `setMode('select')` from `cancelLinkMode()` to prevent circular calls
- Updated all places calling `cancelLinkMode()` directly to use `setMode('select')`

**Delete Type Safety Fix:**
- Region IDs from API could be numbers, but compared as strings
- `5 !== "5"` is `true` in JavaScript (strict inequality)
- Added `Number()` conversion: `state.pageRegions.filter(r => Number(r.id) !== deleteId)`

---

## Session 9 Completed (2026-01-19) - Phase 3D Extraction Dashboard

### Major Features Implemented:

| Component | Description | Lines |
|-----------|-------------|-------|
| Dashboard HTML | Full page template with dark theme | ~500 |
| Dashboard JS | All JavaScript functionality | ~520 |
| API Endpoints | 5 new endpoints for dashboard | ~380 |
| Auto-Slicer Integration | Navigation links and button | ~20 |

### New Files Created:

| File | Purpose |
|------|---------|
| `extraction-dashboard.html` | Dashboard page template |
| `extraction-dashboard.js` | Dashboard JavaScript |
| `PHASE3D-DASHBOARD-REQUIREMENTS.md` | Requirements document |
| `PHASE3D-DASHBOARD-PROGRESS.md` | Progress tracking |

### Files Modified:

| File | Changes |
|------|---------|
| `main.py` | Added `/extraction-dashboard` route |
| `extraction.py` | Added dashboard API endpoints |
| `auto-slicer.html` | Added dashboard navigation link |
| `auto-slicer.js` | Updated to navigate to dashboard |
| `NEXT-SESSION.md` | Updated status |

### Dashboard Features:

1. **Layout**: Dark theme, left sidebar thumbnails, right content area
2. **Progress Bars**: Paragraphs OCR (X/Y) + Diagrams Decode (X/Y)
3. **Summary Table**: Counts by L3 title (paragraphs, diagrams, tables, equations, lists, questions, answers)
4. **Diagrams Table**: Thumbnail + Class + Status + Actions (View/Edit/Re-decode)
5. **Modals**: View details, Edit text, Re-decode with prompt editor
6. **API Mode Toggle**: Batch (50% cost) vs Direct (immediate)
7. **WebSocket**: Live progress updates

### API Endpoints Added:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/extraction/{id}/dashboard` | GET | Combined dashboard data |
| `/extraction/{id}/start` | POST | Start extraction with API mode |
| `/extraction/{id}/diagram/{id}/view` | GET | Diagram details |
| `/extraction/{id}/diagram/{id}/edit` | PUT | Update extracted text |
| `/extraction/{id}/diagram/{id}/redecode` | POST | Re-decode with prompt |

### Access Points:

- **Extraction Dashboard:** http://localhost:7777/extraction-dashboard?book_id=1
- **Auto-Slicer:** http://localhost:7777/auto-slicer (with dashboard link in nav)

---

## Session 8 Completed (2026-01-18) - Phase 3B Implementation

### Major Features Implemented:

| Task | Description | Status |
|------|-------------|--------|
| 3B.1 | Extraction Page Route (`/extract-knowledge`) | COMPLETE |
| 3B.2 | Page Selection Table UI | COMPLETE |
| 3B.3 | Ready Validation (orphan diagram check) | COMPLETE |
| 3B.4 | Extraction Service - core business logic | COMPLETE |
| 3B.5 | Paragraph OCR with Surya (600 DPI) | COMPLETE |
| 3B.6 | Diagram/Table/Equation/List image extraction | COMPLETE |
| 3B.7 | L3 Title OCR | COMPLETE |
| 3B.9 | Claude Batch Service - batch + direct decode | COMPLETE |
| 3B.13 | Book Settings prompts section (6 types) | COMPLETE |
| 3B.15 | Auto-Slicer "Extract Knowledge Units" button | COMPLETE |

### New Files Created:

| File | Description |
|------|-------------|
| `extraction.py` | API routes for extraction endpoints |
| `extraction_service.py` | Core extraction logic with Surya OCR |
| `claude_batch_service.py` | Claude Batch API + Direct API integration |
| `extract-knowledge.html` | Extraction page template |
| `extract-knowledge.js` | Extraction page JavaScript |
| `gpu.py` | GPU management API routes |

### Bug Fixes:

| Issue | Fix |
|-------|-----|
| Deleted region still showing as orphan | Backend now deletes associated links; frontend checks API response |
| Duplicate prompts (Diagram Analysis vs Claude Extraction) | Removed old prompts, unified to `extraction_prompts` |
| Right-click on linked diagram showing premature message | Only handle left-clicks in `onMouseDown` |
| L1/L2 titles empty in Layout Review | Fixed API URL and data format conversion |
| Thumbnails appearing black | Fixed endpoint URL and field names |

### Merged Workflows:

- **"Ready for Extraction"** button now also sets `classesConfirmed`
- Removed redundant **"Confirm Classes"** button
- Single button validates orphans + confirms in one click

### Key Implementation Details:

**Claude Batch Service:**
- `submit_batch()` - Async processing via Message Batches API (50% cost)
- `start_direct_decode()` - Immediate processing (full cost)
- `check_batch_status()` / `retrieve_batch_results()` - Polling and retrieval
- Parent paragraph text included in all decode prompts
- Per-class prompts configurable in Book Settings

**Extraction Service:**
- Surya OCR for paragraphs at 600 DPI
- Image cropping for diagrams/tables/equations/lists
- L1/L2/L3 title hierarchy lookup
- WebSocket progress broadcasting

**Pipeline Execution Note (in code):**
- First step: Translate paragraphs to English
- Second step: Decode all diagrams with basic prompts before further logic

---

## NEXT SESSION: Testing and Refinement

### Step 1: Start Server
```bash
cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777
```

### Step 2: Test Recent Fixes

| Test | Steps | Expected |
|------|-------|----------|
| Link Mode | Right-click diagram → Link to Paragraph → Click paragraph | Mode returns to SELECT |
| Delete + Ready | Delete unlinked diagram → Click Ready for Extraction | Should succeed |
| Question/Answer | Check Auto-Slicer YOLO Detection Classes | Question/Answer checkboxes visible |
| Back to Extraction | Check Layout Review navigation | Button visible, links to dashboard |

### Step 3: Pending Tasks

| Priority | Task | Description |
|----------|------|-------------|
| 1 | End-to-end extraction test | Test full workflow with Book ID 1 |
| 2 | Claude Batch API integration | Test batch mode decode |
| 3 | WebSocket live updates | Verify progress updates work |

---

## ACCESS POINTS

- **Layout Review:** http://localhost:7777/layout-review?book_id=1
- **Extraction Dashboard:** http://localhost:7777/extraction-dashboard?book_id=1
- **Extract Knowledge:** http://localhost:7777/extract-knowledge?book_id=1
- **Auto-Slicer:** http://localhost:7777/auto-slicer?book_id=1
- **Book Settings:** http://localhost:7777/book-settings
- **Library (GPU):** http://localhost:7777/library
- **API Docs:** http://localhost:7777/docs

---

## API ENDPOINTS (Phase 3B)

### Extraction APIs:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extraction/{book_id}/ready-pages` | GET | List pages ready for extraction |
| `/api/extraction/{book_id}/prompts` | GET/PUT | Get/set extraction prompts |
| `/api/extraction/{book_id}/summary` | GET | Summary by L3 title |
| `/api/extraction/{book_id}/extract` | POST | Start extraction |
| `/api/extraction/{book_id}/decode-batch` | POST | Start batch decode |
| `/api/extraction/{book_id}/decode-direct` | POST | Start direct decode |
| `/api/extraction/{book_id}/batch-status` | GET | Check batch status |
| `/api/extraction/{book_id}/batch-results` | POST | Retrieve batch results |
| `/api/extraction/{book_id}/preview-decode` | POST | Preview decode single diagram |
| `/api/extraction/{book_id}/diagrams-for-preview` | GET | List diagrams for preview |

---

## KEYBOARD SHORTCUTS (Layout Review)

| Key | Action |
|-----|--------|
| S | Select mode |
| N | Draw new region |
| L | Link mode (diagram→paragraph) |
| V | Toggle view mode |
| A | Previous page |
| D | Next page |
| Del | Delete selected region |
| Ctrl+Click | Multi-select regions |
| Esc | Cancel/deselect |
| + | Zoom in |
| - | Zoom out |
| ? | Show shortcuts panel |

---

## Model Information

**YOLO Model:** `03-code/models/layout_detection/base/doclayout_yolo_docstructbench_imgsz1024.pt`
**Required Packages:** `ultralytics==8.0.196`, `doclayout-yolo`
**VRAM:** ~78 MB when loaded
