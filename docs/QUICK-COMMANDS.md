# Quick Command Reference

## Full System Startup (Claude Code)

Execute using the Bash tool in sequence:

```
Step 1: Start PostgreSQL cluster (version 16, 15, or 14)
Bash(sc query postgresql-x64-16)

Step 3: Test database connection
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()")

Step 4: Start FastAPI server (run_in_background=true)
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777)

Step 5: Verify health
Bash(sleep 5 && curl -s http://localhost:7777/health)
```

## System Health Check

```
Bash(curl -s http://localhost:7777/health)

Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()")

Bash(curl -s http://localhost:7777/api/ocr/check-all-status)
```

## Start/Restart Server

```
# Start server
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777)

# Start server with auto-reload (for development)
Bash(cd H:/12-extractor/03-code && H:/12-extractor/venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 7777 --reload)
```

## OCR Operations

```powershell
# Load Surya OCR to GPU
curl http://localhost:7777/api/ocr/load-surya

# Load EasyOCR to GPU
curl http://localhost:7777/api/ocr/load-easyocr

# Check all OCR status
curl http://localhost:7777/api/ocr/check-all-status

# Unload all OCR from GPU (free VRAM)
curl http://localhost:7777/api/ocr/unload-all
```

## View Logs

```powershell
# Real-time logs
Get-Content H:\12-extractor\03-code\app.log -Wait -Tail 50

# Recent errors only
Get-Content H:\12-extractor\03-code\app.log -Tail 100 | Select-String "ERROR"
```

## Git Operations

```powershell
cd H:\12-extractor

# Check status
git status

# Add and commit
git add .
git commit -m "Your message"

# Push to GitHub
git push origin master
```

## PostgreSQL (Windows)

```
# Start PostgreSQL cluster (use version installed: 16, 15, or 14)
Bash(sc query postgresql-x64-16)

# Stop PostgreSQL cluster
Bash(sc stop postgresql-x64-16)

# Check cluster status
Bash(sc query postgresql-x64-16)
```
