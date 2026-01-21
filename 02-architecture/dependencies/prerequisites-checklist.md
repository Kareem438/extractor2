# Prerequisites Checklist - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Platform:** Windows VM (primary), Linux compatible
**Status:** ✅ Prerequisites Complete

---

## ✅ Pre-Installation Checklist

### 1. System Requirements

**Operating System:**
- [ ] Windows 10/11 (primary deployment)
- [ ] OR Linux (Ubuntu 20.04+, Debian 11+)
- [ ] Minimum 8GB RAM (16GB recommended)
- [ ] 50GB free disk space (for AI models + data)
- [ ] Stable internet connection (for model downloads)

**Network:**
- [ ] Access to separate Windows machine for PostgreSQL database
- [ ] Both machines on same local network
- [ ] Database machine IP address known
- [ ] Port 5432 accessible (PostgreSQL)

---

### 2. Python Installation

**Version:** Python 3.9.x or higher

**Windows Installation:**
- [ ] Download Python 3.9+ from https://www.python.org/downloads/windows/
- [ ] Run installer as Administrator
- [ ] ✅ CHECK: "Add Python to PATH" during installation
- [ ] ✅ CHECK: "Install pip" (included by default)
- [ ] Verify installation:
  ```powershell
  python --version  # Should show Python 3.9.x or higher
  pip --version     # Should show pip version
  ```

**Linux Installation:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip

# Verify
python3.9 --version
pip3 --version
```

---

### 3. PostgreSQL Database Server

**Version:** PostgreSQL 15.x or higher
**Location:** Separate Windows machine (database server)

**Installation on Database Server:**
- [ ] Download PostgreSQL 15+ from https://www.postgresql.org/download/windows/
- [ ] Run installer
- [ ] ✅ Set postgres user password (remember this!)
- [ ] ✅ Set port: 5432 (default)
- [ ] ✅ Install pgAdmin 4 (recommended, optional)
- [ ] Start PostgreSQL service

**Verify Installation:**
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Or use pgAdmin 4 GUI
```

**Create Database:**
```sql
-- Connect to PostgreSQL as postgres user
CREATE DATABASE knowledge_extraction
    WITH ENCODING 'UTF8'
    LC_COLLATE='en_US.UTF-8'
    LC_CTYPE='en_US.UTF-8';

-- Create application user
CREATE USER knowledge_app WITH PASSWORD 'your_secure_password_here';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE knowledge_extraction TO knowledge_app;
```

**Network Configuration:**
```ini
# Edit postgresql.conf (usually in C:\Program Files\PostgreSQL\15\data\)
# Allow network connections
listen_addresses = '*'  # Or specific IP

# Edit pg_hba.conf
# Add line to allow connections from processing VM
host    knowledge_extraction    knowledge_app    192.168.1.0/24    md5
# Replace 192.168.1.0/24 with your network range
```

**Restart PostgreSQL** after configuration changes.

---

### 4. pgvector Extension

**Version:** 0.5.1 or higher

**Installation on Database Server:**

**Windows:**
- [ ] Download pgvector from https://github.com/pgvector/pgvector/releases
- [ ] Extract files:
  - `vector.dll` → `C:\Program Files\PostgreSQL\15\lib\`
  - `vector.control` + `vector--*.sql` → `C:\Program Files\PostgreSQL\15\share\extension\`
- [ ] Restart PostgreSQL service
- [ ] Enable extension:
  ```sql
  -- Connect to knowledge_extraction database
  CREATE EXTENSION IF NOT EXISTS pgvector;

  -- Verify
  SELECT * FROM pg_extension WHERE extname = 'pgvector';
  ```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# Or compile from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Enable in database
psql -U postgres -d knowledge_extraction -c "CREATE EXTENSION pgvector;"
```

---

### 5. Tesseract OCR

**Version:** 4.1.x or higher (recommend 5.x)

