# Troubleshooting Guide

## Server Won't Start

```powershell
# Check if port is in use
netstat -ano | findstr 7777

# Kill existing Python processes
taskkill /F /IM python.exe

# Check logs for errors
Get-Content H:\12-extractor\03-code\app.log -Tail 50
```

## Database Connection Failed

```bash
# Windows - Check PostgreSQL service status
sc query postgresql-x64-16

# Restart if needed
sc stop postgresql-x64-16 && sc start postgresql-x64-16
```

```powershell
# Windows - Test connection
cd H:\12-extractor\03-code
..\venv\Scripts\python.exe -c "from src.database.connection import SessionLocal; db = SessionLocal(); print('Connected OK')"
```

## OCR Processing Stuck

```powershell
# Check current status
curl http://localhost:7777/api/ocr/status/1

# Check logs for errors
Get-Content H:\12-extractor\03-code\app.log -Tail 100 | Select-String "ERROR"
```

## EasyOCR Encoding Error on Windows

If you see `'charmap' codec can't encode character '\u2588'`:

This is fixed in the code. The issue was EasyOCR's progress bar using Unicode characters that Windows cp1252 can't handle. The fix suppresses stdout/stderr during model loading.

## Surya OCR Models Not Loading

```powershell
# Check GPU status
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

# Manual load test
curl http://localhost:7777/api/ocr/load-surya
```

## ChromaDB Issues

```powershell
# Reinitialize ChromaDB
Remove-Item -Recurse -Force H:\12-extractor\chroma_db

# Test creation
python -c "import chromadb; c = chromadb.PersistentClient(path='H:/12-extractor/chroma_db'); print('ChromaDB OK')"
```

## Virtual Environment Broken

See [VENV-SETUP.md](VENV-SETUP.md) for recreation instructions.
