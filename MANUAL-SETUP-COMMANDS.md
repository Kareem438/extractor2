# Manual Setup Commands - Run These in Separate Shell

## 1. Install EasyOCR (For Real OCR)

```bash
# Run this in a new terminal
cd /mnt/h/12-extractor
pip3 install easyocr --break-system-packages

# Verify installation
python3 -c "import easyocr; print('EasyOCR version:', easyocr.__version__)"
```

**Expected Output:** `EasyOCR version: 1.7.x` or similar

---

## 2. Install ChromaDB (For Semantic Search)

```bash
# Run this in a new terminal
pip3 install chromadb sentence-transformers --break-system-packages

# Verify installation
python3 -c "import chromadb; print('ChromaDB installed:', chromadb.__version__)"
python3 -c "from sentence_transformers import SentenceTransformer; print('Sentence Transformers ready')"
```

**Expected Output:**
```
ChromaDB installed: 0.x.x
Sentence Transformers ready
```

---

## 3. Run Tests After Installation

```bash
# Navigate to project directory
cd /mnt/h/12-extractor

# Run unit tests
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -m pytest 04-tests/unit/ -v

# Run integration tests
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -m pytest 04-tests/integration/ -v

# Run E2E tests
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -m pytest 04-tests/e2e/ -v
```

---

## 4. Process Book 1 with Real OCR (After EasyOCR Installed)

```bash
# Clear existing sample data
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -c "
from sqlalchemy import text
from src.database.connection import SessionLocal

db = SessionLocal()
try:
    db.execute(text('DELETE FROM book1_01wessam_explanation_2026_knowledge_units'))
    db.execute(text('''
        UPDATE book1_01wessam_explanation_2026_processing_state
        SET paddleocr_complete = false, images_processed = true, current_page = 0
        WHERE id = 1
    '''))
    db.commit()
    print('Book 1 cleared, ready for real OCR')
finally:
    db.close()
"

# Run EasyOCR extraction (this will take ~30-60 minutes for 272 pages)
curl -X POST "http://localhost:7777/api/ocr/paddleocr" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'

# Monitor progress in logs
tail -f /mnt/h/12-extractor/03-code/app.log | grep "Processing page"
```

---

## 5. Initialize ChromaDB Collection

```bash
# After ChromaDB is installed, run this once
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -c "
import chromadb
from chromadb.config import Settings

# Create persistent client
client = chromadb.PersistentClient(path='/mnt/h/12-extractor/chroma_db')

# Create collection
collection = client.get_or_create_collection(
    name='knowledge_base_unified',
    metadata={'description': 'Unified collection for all books'}
)

print(f'ChromaDB initialized: {collection.count()} documents')
"
```

---

## 6. Test Verification Page

```bash
# Open in browser
# http://localhost:7777/verification

# Or test API directly
curl -s "http://localhost:7777/api/books/1/knowledge-units?limit=5" | python3 -m json.tool
```

---

## 7. Database Diagnostics

```bash
# Check books
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -c "
from sqlalchemy import text
from src.database.connection import SessionLocal

db = SessionLocal()
try:
    result = db.execute(text('SELECT book_id, book_name, processing_status FROM books_metadata')).fetchall()
    for row in result:
        print(f'Book {row[0]}: {row[1]} | Status: {row[2]}')
finally:
    db.close()
"

# Check knowledge units count
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -c "
from sqlalchemy import text
from src.database.connection import SessionLocal

db = SessionLocal()
try:
    count = db.execute(text('SELECT COUNT(*) FROM book1_01wessam_explanation_2026_knowledge_units')).scalar()
    print(f'Total knowledge units: {count}')

    with_text = db.execute(text('''
        SELECT COUNT(*) FROM book1_01wessam_explanation_2026_knowledge_units
        WHERE LENGTH(text_content) > 0
    ''')).scalar()
    print(f'Units with text: {with_text}')
finally:
    db.close()
"

# Check images
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -c "
from sqlalchemy import text
from src.database.connection import SessionLocal

db = SessionLocal()
try:
    count = db.execute(text('SELECT COUNT(*) FROM book1_01wessam_explanation_2026_images')).scalar()
    print(f'Total images: {count}')
finally:
    db.close()
"
```

