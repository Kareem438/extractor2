# Environment Configuration

## Runtime Environment Split

| Component | Environment | Path/Location |
|-----------|-------------|---------------|
| **Python venv** | Windows (native) | `H:\12-extractor\venv\` |
| **FastAPI Server** | Windows (native) | Runs via `python -m uvicorn` |
| **PostgreSQL** | Windows (native) | PostgreSQL 16 Windows service |
| **ChromaDB** | Windows (native) | `H:\12-extractor\chroma_db\` |
| **OCR Engines** | Windows (native) | EasyOCR, Surya, Tesseract |

## Starting the System

### Windows PowerShell - Start FastAPI Server

```powershell
cd H:\12-extractor\03-code
..\venv\Scripts\activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 7777 --reload
```

### Windows - PostgreSQL Service

```bash
sc query postgresql-x64-16
sc start postgresql-x64-16
```

## Database Connection

The Windows Python app connects to PostgreSQL running in WSL via:
- Host: `localhost` (WSL's PostgreSQL is accessible from Windows)
- Port: `5432`
- Database: `knowledge_extraction`

## Server URLs

| URL | Description |
|-----|-------------|
| http://localhost:7777 | Main application |
| http://localhost:7777/library | Book library |
| http://localhost:7777/verify-pages | Page verification |
| http://localhost:7777/docs | API documentation |
| http://localhost:7777/health | Health check |
