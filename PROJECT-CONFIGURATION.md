# Project Configuration - 13-extractor2

This document describes the configuration for this project instance, which runs in parallel with the original project (12-extractor).

## Important: This is a Parallel Instance

This project (`H:\13-extractor2`) is a copy of the original project (`H:\12-extractor`) configured to run simultaneously without conflicts.

## Configuration Differences from Original

| Setting | Original (12-extractor) | This Instance (13-extractor2) |
|---------|------------------------|-------------------------------|
| **Project Path** | `H:\12-extractor` | `H:\13-extractor2` |
| **Database Name** | `knowledge_extraction` | `knowledge_extraction_2` |
| **Server Port** | `7777` | `8888` |
| **Virtual Environment** | `H:\12-extractor\venv` | `H:\13-extractor2\venv` |

## Database Setup

The database `knowledge_extraction_2` has been created and populated with data from the original project.

### Initial Data Restoration (Completed 2026-01-21)

**PostgreSQL Database:**
- Source: `H:\13-extractor2\06-PostgreSQL BACKUP\knowledge_extraction_2026-01-21_08-26-07.sql`
- Target: `knowledge_extraction_2`
- Tables restored: 47 tables including:
  - `books_metadata` (main metadata table)
  - Book-specific tables (book1, book2, book3, book4)
  - Layout detection tables (`layout_models`, `layout_flagged_pages`, etc.)
  - Pipeline/worker tables (`pipeline_templates`, `worker_status`, etc.)
  - Raw data tables

**ChromaDB:**
- Source: `H:\13-extractor2\07-Chroma BACKUP\chroma_backup_2026-01-21_08-30-24.zip`
- Target: `H:\13-extractor2\chroma_db\`
- Contents: `chroma.sqlite3` + vector collection data

### Manual Database Creation (if needed)

If you need to recreate the database from scratch:

```sql
-- Connect to PostgreSQL and run:
CREATE DATABASE knowledge_extraction_2;
```

Or via command line:
```bash
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE knowledge_extraction_2;"
```

## Access URLs

After starting the server, access the application at:

- **Library:** http://localhost:8888/library
- **Upload:** http://localhost:8888/upload
- **API Docs:** http://localhost:8888/docs
- **Health Check:** http://localhost:8888/health

## Startup Commands

```bash
# Verify PostgreSQL
sc query postgresql-x64-16

# Verify database connection
cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()"

# Start server (port 8888)
cd H:/13-extractor2/03-code && H:/13-extractor2/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8888

# Verify health
curl -s http://localhost:8888/health
```

## Running Both Instances Simultaneously

You can run both the original and this instance at the same time:

1. **Original (12-extractor):** Runs on port `7777`, uses database `knowledge_extraction`
2. **This instance (13-extractor2):** Runs on port `8888`, uses database `knowledge_extraction_2`

Each instance has its own:
- Database (completely separate data)
- ChromaDB directory
- Log files
- Virtual environment

## Git Status

Git configuration in this folder is not set up correctly (copied from original project). This will be fixed at a later stage.

## Configuration Files

The following files contain the configuration:
- `H:\13-extractor2\.env` - Root environment variables
- `H:\13-extractor2\03-code\.env` - Application environment variables (primary)
- `H:\13-extractor2\CLAUDE.md` - Claude Code instructions with correct paths

## Change History

| Date | Change |
|------|--------|
| 2026-01-21 | Initial configuration: Set database to `knowledge_extraction_2`, port to `8888`, updated all paths from `H:\12-extractor` to `H:\13-extractor2` |
| 2026-01-21 | Database restoration: Restored PostgreSQL (47 tables) from `knowledge_extraction_2026-01-21_08-26-07.sql` and ChromaDB from `chroma_backup_2026-01-21_08-30-24.zip` |
