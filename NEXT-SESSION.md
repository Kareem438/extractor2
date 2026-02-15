# Next Session Context

**Last Updated:** 2026-02-09
**Primary Reference:** `000-tracking/00-main-steps.md`

---

## TRACKING FRAMEWORK ACTIVE

All task tracking now uses the structured framework in `000-tracking/`.

**At session start, read these files:**

| File | Purpose |
|------|---------|
| `000-tracking/00-main-steps.md` | Master task index — start here |
| `000-tracking/00-tracking-framework.md` | Framework rules and workflow |
| `.kiro/steering/code-review-first.md` | Server commands & code review rules |

For any in-progress tasks in `00-main-steps.md`, also read the requirement, tracking, and testing files listed there.

---

## Files to Read on Session Start

| File | Purpose |
|------|---------|
| `000-tracking/00-main-steps.md` | Master task index |
| `.kiro/steering/code-review-first.md` | CRITICAL: Server commands & code review rules |
| `.kiro/steering/tracking-framework.md` | Tracking framework steering rules |

---

## Quick Commands

```powershell
# Start server (PORT 8888!)
cd H:\13-extractor2
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Restart server
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2; Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Check server health
Invoke-WebRequest -Uri "http://localhost:8888/health" -UseBasicParsing | Select-Object -ExpandProperty Content

# Run migrations for new books
.\venv\Scripts\python.exe 03-code/migrate_add_title_fk_columns.py
.\venv\Scripts\python.exe 03-code/migrate_add_multi_pdf_crossbook.py
```

---

## Project Configuration

- **Location:** `H:\13-extractor2`
- **Database:** `knowledge_extraction_2`
- **Port:** `8888` (NOT 8000!)
- **Virtual Environment:** `H:\13-extractor2\venv`

---

## Requirements Status

| Requirement | Status |
|-------------|--------|
| Req 4 - Title Hierarchy | ✅ Complete (all tests passed) |
| Req 5 - Multi-PDF & Cross-Book | ✅ Complete |
| Req 6 - Delete Book | ✅ Complete |
| Req 7 - KU Grouping & Training | ✅ Design Complete → Tasks Phase |
| Req 8 - YOLO Fine-Tuning | ✅ Complete (all tests passed) |

---

## Key URLs

- Auto-Slicer: http://localhost:8888/auto-slicer?book_id=2
- Extraction Dashboard: http://localhost:8888/extraction-dashboard?book_id=2
- Layout Review: http://localhost:8888/layout-review?book_id=2
- Book Settings: http://localhost:8888/book-settings
