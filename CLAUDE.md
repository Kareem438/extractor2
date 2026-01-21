# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Read PROJECT-CONFIGURATION.md First

**This is a parallel instance of the project.** Before proceeding, understand:
- **Project Path:** `H:\13-extractor2` (NOT `H:\12-extractor`)
- **Database:** `knowledge_extraction_2` (NOT `knowledge_extraction`)
- **Port:** `8888` (NOT `7777`)

See **[PROJECT-CONFIGURATION.md](PROJECT-CONFIGURATION.md)** for full details on this parallel instance configuration.

---

## CRITICAL: System Startup Instructions

**DO NOT improvise or try alternative commands. Execute ONLY the exact commands below using the Bash tool. These commands have been tested and verified to work. Any deviation will cause failures.**

### Step 1: Verify PostgreSQL Service (REQUIRED)
```
Bash(sc query postgresql-x64-16)
```
- PostgreSQL 16 is installed natively on Windows
- Service should show STATE: RUNNING
- If not running, start it: `sc start postgresql-x64-16`
- DO NOT use WSL commands - PostgreSQL runs on Windows now

### Step 2: Verify Database Connection (REQUIRED)
```
Bash(cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()")
```
- Must print "Database OK" before proceeding
- If connection fails, check PostgreSQL service in Step 1

### Step 3: Start FastAPI Server (REQUIRED)
```
Bash(cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8888)
```
- Use `run_in_background=true` parameter when calling Bash tool
- Server runs on port 8888

### Step 4: Verify Server Health (REQUIRED)
```
Bash(ping -n 6 127.0.0.1 >nul && curl -s http://localhost:8888/health)
```
- Expected response: `{"status":"healthy","service":"Knowledge Extraction System","version":"1.0.0"}`

### Access Points (after startup)

**Main Pages:**
- **Library:** http://localhost:8888/library
- **Upload:** http://localhost:8888/upload
- **Settings:** http://localhost:8888/book-settings
- **Auto-slicer:** http://localhost:8888/auto-slicer (accessed via Book Settings)
- **Review Raw:** http://localhost:8888/review-raw
- **Verify Pages:** http://localhost:8888/verify-pages
- **Edit Paragraphs:** http://localhost:8888/edit-paragraphs
- **Edit Diagrams:** http://localhost:8888/edit-diagrams

**Pipeline System:**
- **Pipeline Configuration:** http://localhost:8888/pipeline-config
- **Pipeline Dashboard:** http://localhost:8888/pipeline-dashboard

**API Documentation:**
- **Swagger UI:** http://localhost:8888/docs
- **ReDoc:** http://localhost:8888/redoc

---

## Project Overview

Knowledge Extraction System - A Python-based document processing pipeline that extracts text and images from PDFs using multi-tier OCR (PaddleOCR, Surya, Tesseract) with a FastAPI web interface.

## Common Commands

```bash
# Run tests
pytest 04-tests/ -v

# Run single test file
pytest 04-tests/<test_file>.py -v

# Run with coverage
pytest 04-tests/ --cov=03-code/src --cov-report=html

# Format code
black 03-code/src/

# Lint
flake8 03-code/src/ --max-line-length=100

# Database migrations (run from 03-code/)
cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe migrate_add_<feature>.py

# Worker system migration (REQUIRED once for pipeline features)
cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe migrate_add_worker_system.py

# Start worker process (for Claude pipeline processing)
cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe -m src.worker.main
```

## Database Backup & Restore

### Backup Scripts

Two Python scripts are available for backing up databases without affecting running operations:

#### PostgreSQL Backup
```bash
python "06-PostgreSQL Backup.py"
```
- Creates TWO backup formats in `06-PostgreSQL BACKUP/`:
  - **SQL format** (~600 MB) - Human-readable, easy to restore with psql
  - **Custom format** (~295 MB) - Compressed binary, faster restore with pg_restore
- Automatic timestamping: `knowledge_extraction_2_YYYY-MM-DD_HH-MM-SS.*`
- Safe to run while database is active