**Windows Installation:**
- [ ] Download from https://github.com/UB-Mannheim/tesseract/wiki
- [ ] Run installer
- [ ] ✅ Install to: `C:\Program Files\Tesseract-OCR\` (default)
- [ ] ✅ CHECK: "Add to system PATH" during installation
- [ ] ✅ Install language data: English (eng.traineddata - included)
- [ ] ✅ Install language data: Arabic (ara.traineddata - download separately)

**Download Arabic Language Data:**
- [ ] Go to: https://github.com/tesseract-ocr/tessdata
- [ ] Download `ara.traineddata`
- [ ] Copy to: `C:\Program Files\Tesseract-OCR\tessdata\`

**Verify Installation:**
```powershell
tesseract --version  # Should show version 4.x or 5.x
tesseract --list-langs  # Should show eng and ara
```

**Linux Installation:**
```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara

# Verify
tesseract --version
tesseract --list-langs
```

---

### 6. Git (Optional but Recommended)

**Version:** Any recent version

**Windows:**
- [ ] Download Git from https://git-scm.com/download/win
- [ ] Run installer with defaults
- [ ] Verify: `git --version`

**Linux:**
```bash
sudo apt install git
```

---

### 7. Modern Web Browser

**Required for Web Interface:**
- [ ] Google Chrome 90+ (recommended)
- [ ] Firefox 88+
- [ ] Microsoft Edge 90+
- [ ] Any modern browser with WebSocket support

---

## 📦 Installation Steps

### Step 1: Clone/Download Project

```powershell
# If using Git
git clone <repository-url>
cd 12-extractor

# Or download and extract ZIP
```

---

### Step 2: Create Virtual Environment

**Windows:**
```powershell
cd 12-extractor
python -m venv venv
venv\Scripts\activate
```

**Linux:**
```bash
cd 12-extractor
python3.9 -m venv venv
source venv/bin/activate
```

**Verify:**
```bash
# Prompt should show (venv)
# Check Python in venv
python --version
which python  # Should point to venv directory
```

---

### Step 3: Install Python Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies (will take 5-10 minutes)
pip install -r requirements.txt
```

**Expected Installation Size:** ~1.65 GB
- PyTorch (CPU): ~150 MB
- SBERT models: ~420 MB (downloaded on first use)
- BLIP model: ~990 MB (downloaded on first use)
- Other packages: ~90 MB

---

### Step 4: Download AI Models

**These models download on first use, but you can pre-download:**

```python
# Download SBERT model (420 MB)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Download BLIP model (990 MB)
python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base'); BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')"

# Download spaCy model (12 MB)
python -m spacy download en_core_web_sm
```

**Total Download:** ~1.4 GB
**Cache Location:** `~/.cache/` (Windows: `C:\Users\<username>\.cache\`)

---

### Step 5: Configure Environment

**Create `.env` file:**
```bash
cp .env.example .env
```

**Edit `.env` file:**
```env
# Database Configuration
DATABASE_URL=postgresql://knowledge_app:your_password@192.168.1.100:5432/knowledge_extraction

# Tesseract Configuration (Windows)
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# Model Cache Directory
MODEL_CACHE_DIR=C:\Users\<username>\.cache\models

# Or Linux
# TESSERACT_PATH=/usr/bin/tesseract
# MODEL_CACHE_DIR=/home/<username>/.cache/models
```

**Replace:**
- `your_password` → Your PostgreSQL password
- `192.168.1.100` → Your database server IP
- `<username>` → Your Windows/Linux username

---

### Step 6: Initialize Database

```bash
# Run database initialization script
python src/database/init_db.py
```

**Expected Output:**
```
Creating extensions...
✓ pgvector extension created
✓ pg_trgm extension created

Creating shared tables...
✓ books_metadata table created
✓ Trigger functions created

Database initialized successfully!
```

---

### Step 7: Test Connection

```bash
# Test database connection
python -c "from src.database.connection import engine; print(engine.connect())"

# Should output: <sqlalchemy.engine.base.Connection object at 0x...>
```

---

### Step 8: Run Application

```bash
# Start FastAPI server
python src/main.py

# Or with uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Step 9: Access Web Interface

**Open browser:**
```
http://localhost:8000
```

**You should see:** Upload page for document processing

---

## 🔍 Verification Checklist

### Python Environment
- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] All packages installed (no errors)
- [ ] AI models downloaded successfully

