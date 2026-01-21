# Knowledge Extraction System (12-extractor)

A comprehensive PDF knowledge extraction system with multi-engine OCR, semantic text splitting, AI-powered pipeline processing, and vector database integration.

**Current Status:** ✅ PRODUCTION READY - Core system implemented + Claude AI Pipeline System

---

## Quick Links

- **[PROJECT-SUMMARY.md](PROJECT-SUMMARY.md)** - 📋 **Comprehensive project summary** (START HERE)
- **[CLAUDE.md](CLAUDE.md)** - System startup guide and commands
- **[WORKER_SYSTEM_IMPLEMENTATION.md](WORKER_SYSTEM_IMPLEMENTATION.md)** - Claude Pipeline system documentation
- **[QUICK-START.md](QUICK-START.md)** - Quick start guide

---

## Project Overview

Extract, process, and manage knowledge from PDF documents using:
- **Multi-engine OCR:** Tesseract, PaddleOCR, Surya
- **Semantic text splitting:** SBERT embeddings
- **Dual database:** PostgreSQL + Chroma DB vector search
- **Flexible schema:** 80 attributes (8 system + 72 user-defined)
- **Advanced features:** Record merge/split, WebSocket updates, CSV/JSON export

---

## Features

### Core Capabilities
- **PDF Processing:** Upload and extract text with multi-engine OCR (PaddleOCR, Surya, Tesseract)
- **Semantic Splitting:** Automatic text chunking into knowledge units
- **Dual Database:** PostgreSQL for structured data + ChromaDB for vector search
- **AI Pipeline System (NEW):** Claude-powered configurable processing pipelines
- **Full Search:** Text and semantic search across all books
- **Data Management:** Merge/split knowledge units, export to CSV/JSON
- **Real-time Monitoring:** WebSocket updates and pipeline dashboard

### Claude AI Pipeline System (NEW)
- **Configurable Steps:** Build multi-step AI processing pipelines
- **Template Variables:** Dynamic prompt generation with book data
- **Cost Control:** Response caching and rate limit handling
- **Dual I/O:** Read/write from PostgreSQL and ChromaDB
- **Progress Tracking:** Per-step execution monitoring
- **Standalone Worker:** Independent background processor
- **Multiple Models:** Choose Claude Sonnet, Opus, or Haiku per step

### Technical Highlights
- **Three OCR engines** for maximum accuracy
- **Two-tier storage** (raw + processed data for re-splitting without re-OCR)
- **Worker system** for autonomous AI pipeline processing
- **Cross-book semantic search** via unified vector collection
- **Real-time WebSocket updates** for processing progress
- **40-attribute flexible schema** adapts to any book type
- **14 per-book tables** (4 raw + 7 processed + 3 pipeline)

---

## Architecture

### Database Design

**PostgreSQL Tables:**

*Global Tables (3):*
- `books_metadata` - Shared table for all books
- `worker_status` - Worker heartbeat and state (NEW)
- `pipeline_templates` - Reusable pipeline configs (NEW)
- `worker_commands` - Worker control commands (NEW)

*Per-book Tables (14 per book):*
- Raw Data (4): `raw_pages`, `raw_knowledge_units`, `raw_paragraph_images`, `raw_diagram_images`
- Processed (7): `knowledge_units`, `pages`, `images`, `processing_state`, `settings`, `hierarchy`, `attribute_keys`
- Pipeline System (3): `pipeline_config`, `task_queue`, `step_progress` (NEW)

**ChromaDB (Vector Database):**
- Single unified collection: `knowledge_base_unified`
- 384-dimensional embeddings (MiniLM)
- Stores all books, text chunks, and images
- 14 metadata fields for filtering

### Technology Stack
- **Backend:** Python 3.9+, FastAPI
- **Database:** PostgreSQL 15+, pgvector extension
- **Vector DB:** Chroma DB
- **OCR:** Tesseract, PaddleOCR, Surya
- **Embeddings:** SBERT (MiniLM)
- **Frontend:** HTML, JavaScript, WebSocket

---

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Core System** | ✅ Complete | PDF processing, OCR, storage |
| **Web Interface** | ✅ Complete | Library, upload, review, edit |
| **Worker System** | ✅ Complete | Claude AI pipeline processing |
| **API Endpoints** | ✅ Complete | Full REST API + WebSocket |
| **Database Schema** | ✅ Complete | PostgreSQL + ChromaDB |
| **Documentation** | ✅ Complete | User and developer docs |

**Overall Status:** ✅ PRODUCTION READY

### What's Implemented
- ✅ FastAPI application with 12+ route modules
- ✅ Multi-engine OCR (PaddleOCR, Surya, Tesseract)
- ✅ Semantic text splitting and chunking
- ✅ PostgreSQL database with 14 per-book tables
- ✅ ChromaDB vector search integration
- ✅ Web UI for all major workflows
- ✅ **Worker system for Claude AI pipelines** (NEW)
- ✅ **Pipeline configuration and monitoring UI** (NEW)
- ✅ Real-time WebSocket progress updates

### Recent Additions (2026-01-01)
- ✅ Claude AI Pipeline System (4 phases complete)
- ✅ Template variable substitution engine
- ✅ PostgreSQL and ChromaDB I/O handlers
- ✅ Rate limit handling with auto-recovery
- ✅ Pipeline configuration web interface
- ✅ Real-time dashboard with worker monitoring
- ✅ Standalone background worker process

---

## Quick Start (For Development)

