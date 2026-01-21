# START HERE - Quick Resume Guide

**Last Updated:** 2026-01-21
**Project:** Knowledge Extraction System (12-extractor)
**Status:** Production Ready + Enhanced UI + Interactive OCR + Diagram Analysis
**Working Directory:** `H:\12-extractor` (Windows) / `/mnt/h/12-extractor` (WSL)

---

## 📋 NEW: Comprehensive Project Summary

**👉 [PROJECT-SUMMARY.md](PROJECT-SUMMARY.md) - READ THIS FIRST for complete project overview**

This document provides:
- Complete system architecture explanation
- Current status and progress (95% complete)
- Processing workflow details
- Database design overview
- AI integration details
- Use cases and typical workflows
- Quick links to all documentation

---

## Documentation Index

| Document | Description |
|----------|-------------|
| **[PROJECT-SUMMARY.md](PROJECT-SUMMARY.md)** | **📋 Comprehensive project summary (START HERE)** |
| [docs/ENVIRONMENT-CONFIG.md](docs/ENVIRONMENT-CONFIG.md) | Runtime setup, starting the system |
| [docs/VENV-SETUP.md](docs/VENV-SETUP.md) | Virtual environment setup & backup |
| [docs/QUICK-COMMANDS.md](docs/QUICK-COMMANDS.md) | Common commands reference |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [NEXT-SESSION-CONTEXT.md](NEXT-SESSION-CONTEXT.md) | Detailed session notes |

---

## Quick Start (3 minutes)

### 1. Verify PostgreSQL Service (Windows)
```bash
sc query postgresql-x64-16
```
Expected: STATE = RUNNING. If not running: `sc start postgresql-x64-16`

### 2. Verify Database Connection
```bash
cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()"
```

### 3. Start FastAPI Server
```bash
cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777
```

### 4. Verify Server is Running
```bash
curl -s http://localhost:7777/health
```
Expected: `{"status":"healthy","service":"Knowledge Extraction System","version":"1.0.0"}`

### 5. Access the Application
- **Library:** http://localhost:7777/library
- **Verify Pages:** http://localhost:7777/verify-pages
- **API Docs:** http://localhost:7777/docs

---

## Claude Code Automated Startup

**For Claude Code to launch the system automatically, execute these commands using the Bash tool:**

```
Step 1: Verify PostgreSQL service is running
Bash(sc query postgresql-x64-16)

Step 2: Test database connection
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()")

Step 3: Start FastAPI server (use run_in_background=true parameter)
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777)

Step 4: Wait and verify health
Bash(ping -n 6 127.0.0.1 >nul && curl -s http://localhost:7777/health)
```

**Important Notes:**
- PostgreSQL 16 runs natively on Windows as a Windows service
- Use forward slashes in paths (H:/12-extractor not H:\12-extractor)
- Use full path to python.exe: `H:/12-extractor/venv/Scripts/python.exe`
- Server runs on port 7777

---

## If venv is Missing or Broken

See [docs/VENV-SETUP.md](docs/VENV-SETUP.md) for complete instructions.

**Quick version:**
```powershell
cd H:\12-extractor
python -m venv venv
.\venv\Scripts\activate
pip install -r 03-code/requirements-frozen.txt
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

---

## Current System Status

### Components
- FastAPI Server (Windows)
- PostgreSQL 16 Database (Windows Native)
- ChromaDB Vector Store
- EasyOCR (GPU, Arabic+English)
- Surya OCR (GPU)
- Tesseract OCR
- Claude Vision (Diagram Analysis)

### Key Package Versions
| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.13.2 | Windows native |
| PyTorch | 2.9.1+cu126 | CUDA 12.6 for RTX 4070 |
| EasyOCR | 1.7.2 | Arabic + English |
| Surya OCR | 0.17.0 | GPU-accelerated |

---

## Latest Session (Dec 31, 2025)

### Completed
1. **PostgreSQL Migration** - Migrated from WSL to Windows native PostgreSQL 16
2. **Database Import** - Successfully imported backup with 33 tables and 1 book
3. **Configuration Update** - Updated .env to use localhost instead of WSL IP
4. **System Verification** - All services running correctly on Windows
5. **Documentation Update** - Updated all docs for Windows PostgreSQL setup

### Fixed Issues
- WSL PostgreSQL networking issues (replaced with Windows native)
- Database connection timeout from Windows to WSL
- Unreliable WSL IP address changes

---

## Project Structure

```
H:\12-extractor\
├── 03-code/                  # Source code
│   ├── src/
│   │   ├── api/routes/       # FastAPI endpoints
│   │   ├── services/         # Business logic (OCR, diagrams)
│   │   ├── database/         # Database services
│   │   ├── frontend/         # HTML templates, JS, CSS
│   │   ├── config.py         # Configuration
│   │   └── main.py           # FastAPI app
│   ├── .env                  # Environment variables (NOT in git)
│   ├── .env.example          # Template for .env
│   └── requirements-frozen.txt  # Exact package versions
├── docs/                     # Documentation
│   ├── ENVIRONMENT-CONFIG.md
│   ├── VENV-SETUP.md
│   ├── QUICK-COMMANDS.md
│   └── TROUBLESHOOTING.md
├── venv/                     # Virtual environment (NOT in git)
├── chroma_db/                # ChromaDB vector storage
└── START-HERE.md             # This file
```

---

## Next Steps

1. **Implement Backend Worker System** - See backend-option-a.md
   - Create database migration scripts
   - Build worker module (src/worker/)
   - Build pipeline configuration UI
   - Build pipeline dashboard

---

## Quick Links

- **GitHub:** https://github.com/kareemmohamed2024/12-extractor
- **API Docs:** http://localhost:7777/docs
- **Anthropic Console:** https://console.anthropic.com/

---

**Ready to resume! Check the documentation index above for specific topics.**
