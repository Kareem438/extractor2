---
inclusion: auto
---

# Session Essentials — Read Every Session

**CRITICAL: At the start of every new session, you MUST read these files before doing anything else:**

1. `CLAUDE-CODE-REFERENCE.md` — Contains code snippets, API endpoints, and implementation notes for the pipeline page (Claude analysis, diagram decoding, re-decode functionality)
2. `docs/QUICK-COMMANDS.md` — Contains all project commands, paths, ports, URLs, and operational procedures

---

## Key Facts (from QUICK-COMMANDS.md)

- **Project Path:** `H:\13-extractor2`
- **Virtual Environment:** `H:\13-extractor2\venv`
- **Server Port:** `8888` (NOT 8000, NOT 7777)
- **Database:** `knowledge_extraction_2` on PostgreSQL 16 (localhost:5432)
- **Start Server:** `Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden`

---

## Database Credentials

- **User:** `postgres`
- **Password:** `postgres`
- **Host:** `localhost:5432`
- **Database:** `knowledge_extraction_2`
- **Connection URL:** `postgresql://postgres:postgres@localhost:5432/knowledge_extraction_2`

When running `pg_dump` or any PostgreSQL CLI tool, set the password environment variable first:
```powershell
$env:PGPASSWORD = "postgres"; & "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U postgres -d knowledge_extraction_2 -F c -f "H:\13-extractor2\backups\knowledge_extraction_2_$(Get-Date -Format 'yyyy-MM-dd').backup"
```

---

## Reminder

- ALWAYS read `docs/QUICK-COMMANDS.md` before running any server, database, or operational commands
- ALWAYS read `CLAUDE-CODE-REFERENCE.md` before working on pipeline or extraction features
- NEVER guess ports, paths, or credentials — they are documented in these files