```bash
# 1. Navigate to project
cd /home/kiko/12-extractor

# 2. Review next chunk specification
cat 02-architecture/code-chunks/breakdown.md | grep "CHUNK-001" -A 30

# 3. Review tests
cat 04-tests/unit/test_chunk_001.py

# 4. Implement code (30-50 LOC)
# Create 03-code/src/config.py

# 5. Run tests
pytest 04-tests/unit/test_chunk_001.py -v

# 6. Fix until 100% pass, then commit
```

---

## Database Backup & Maintenance

### Automated Backup Scripts

Two Python scripts provide safe, non-disruptive database backups:

#### PostgreSQL Backup
```bash
python "06-PostgreSQL Backup.py"
```
**Creates:**
- SQL format backup (~600 MB) - Human-readable, compatible with psql
- Custom format backup (~295 MB) - Compressed binary, faster restore

**Saved to:** `06-PostgreSQL BACKUP/knowledge_extraction_YYYY-MM-DD_HH-MM-SS.*`

#### ChromaDB Backup
```bash
python "07-Chroma Backup.py"
```
**Creates:**
- Compressed ZIP archive (~0.03 MB from 0.38 MB)
- Includes SQLite database and all vector collections
- 90%+ compression ratio

**Saved to:** `07-Chroma BACKUP/chroma_backup_YYYY-MM-DD_HH-MM-SS.zip`

### Restore Instructions

**PostgreSQL (SQL format):**
```bash
psql -h localhost -p 5432 -U postgres -d knowledge_extraction < "backup_file.sql"
```

**PostgreSQL (Custom format):**
```bash
pg_restore -h localhost -p 5432 -U postgres -d knowledge_extraction "backup_file.dump"
```

**ChromaDB:**
1. Stop server: Stop FastAPI and worker processes
2. Backup existing: `mv chroma_db chroma_db.old`
3. Extract: `unzip "backup_file.zip"`
4. Restart server

### Best Practices
- ✅ Backup before migrations or schema changes
- ✅ Backup before major updates
- ✅ Run backups daily/weekly for important data
- ✅ Store backups off-site for disaster recovery
- ✅ Both scripts safe to run while databases are active

---

## Project Structure

```
12-extractor/
├── 01-requirements/           # ✅ Phase 1: Requirements
│   ├── requirements-specification.md
│   ├── user-stories.md
│   ├── acceptance-criteria.md
│   └── ui-mockups/           # 5 SVG HTML mockups
│
├── 02-architecture/          # ✅ Phase 2: Architecture
│   ├── system-design.md
│   ├── database-schema.md
│   ├── data-model.md
│   ├── api-design.md
│   ├── code-chunks/          # 45 chunk specifications
│   └── diagrams/             # ER diagrams
│
├── 04-tests/                 # ✅ Phase 3: Tests
│   ├── test-plan.md
│   ├── unit/                 # 45 unit test files
│   ├── integration/          # 5 integration test files
│   └── e2e/                  # 5 E2E test files
│
├── 03-code/                  # ⏳ Phase 4: Development (pending)
│   └── src/                  # To be created
│
├── START-HERE.md             # Quick resume guide
├── PROJECT-STATUS.md         # Complete project status
└── README.md                 # This file
```

---

## Development Approach

### Test-First Development
All 535 tests were generated **before** any code. Development follows:
1. Read chunk specification
2. Read test file
3. Implement code to make tests pass
4. Must achieve 100% test pass before next chunk

### Code Chunks (45 total)
Organized into 5 dependency levels:
- **Level 0:** Foundation (8 chunks) - Config, database, models
- **Level 1:** Core logic (10 chunks) - OCR, text splitting
- **Level 2:** Services (12 chunks) - Background tasks, WebSocket
- **Level 3:** Presentation (10 chunks) - API endpoints, UI
- **Level 4:** Integration (5 chunks) - Full workflows

Each chunk is 30-50 LOC with clear dependencies.

---

## Key Design Decisions

### Why Dual Databases?
- **PostgreSQL:** ACID transactions, complex queries, source of truth
- **Chroma DB:** Optimized vector search, cross-book semantic discovery
- **Async sync:** Non-blocking, metadata-only updates when possible

### Why Two-Tier Storage?
- **Raw data:** Preserves original OCR from all 3 engines
- **Processed data:** Semantically split chunks
- **Benefit:** Re-split text without re-running expensive OCR

### Why 40 Attributes?
- **8 system:** Reserved for core functionality
- **32 user:** Customizable without schema changes
- **Flexible:** Adapts to any book type (textbooks, novels, technical docs)

---

## Documentation

- **[START-HERE.md](START-HERE.md)** - Quick resume guide
- **[PROJECT-STATUS.md](PROJECT-STATUS.md)** - Detailed project status
- **[01-requirements/requirements-specification.md](01-requirements/requirements-specification.md)** - Full requirements
- **[02-architecture/system-design.md](02-architecture/system-design.md)** - System architecture
- **[02-architecture/database-schema.md](02-architecture/database-schema.md)** - Database schema
- **[04-tests/test-plan.md](04-tests/test-plan.md)** - Test strategy

---

## Development Agents

This project was developed using 5 specialized AI agents:
- **Business Analyst:** Requirements gathering
- **Architect:** System design and code chunk planning
- **Tester:** Test generation (535 tests before any code)
- **Developer:** Implementation (Phase 4, pending)
- **Orchestrator:** Lifecycle management

Agent configurations are in `.claude/agents/`

---

## License

This project is for educational and personal use.
