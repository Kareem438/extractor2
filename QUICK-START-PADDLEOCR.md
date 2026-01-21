# Quick Start - PaddleOCR Testing

**Date:** 2025-11-12
**Status:** Installation in progress

## 🚀 Complete These Steps:

### Step 1: Wait for Installation (In Progress)
```bash
# Check if installation finished
python3 -c "from paddleocr import PaddleOCR; print('✅ Ready')"

# If not ready, wait or check process:
ps aux | grep "pip3 install paddle"
```

### Step 2: Clear Database
```bash
cd /mnt/h/12-extractor
PYTHONPATH=/mnt/h/12-extractor/03-code python3 << 'EOF'
from sqlalchemy import text
from src.database.connection import SessionLocal
db = SessionLocal()
db.execute(text('DELETE FROM book1_01wessam_explanation_2026_knowledge_units'))
db.execute(text('''UPDATE book1_01wessam_explanation_2026_processing_state
    SET paddleocr_complete=false, current_page=0, current_agent=NULL WHERE id=1'''))
db.commit()
db.close()
print('✅ Database cleared')
EOF
```

### Step 3: Test with 5 Pages
```bash
curl -X POST "http://localhost:7777/api/ocr/paddleocr" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1, "max_pages": 5}'
```

### Step 4: Monitor (Wait 2-3 minutes)
```bash
# Watch logs
tail -f /mnt/h/12-extractor/logs/app.log | grep "Processing page\|Extracted\|complete"

# Or wait and check results:
sleep 180
```

### Step 5: Verify Results
```bash
PYTHONPATH=/mnt/h/12-extractor/03-code python3 << 'EOF'
from sqlalchemy import text
from src.database.connection import SessionLocal
db = SessionLocal()
count = db.execute(text('SELECT COUNT(*) FROM book1_01wessam_explanation_2026_knowledge_units')).scalar()
print(f'\n✅ Knowledge units: {count}')
if count > 0:
    rows = db.execute(text('''SELECT page_number, LEFT(attr2_value, 80), attr5_value
        FROM book1_01wessam_explanation_2026_knowledge_units ORDER BY page_number LIMIT 3''')).fetchall()
    for r in rows:
        print(f'\nPage {r[0]}: {r[1]}...\nConfidence: {r[2]}%')
db.close()
EOF
```

## ✅ If Test Succeeds:

### Process All 272 Pages
```bash
curl -X POST "http://localhost:7777/api/ocr/paddleocr" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

### Run Evaluation
```bash
curl -X POST "http://localhost:7777/api/evaluate-split-mark" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

### Sync to ChromaDB
```bash
curl -X POST "http://localhost:7777/api/search/sync" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

## 📁 Key Files:
- Implementation: `/mnt/h/12-extractor/03-code/src/services/ocr_sequential.py`
- Status Doc: `/mnt/h/12-extractor/PADDLEOCR-IMPLEMENTATION-STATUS.md`
- Server: `http://localhost:7777`

---
*Run these commands in order after installation completes*