---

## 8. Commit All Changes

```bash
cd /mnt/h/12-extractor

# Add all changes
git add -A

# Commit with message
git commit -m "feat: complete Option C implementation

- Session summary saved (SESSION-SUMMARY-2025-11-12.md)
- Manual setup commands documented
- Test cases updated
- ChromaDB integration prepared
- Ready for EasyOCR and full feature implementation

Remaining: EasyOCR installation, ChromaDB service, Marker agent"

# Push to remote (if configured)
git push origin master
```

---

## Expected Timeline

| Task | Duration | Status |
|------|----------|--------|
| EasyOCR installation | 10-15 min | 🔄 Run manually |
| ChromaDB installation | 5-10 min | 🔄 Run manually |
| EasyOCR processing (272 pages) | 30-60 min | ⏳ After install |
| ChromaDB indexing | 5-10 min | ⏳ After install |
| Test suite run | 5 min | ⏳ After all done |

---

## Troubleshooting

### If EasyOCR Fails to Install
```bash
# Try with pip cache clear
pip3 cache purge
pip3 install easyocr --break-system-packages --no-cache-dir

# Or install dependencies separately
pip3 install torch torchvision --break-system-packages
pip3 install opencv-python-headless --break-system-packages
pip3 install easyocr --break-system-packages
```

### If ChromaDB Fails
```bash
# Install build dependencies
sudo apt update
sudo apt install -y python3-dev build-essential

# Then try again
pip3 install chromadb --break-system-packages
```

### If Tests Fail
```bash
# Check Python path
echo $PYTHONPATH

# Should be: /mnt/h/12-extractor/03-code
export PYTHONPATH=/mnt/h/12-extractor/03-code

# Run individual test
PYTHONPATH=/mnt/h/12-extractor/03-code python3 -m pytest 04-tests/unit/test_chunk_024.py -v
```

---

## Quick Status Check

```bash
# Run this anytime to check system status
PYTHONPATH=/mnt/h/12-extractor/03-code python3 << 'EOF'
from sqlalchemy import text
from src.database.connection import SessionLocal

db = SessionLocal()
try:
    # Check books
    books = db.execute(text('SELECT COUNT(*) FROM books_metadata')).scalar()
    print(f'📚 Total books: {books}')

    # Check book 1 status
    state = db.execute(text('''
        SELECT current_page, paddleocr_complete, images_processed, status
        FROM book1_01wessam_explanation_2026_processing_state
        WHERE id = 1
    ''')).first()

    if state:
        print(f'📄 Book 1: Page {state[0]}/272 | OCR: {state[1]} | Images: {state[2]} | Status: {state[3]}')

    # Check knowledge units
    units = db.execute(text('SELECT COUNT(*) FROM book1_01wessam_explanation_2026_knowledge_units')).scalar()
    print(f'📝 Knowledge units: {units}')

    # Check images
    images = db.execute(text('SELECT COUNT(*) FROM book1_01wessam_explanation_2026_images')).scalar()
    print(f'🖼️  Images extracted: {images}')

finally:
    db.close()

# Check packages
try:
    import easyocr
    print('✅ EasyOCR installed')
except ImportError:
    print('❌ EasyOCR NOT installed - run: pip3 install easyocr --break-system-packages')

try:
    import chromadb
    print('✅ ChromaDB installed')
except ImportError:
    print('❌ ChromaDB NOT installed - run: pip3 install chromadb --break-system-packages')

EOF
```

---

**Last Updated:** 2025-11-12
**For:** Knowledge Extraction System
**Context:** Session continuation after context window reset