#### ChromaDB Backup
```bash
python "07-Chroma Backup.py"
```
- Creates compressed ZIP archive in `07-Chroma BACKUP/`
- Includes SQLite database and all collection data
- Automatic timestamping: `chroma_backup_YYYY-MM-DD_HH-MM-SS.zip`
- 90%+ compression ratio (0.38 MB → 0.03 MB typical)
- Safe to run while ChromaDB is active

### Restore Instructions

**PostgreSQL Restore (SQL format):**
```bash
psql -h localhost -p 5432 -U postgres -d knowledge_extraction_2 < "06-PostgreSQL BACKUP/knowledge_extraction_2_YYYY-MM-DD_HH-MM-SS.sql"
```

**PostgreSQL Restore (Custom format):**
```bash
pg_restore -h localhost -p 5432 -U postgres -d knowledge_extraction_2 "06-PostgreSQL BACKUP/knowledge_extraction_2_YYYY-MM-DD_HH-MM-SS.dump"
```

**ChromaDB Restore:**
1. Stop FastAPI server and any workers
2. Rename/backup existing `chroma_db/` directory
3. Extract backup: `unzip "07-Chroma BACKUP/chroma_backup_YYYY-MM-DD_HH-MM-SS.zip"`
4. Restart server

### Backup Recommendations

- **Before major changes:** Always backup before migrations, schema changes, or bulk operations
- **Regular backups:** Run both scripts daily/weekly depending on data importance
- **Before updates:** Backup before updating dependencies or system components
- **Store off-site:** Copy backup files to external storage or cloud for disaster recovery

## Architecture

```
FastAPI App (03-code/src/main.py)
├── API Routes (src/api/routes/)     # REST endpoints + WebSocket
├── Agents (src/agents/)             # Document processing pipeline
│   ├── orchestrator.py              # Coordinates all agents
│   ├── reader/                      # PDF text extraction (native + OCR)
│   ├── splitter/                    # Semantic text chunking
│   ├── image_reader/                # Image extraction & captioning
│   └── marker/                      # Visual annotation
├── Services (src/services/)         # Business logic
│   ├── ocr_sequential.py            # Multi-tier OCR (PaddleOCR→Surya→Tesseract)
│   ├── chroma_service.py            # Vector search
│   └── diagram_analyzer.py          # Claude Vision for diagrams
├── Database (src/database/)         # SQLAlchemy ORM + services
│   ├── connection.py                # Connection pooling
│   ├── models/                      # ORM models
│   ├── services/                    # Data access layer
│   └── table_creator.py             # Dynamic per-book tables
├── Utils (src/utils/)               # Helpers
└── Frontend (src/frontend/)         # HTML/JS templates
```

**Processing Flow:** Upload PDF → Reader Agent → Splitter Agent → Image Reader → Marker → PostgreSQL storage → Verification UI

**Database Pattern:** 1 shared `books_metadata` table + 14 dynamic tables per book (7 original + 3 worker system tables + 4 raw data tables)

**Worker System:** Standalone background process for Claude API pipeline processing (see WORKER_SYSTEM_IMPLEMENTATION.md)

## Key Files

- `03-code/src/main.py` - FastAPI entry point, route registration
- `03-code/src/config.py` - Pydantic settings from `.env`
- `03-code/src/agents/orchestrator.py` - Agent coordination
- `03-code/src/services/ocr_sequential.py` - Multi-engine OCR logic
- `03-code/src/database/connection.py` - SQLAlchemy session management
- `03-code/.env` - Runtime configuration (DATABASE_URL, TESSERACT_PATH, etc.)

## Configuration

