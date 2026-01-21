# Phase 3B: Extract Knowledge Units - Implementation Progress

**Feature:** Extract Knowledge Units from Layout Review regions
**Started:** 2026-01-16
**Status:** ~85% COMPLETE - Core implementation done, UI polish remaining
**Requirements:** See `PHASE3-EXTRACTION-URGENT.md`

---

## CRITICAL: Read First Every Session

**Current Task:** Phase 3B - Extract Knowledge Units
**Requirements Doc:** `02-architecture/PHASE3-EXTRACTION-URGENT.md`
**Status:** Core extraction + Claude decode implemented, testing and UI polish remaining

---

## Implementation Progress Tracking

**IMPORTANT:** Update this section every ~50 lines of code.

| Task | Status | Lines Written | Last Updated |
|------|--------|---------------|--------------|
| 3B.1 Extraction Page Route | COMPLETE | ~30 | 2026-01-18 |
| 3B.2 Page Selection Table UI | COMPLETE | ~480 | 2026-01-18 |
| 3B.3 Ready Validation (orphan check) | COMPLETE | ~120 | 2026-01-18 |
| 3B.4 Extraction Service | COMPLETE | ~400 | 2026-01-18 |
| 3B.5 Paragraph OCR (Surya) | COMPLETE | ~150 | 2026-01-18 |
| 3B.6 Diagram Image Extraction | COMPLETE | ~120 | 2026-01-18 |
| 3B.7 L3 Title OCR | COMPLETE | ~80 | 2026-01-18 |
| 3B.8 Summary Table UI | COMPLETE (UI) | ~100 | 2026-01-16 |
| 3B.9 Claude Batch Service | COMPLETE | ~700 | 2026-01-18 |
| 3B.10 Decode Button & Status | COMPLETE (UI) | ~50 | 2026-01-16 |
| 3B.11 Preview Feature UI | COMPLETE (UI) | ~150 | 2026-01-16 |
| 3B.12 Prompt Management | COMPLETE | ~80 | 2026-01-16 |
| 3B.13 Book Settings Prompts | COMPLETE | ~120 | 2026-01-18 |
| 3B.14 Progress Bar & WebSocket | COMPLETE (UI) | ~50 | 2026-01-16 |
| 3B.15 Auto-Slicer Button | COMPLETE | ~30 | 2026-01-18 |

**Total Lines Written:** ~2,660
**Last Session:** 2026-01-18

---

## Overall Progress

| Phase | Status | Hours Est. | Hours Spent | Completion |
|-------|--------|------------|-------------|------------|
| Phase 1: Core Detection | COMPLETE | 36h | ~10h | 100% |
| Phase 2: Review Interface | COMPLETE | 36h | ~14h | 95% |
| Phase 3A: Enhanced Layout Review | COMPLETE | 25h | ~20h | 100% |
| **Phase 3B: Extract Knowledge Units** | **~85% COMPLETE** | **40h** | **~12h** | **85%** |
| Phase 4: Fine-Tuning (Optional) | NOT STARTED | 36h | 0h | 0% |
| Phase 5: Remaining Phase 2 (Optional) | NOT STARTED | 12h | 0h | 0% |
| Phase 6: Advanced Features (Optional) | NOT STARTED | 44h | 0h | 0% |
| Phase 7: Export & Polish (Optional) | NOT STARTED | 40h | 0h | 0% |

---

## Files Created

| File | Status | Lines | Purpose |
|------|--------|-------|---------|
| `extract-knowledge.html` | COMPLETE | ~300 | Page template |
| `extract-knowledge.js` | COMPLETE | ~400 | Page JavaScript |
| `extraction.py` (routes) | COMPLETE | ~450 | API endpoints |
| `extraction_service.py` | COMPLETE | ~400 | Surya OCR business logic |
| `claude_batch_service.py` | COMPLETE | ~700 | Claude Batch + Direct API |
| `gpu.py` (routes) | COMPLETE | ~100 | GPU management endpoints |

## Files Modified

| File | Status | Changes |
|------|--------|---------|
| `main.py` | COMPLETE | Added extraction routes |
| `auto-slicer.html` | COMPLETE | Added "Extract Knowledge Units" button |
| `auto-slicer.js` | COMPLETE | Added navigation + thumbnail fix |
| `layout-review.js` | COMPLETE | Orphan validation, delete fix, L1/L2 fix |
| `layout-review.html` | COMPLETE | Removed "Confirm Classes" button |
| `layout_detection.py` | COMPLETE | Delete also removes links |
| `book-settings.html` | COMPLETE | Added prompts section (6 types) |
| `book-settings.js` | COMPLETE | Added prompt load/save/reset |
| `diagram_context.py` | COMPLETE | Use extraction_prompts from config |

---

## API Endpoints Created

