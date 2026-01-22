# Quick Command Reference

## Project Location & Configuration
- **Project Path:** `H:\13-extractor2`
- **Virtual Environment:** `H:\13-extractor2\venv`
- **Database:** `knowledge_extraction_2`
- **Server Port:** `8888`

---

## Full System Startup

### From PowerShell (Recommended)

```powershell
# Step 1: Activate virtual environment
cd H:\13-extractor2
.\venv\Scripts\Activate.ps1

# Step 2: Start PostgreSQL (if not running)
sc query postgresql-x64-16

# Step 3: Start FastAPI server
cd 03-code
python -m uvicorn src.main:app --host 0.0.0.0 --port 8888

# OR start in background (hidden window):
Start-Process -FilePath "..\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden
```

### Quick One-Liner (Background Start)
```powershell
cd H:\13-extractor2; Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden
```

### Verify Server is Running
```powershell
Invoke-WebRequest -Uri "http://localhost:8888/api/books" -UseBasicParsing | Select-Object StatusCode
# Should return: StatusCode 200
```

---

## Stop/Restart Server

### Find and Kill Server Process
```powershell
# Find process on port 8888
Get-NetTCPConnection -LocalPort 8888 | Select-Object OwningProcess

# Kill the process (replace PID with actual process ID)
Stop-Process -Id <PID> -Force

# Then restart using startup commands above
```

### Quick Restart (One Command)
```powershell
# Kill existing and start new
$pid = (Get-NetTCPConnection -LocalPort 8888 -ErrorAction SilentlyContinue | Where-Object {$_.OwningProcess -ne 0} | Select-Object -First 1).OwningProcess; if ($pid) { Stop-Process -Id $pid -Force }; Start-Sleep 2; cd H:\13-extractor2; Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden
```

---

## System Health Check

```powershell
# Check server health
Invoke-WebRequest -Uri "http://localhost:8888/health" -UseBasicParsing

# Check database connection
cd H:\13-extractor2\03-code
..\venv\Scripts\python.exe -c "from src.database.connection import engine; conn = engine.connect(); print('Database OK'); conn.close()"

# Check OCR status
Invoke-WebRequest -Uri "http://localhost:8888/api/ocr/check-all-status" -UseBasicParsing
```



## OCR Operations

```powershell
# Load Surya OCR to GPU
Invoke-WebRequest -Uri "http://localhost:8888/api/gpu/load/surya" -Method POST

# Load EasyOCR to GPU
Invoke-WebRequest -Uri "http://localhost:8888/api/gpu/load/easyocr" -Method POST

# Load DocLayout-YOLO to GPU
Invoke-WebRequest -Uri "http://localhost:8888/api/gpu/load/doclayout" -Method POST

# Check GPU status
Invoke-WebRequest -Uri "http://localhost:8888/api/gpu/status" -UseBasicParsing

# Unload model from GPU (free VRAM)
Invoke-WebRequest -Uri "http://localhost:8888/api/gpu/unload/surya" -Method POST
```

## View Logs

```powershell
# Real-time logs
Get-Content H:\13-extractor2\03-code\app.log -Wait -Tail 50

# Recent errors only
Get-Content H:\13-extractor2\03-code\app.log -Tail 100 | Select-String "ERROR"
```

## Git Operations

```powershell
cd H:\13-extractor2

# Check status
git status

# Add and commit
git add .
git commit -m "Your message"

# Push to GitHub
git push origin main
```

## PostgreSQL (Windows)

```powershell
# Check PostgreSQL status
sc query postgresql-x64-16

# Start PostgreSQL
sc start postgresql-x64-16

# Stop PostgreSQL
sc stop postgresql-x64-16
```

---

## Main Application URLs

| Page | URL |
|------|-----|
| Library | http://localhost:8888/library |
| Upload | http://localhost:8888/upload |
| Auto-Slicer | http://localhost:8888/auto-slicer |
| Layout Review | http://localhost:8888/layout-review?book_id=1 |
| Extraction Dashboard | http://localhost:8888/extraction-dashboard?book_id=1 |
| Pipeline Dashboard | http://localhost:8888/pipeline-dashboard?book_id=1 |
| Book Settings | http://localhost:8888/book-settings?book_id=1 |
| API Docs | http://localhost:8888/docs |