Environment variables in `03-code/.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `TESSERACT_PATH` - Path to Tesseract binary
- `HOST`/`PORT` - Server binding (default: 0.0.0.0:8888)
- `ANTHROPIC_API_KEY` - For Claude Vision diagram analysis

Agent behavior configured in `agent-config.json` at project root.

## Directory Structure

```
01-requirements/   # Business requirements & UI mockups
02-architecture/   # Design docs, API specs, database schema
03-code/           # Implementation (main codebase)
04-tests/          # Test suite
.claude/agents/    # Claude Code agent instructions
```

## Tech Stack

- **Backend:** FastAPI 0.104.1, SQLAlchemy 2.0, PostgreSQL 16 (Windows Native)
- **OCR:** PaddleOCR (GPU), Surya OCR (GPU), Tesseract (CPU fallback)
- **ML:** sentence-transformers (embeddings), BLIP (image captioning), ChromaDB (vector search)
- **Frontend:** Vanilla HTML/CSS/JS with WebSocket for real-time updates

## Development Notes

- All agents run sequentially in-process (no message queue)
- Images stored as BYTEA in PostgreSQL with LZ4 compression
- WebSocket at `/ws/progress/{book_id}` for processing updates
- API docs at http://localhost:8888/docs (Swagger) or /redoc
- Connection pool: 10 base + 20 overflow connections

## Feature Documentation

See these files in `02-architecture/` for detailed feature specifications:

### AUTO-SLICER.md - Bulk Page OCR Processing (WORKING)
- Automatically processes book pages with Surya OCR at 600 DPI
- Supports 3 levels of titles for pipeline grouping
- Configurable OCR boundaries per page range
- Multiple rectangles with custom attribute mapping (attr31-80)
- Cancel/Pause/Resume with DB persistence
- Page Viewer with OCR text extraction for title configuration
- Zoom options 10%-100% (default 10% for 600 DPI)
- Paragraph preview section with thumbnails
- Full details modal for viewing/editing paragraphs
- Delete button on thumbnails
- Auto-Slicer link added to all page headers
- Access via header link or Book Settings page
- **Status:** WORKING (Fixed in Session 5)
- **Progress:** See `02-architecture/AUTO-SLICER-PROGRESS.md`

### AUTOMATIC BOUNDARIES - DocLayout-YOLO Enhancement (PHASE 1 COMPLETE)
- Enhances Auto-Slicer with automatic boundary detection using DocLayout-YOLO
- Per-book fine-tuned models with model inheritance
- 14 region classes (titles, paragraphs, diagrams, tables, lists, etc.)
- Reference detection for diagram-paragraph linking
- Template learning from user corrections
- **Status:** PHASE 1 COMPLETE - Ready for testing, then Phase 2
- **Phase 1 Code:** ~2,060 lines created
- **Remaining Effort:** ~156 hours (Phases 2-5)
- **CRITICAL: Progress Tracking:** `02-architecture/AUTO-BOUNDARIES-PROGRESS.md`
- **Reference Files:**
  - Research: `02-architecture/automatic-boundaries-local-llm.md`
  - Integration Analysis: `02-architecture/automatic-boundaries-local-llm-part2.md`
  - **Full Requirements:** `02-architecture/automatic-boundaries-local-llm-part3.md`

## Next Session Instructions

**IMPORTANT:**
1. Read `NEXT-SESSION.md` for current task priorities
2. **CRITICAL:** Read `02-architecture/AUTO-BOUNDARIES-PROGRESS.md` for implementation status

### BEFORE TESTING - Required Steps:
1. Run migration: `cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe migrate_add_layout_detection.py`
2. Download model to: `03-code/models/layout_detection/base/doclayout_yolo_docsynth300k.pt`

### Current Priority: Test Phase 1, then Phase 2

```
CURRENT FEATURE: Automatic Boundaries (DocLayout-YOLO)
├── Phase 1: Core Detection (36h) ← COMPLETE (2,060 lines)
│   ├── 1.1 Database Migration ✓
│   ├── 1.2 YOLO Service ✓
│   ├── 1.3 Detection API Endpoints ✓
│   ├── 1.4 WebSocket Progress ✓
│   ├── 1.5 Basic Review UI ✓
│   └── 1.6 Integration with Auto-Slicer ✓
├── Phase 2: Review Interface (36h) ← NEXT
├── Phase 3: Fine-Tuning System (36h)
├── Phase 4: Advanced Features (44h)
└── Phase 5: Export & Polish (40h)
```

### Before Starting Phase 2
1. Run migration and download model (see above)
2. Test Phase 1 at http://localhost:8888/auto-slicer
3. Read `02-architecture/AUTO-BOUNDARIES-PROGRESS.md` for Phase 2 tasks
4. Update tracking file every ~100 lines of code