| Endpoint | Method | Status | Purpose |
|----------|--------|--------|---------|
| `/extract-knowledge` | GET | COMPLETE | Render page |
| `/api/extraction/{book_id}/ready-pages` | GET | COMPLETE | Get ready pages |
| `/api/extraction/{book_id}/extract` | POST | COMPLETE | Start extraction |
| `/api/extraction/{book_id}/summary` | GET | COMPLETE | Summary by L3 |
| `/api/extraction/{book_id}/decode-batch` | POST | COMPLETE | Start batch decode |
| `/api/extraction/{book_id}/decode-direct` | POST | COMPLETE | Start direct decode |
| `/api/extraction/{book_id}/batch-status` | GET | COMPLETE | Batch status |
| `/api/extraction/{book_id}/batch-results` | POST | COMPLETE | Retrieve batch results |
| `/api/extraction/{book_id}/preview-decode` | POST | COMPLETE | Preview decode |
| `/api/extraction/{book_id}/save-decode` | POST | COMPLETE | Save preview result |
| `/api/extraction/{book_id}/prompts` | GET/PUT | COMPLETE | Manage prompts |
| `/api/extraction/{book_id}/diagrams-for-preview` | GET | COMPLETE | List diagrams |
| `/api/extraction/{book_id}/diagram-image/{id}` | GET | COMPLETE | Get diagram image |

---

## Remaining Tasks (15%)

| Task | Description | Priority |
|------|-------------|----------|
| 3B.8 | Summary Table - Test with real data, fix paragraph counts | HIGH |
| Testing | End-to-end test of extraction flow | HIGH |
| 3B.10 | Direct decode progress - Add real-time UI updates | MEDIUM |
| 3B.11 | Preview Feature - Wire up UI to APIs | MEDIUM |
| 3B.14 | Progress bar - Add to extraction process | LOW |
| Polish | Error handling, loading indicators | LOW |

---

## Session Log

### Session 1 (2026-01-16)
- Created requirements document `PHASE3-EXTRACTION-URGENT.md`
- Created progress tracking document `PHASE3-EXTRACTION-PROGRESS.md`
- Requirements finalized via Q&A (13 batches, 26 questions)
- Ready for implementation

### Session 2 (2026-01-16) - Layout Review Enhancements
**Focus:** Bug fixes and enhancements to Layout Review page (Phase 3A refinements)
- L3 Link dashed lines fix
- Z-Index system for overlapping regions
- Split Region feature
- Context menu class filtering
**Total New Lines:** ~400

### Session 3 (2026-01-18) - Phase 3B Core Implementation
**Focus:** Full extraction pipeline implementation

**New Files Created:**
- `extraction.py` - API routes for all extraction endpoints
- `extraction_service.py` - Core extraction logic with Surya OCR
- `claude_batch_service.py` - Claude Batch API + Direct API integration

**Key Features Implemented:**
1. **Extraction Service** - Paragraph OCR at 600 DPI with Surya
2. **Claude Batch Service** - Both batch (50% cost) and direct modes
3. **Parent Paragraph Context** - Included in all decode prompts
4. **Orphan Validation** - Block "Ready" if diagrams lack parent
5. **Book Settings Prompts** - 6 textarea inputs for each class type
6. **Unified Prompts** - Removed duplicate "Diagram Analysis Prompts"

**Bug Fixes:**
- Deleted region still showing as orphan (backend + frontend fix)
- L1/L2 titles empty (API URL and data format fix)
- Thumbnails appearing black (endpoint and field name fix)
- Right-click on linked diagram premature message (left-click only)

**Merged Workflows:**
- "Ready for Extraction" now also sets `classesConfirmed`
- Removed redundant "Confirm Classes" button

**Total New Lines:** ~1,600

---

## Key Implementation Details

### Claude Batch Service (`claude_batch_service.py`)
```python
# Functions implemented:
submit_batch(book_id, diagram_ids)      # Async batch processing (50% cost)
check_batch_status(book_id, batch_id)   # Poll batch status
retrieve_batch_results(book_id, batch_id)  # Download and save results
decode_single_diagram(book_id, diagram_id)  # Direct decode
start_direct_decode(book_id, diagram_ids)   # Process all directly
preview_decode(book_id, diagram_id, prompt)  # Test prompt
save_decode_result(book_id, diagram_id, content)  # Save result

# Each decode request includes:
# - Diagram/table/equation/list image
# - Parent paragraph text (if linked)
# - Per-class prompt from book settings
```

### Extraction Service (`extraction_service.py`)
```python
# Functions implemented:
start_extraction(book_id, page_numbers)  # Main entry point
extract_page(book_id, page_number)       # Process single page
run_surya_ocr(image_data)                # OCR with Surya at 600 DPI
crop_region_image(page_image, region)    # Extract region image
save_paragraph(db, prefix, data)         # Save paragraph to DB
save_diagram(db, prefix, data)           # Save diagram to DB
get_titles_for_page(book_id, page_number)  # L1/L2/L3 lookup
```

### Pipeline Execution Note
```
PIPELINE EXECUTION NOTE:
- First step: Translate paragraphs to English
- Second step: Decode all diagrams with basic prompts before further logic
```

---

## Quick Resume Instructions

1. Read `NEXT-SESSION.md` for session priorities
2. Start server: `cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777`
3. Test at http://localhost:7777/extract-knowledge?book_id=1
4. Check remaining tasks in table above
5. Update progress as you work

---