### Database
- [ ] PostgreSQL 15+ running on database server
- [ ] pgvector extension installed and enabled
- [ ] knowledge_extraction database created
- [ ] Application user created with permissions
- [ ] Network connection working from processing VM
- [ ] Shared tables created (books_metadata)

### OCR
- [ ] Tesseract 4.1+ installed
- [ ] English language data installed
- [ ] Arabic language data installed
- [ ] tesseract command accessible from terminal
- [ ] Path configured in .env file

### Application
- [ ] .env file configured correctly
- [ ] Database initialization successful
- [ ] FastAPI server starts without errors
- [ ] Web interface accessible at http://localhost:8000
- [ ] No errors in console/logs

---

## 🚨 Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'fitz'"
**Solution:**
```bash
pip install PyMuPDF==1.23.8
```

### Issue 2: "psycopg2.OperationalError: could not connect to server"
**Solution:**
- Check PostgreSQL is running on database server
- Verify DATABASE_URL in .env
- Check network connectivity: `ping <database-server-ip>`
- Verify pg_hba.conf allows connections from processing VM
- Check firewall allows port 5432

### Issue 3: "pytesseract.TesseractNotFoundError"
**Solution:**
- Verify Tesseract is installed: `tesseract --version`
- Check TESSERACT_PATH in .env points to correct location
- Windows: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Linux: `/usr/bin/tesseract`

### Issue 4: "CUDA not available" or torch warnings
**Solution:**
- This is EXPECTED (we use CPU-only PyTorch)
- Models will run on CPU (slower but works)
- Ignore CUDA warnings

### Issue 5: AI models download slowly
**Solution:**
- Models download from HuggingFace (can be slow)
- Use good internet connection for first-time setup
- Models are cached after first download
- Total ~1.4 GB download

### Issue 6: Port 8000 already in use
**Solution:**
```bash
# Use different port
uvicorn src.main:app --port 8001

# Or kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux:
lsof -i :8000
kill -9 <PID>
```

---

## 📊 Resource Requirements

### Processing VM (Where Application Runs)
- **CPU:** 4+ cores (recommended)
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 50GB free (AI models + documents)
- **Network:** Gigabit LAN (for database connection)

### Database Server
- **CPU:** 2+ cores
- **RAM:** 4GB minimum, 8GB recommended
- **Disk:** 100GB+ (for storing books data)
- **Network:** Gigabit LAN

### Estimated Storage per Book (500 pages):
- Knowledge units: ~10 MB
- Images (compressed): ~10 MB
- Pages (compressed): ~50 MB
- **Total: ~70 MB per book**

---

## ✅ Final Verification

**Run this checklist before starting development:**

1. [ ] Python 3.9+ working
2. [ ] Virtual environment active (see `(venv)` in prompt)
3. [ ] All pip packages installed
4. [ ] PostgreSQL accessible from VM
5. [ ] pgvector extension working
6. [ ] Tesseract OCR working (test: `tesseract --version`)
7. [ ] .env file configured
8. [ ] Database initialized (books_metadata table exists)
9. [ ] FastAPI starts without errors
10. [ ] Web interface loads at http://localhost:8000

**If all checked:** ✅ Ready for development!

---

## 📞 Support

**Common Locations:**
- PostgreSQL data: `C:\Program Files\PostgreSQL\15\data\`
- Tesseract: `C:\Program Files\Tesseract-OCR\`
- Python venv: `12-extractor\venv\`
- Model cache: `C:\Users\<username>\.cache\`
- Application logs: `12-extractor\app.log`

**Database Connection String Format:**
```
postgresql://username:password@host:port/database
```

**Example:**
```
postgresql://knowledge_app:mypassword@192.168.1.100:5432/knowledge_extraction
```

---

**Prerequisites Checklist Complete:** ✅
**Ready for:** setup.sh script execution + development start

