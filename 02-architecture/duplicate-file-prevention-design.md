# Duplicate File Upload Prevention - Architecture Design

**Date:** 2025-11-11
**Architect:** Claude Code
**Status:** Design Complete

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Upload Flow                              │
└─────────────────────────────────────────────────────────────────┘

User Upload Request
        ↓
┌───────────────────────┐
│  1. File Validation   │  (Size, Type, Empty check)
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  2. Duplicate Check   │
│   - Query by name+size│
│   - If found → check  │
│     file readability  │
└──────────┬────────────┘
           ↓
     ┌────┴────┐
     │ Exists? │
     └────┬────┘
          │
    ┌─────┴─────┐
    │           │
   YES         NO
    │           │
    ↓           ↓
┌─────────┐  ┌─────────┐
│ Check   │  │ Proceed │
│ File    │  │ Upload  │
│ Readable│  └─────────┘
└────┬────┘
     │
┌────┴────┐
│Readable?│
└────┬────┘
     │
 ┌───┴───┐
 │       │
YES     NO
 │       │
 ↓       ↓
REJECT  OVERWRITE
Upload  Old File
```

---

## Component Design

### **1. Database Schema Changes**

#### **Add to `books_metadata` table:**
```sql
ALTER TABLE books_metadata
ADD COLUMN file_path VARCHAR(500),
ADD COLUMN file_hash VARCHAR(64);  -- Optional: SHA-256 for better duplicate detection

CREATE INDEX idx_books_duplicate_check
ON books_metadata (book_name, file_size_bytes);
```

---

### **2. New Service: DuplicateCheckService**

**Location:** `03-code/src/services/duplicate_check_service.py`

```python
class DuplicateCheckService:
    """
    Service for checking and managing duplicate file uploads.
    """

    def check_duplicate(self, filename: str, file_size: int) -> DuplicateCheckResult:
        """
        Check if file is duplicate based on name and size.

        Returns:
            DuplicateCheckResult with:
            - is_duplicate: bool
            - existing_book_id: int | None
            - file_readable: bool
            - action: 'allow' | 'reject' | 'overwrite'
            - message: str
        """

    def is_file_readable(self, file_path: str) -> bool:
        """Check if file exists and is readable."""

    def get_uploaded_books(self, limit: int = 10, offset: int = 0) -> List[BookSummary]:
        """Get list of uploaded books with metadata."""
```

---

### **3. API Endpoint: List Uploaded Books**

**New Route:** `GET /api/books/list`

```python
@router.get("/books/list")
async def list_uploaded_books(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> ListBooksResponse:
    """
    Get list of uploaded books.

    Query Parameters:
        limit: Number of books to return (default: 10)
        offset: Pagination offset (default: 0)

    Returns:
        {
            "books": [
                {
                    "book_id": 1,
                    "book_name": "My Book",
                    "file_size_bytes": 1048576,
                    "file_type": "PDF",
                    "total_pages": 100,
                    "upload_date": "2025-11-11T10:30:00",
                    "processing_status": "ready",
                    "file_readable": true
                }
            ],
            "total": 25,
            "limit": 10,
            "offset": 0
        }
    """
```

---

### **4. Modified Endpoint: Upload with Duplicate Check**

**Modified Route:** `POST /api/upload`

```python
@router.post("/upload")
async def upload_file(...):
    # ... existing validation ...

    # NEW: Check for duplicates
    duplicate_service = DuplicateCheckService()
    check_result = duplicate_service.check_duplicate(
        filename=file.filename,
        file_size=file_size
    )

    if check_result.action == 'reject':
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_file",
                "message": check_result.message,
                "existing_book_id": check_result.existing_book_id
            }
        )

    if check_result.action == 'overwrite':
        logger.info(f"Overwriting corrupted file for book {check_result.existing_book_id}")
        book_id = check_result.existing_book_id
        # Delete old file
        # Continue with upload using same book_id
    else:
        # Normal new upload
        book_id = get_next_book_id()

    # ... rest of upload logic ...
```

---

### **5. Frontend Changes**

#### **A. Upload Page - Uploaded Files Section**

**Location:** `03-code/src/frontend/templates/upload.html`

Add section before upload form:

```html
<!-- Uploaded Files Section -->
<section class="uploaded-files-section">
    <h2>Previously Uploaded Files</h2>
    <div id="uploaded-files-container">
        <!-- Will be populated by JavaScript -->
        <div class="loading">Loading uploaded files...</div>
    </div>
</section>
```

#### **B. Upload JavaScript - Duplicate Handling**

**Location:** `03-code/src/frontend/static/js/upload.js`

```javascript
// Load uploaded files on page load
async function loadUploadedFiles() {
    try {
        const response = await fetch('/api/books/list?limit=10');
        const data = await response.json();
        displayUploadedFiles(data.books);
    } catch (error) {
        console.error('Error loading uploaded files:', error);
    }
}

// Handle duplicate error (409 status)
async function handleUpload() {
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (response.status === 409) {
            const errorData = await response.json();
            showDuplicateWarning(errorData);
            return;
        }

        // ... handle success ...
    } catch (error) {
        // ... error handling ...
    }
}

// Show duplicate warning modal
function showDuplicateWarning(errorData) {
    const modal = document.createElement('div');
    modal.className = 'modal duplicate-warning';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>⚠️ Duplicate File Detected</h3>
            <p>${errorData.detail.message}</p>
            <p>Existing Book ID: #${errorData.detail.existing_book_id}</p>
            <div class="modal-actions">
                <button onclick="closeModal()">Cancel</button>
                <button onclick="viewExistingBook(${errorData.detail.existing_book_id})">View Existing Book</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}
```

---

## Data Flow Diagrams

### **Duplicate Check Flow**

```
┌────────────────┐
│ Upload Request │
└───────┬────────┘
        ↓
┌───────────────────────────────┐
│ DuplicateCheckService         │
│ check_duplicate()             │
│                               │
│ 1. Query books_metadata       │
│    WHERE book_name = ?        │
│    AND file_size_bytes = ?    │
└───────┬───────────────────────┘
        ↓
   ┌────┴────┐
   │ Found?  │
   └────┬────┘
        │
    ┌───┴───┐
    NO      YES
    │       │
    ↓       ↓
 ┌──────┐ ┌──────────────────┐
 │ALLOW │ │Check file_path   │
 │      │ │is_file_readable()│
 └──────┘ └────┬─────────────┘
               ↓
          ┌────┴────┐
          │Readable?│
          └────┬────┘
               │
           ┌───┴───┐
           YES     NO
           │       │
           ↓       ↓
        ┌──────┐ ┌─────────┐
        │REJECT│ │OVERWRITE│
        └──────┘ └─────────┘
```

---

## Storage Strategy

### **Current (Problem):**
- Files stored in `/tmp/book_uploads/`
- `/tmp` is cleared on reboot
- No persistent storage

### **Proposed Solution:**

#### **Option 1: Environment-Configurable Path (Recommended)**
```python
# .env
UPLOAD_STORAGE_PATH=/var/lib/knowledge-extractor/uploads

# Config
upload_dir = settings.UPLOAD_STORAGE_PATH
os.makedirs(upload_dir, exist_ok=True, mode=0o755)
```

#### **Option 2: Database Storage**
- Store files as BYTEA in PostgreSQL
- Pros: All data in one place, automatic backups
- Cons: Larger database size, slower queries
- Not recommended for large PDFs

#### **Chosen: Option 1**
- Store files in persistent directory
- Store path in `books_metadata.file_path`
- Allows easy backup and management

---

## Error Handling

### **Error Codes**

| Code | HTTP Status | Scenario | Message |
|------|-------------|----------|---------|
| `duplicate_file` | 409 | Duplicate exists, file readable | "This file has already been uploaded..." |
| `file_not_readable` | 200 | Duplicate exists, file corrupted | "Previous upload corrupted. Overwriting..." |
| `storage_error` | 500 | Cannot write to storage | "Failed to save file to storage" |
| `invalid_file` | 400 | Empty or invalid file | "Invalid file" |

---

## Performance Considerations

### **Database Optimization**
```sql
-- Index for fast duplicate check
CREATE INDEX idx_books_duplicate_check
ON books_metadata (book_name, file_size_bytes);

-- Query performance: < 50ms for duplicate check
EXPLAIN ANALYZE
SELECT book_id, file_path, upload_date
FROM books_metadata
WHERE book_name = 'test.pdf'
AND file_size_bytes = 1048576;
```

### **File I/O Optimization**
```python
# Only read first 1KB to check readability (fast)
def is_file_readable(file_path: str) -> bool:
    try:
        with open(file_path, 'rb') as f:
            f.read(1024)  # Read only 1KB
        return True
    except:
        return False
```

---

## Security Considerations

1. **Path Traversal Protection:**
   ```python
   # Validate file path is within allowed directory
   safe_path = os.path.realpath(file_path)
   if not safe_path.startswith(upload_dir):
       raise SecurityError("Invalid file path")
   ```

2. **File Permissions:**
   ```python
   # Set restrictive permissions
   os.chmod(file_path, 0o600)  # rw-------
   ```

3. **Input Validation:**
   - Sanitize filenames
   - Validate file types
   - Check file size limits

---

## Migration Strategy

### **Step 1: Database Migration**
```sql
-- Add new columns
ALTER TABLE books_metadata ADD COLUMN file_path VARCHAR(500);
ALTER TABLE books_metadata ADD COLUMN file_hash VARCHAR(64);

-- Create index
CREATE INDEX idx_books_duplicate_check ON books_metadata (book_name, file_size_bytes);

-- Backfill existing records
UPDATE books_metadata
SET file_path = '/tmp/book_uploads/' || book_name || '.pdf'
WHERE file_path IS NULL;
```

### **Step 2: Code Deployment**
1. Deploy new service code
2. Update upload endpoint
3. Deploy frontend changes
4. Test duplicate detection

### **Step 3: Storage Migration**
```bash
# Create permanent storage directory
sudo mkdir -p /var/lib/knowledge-extractor/uploads
sudo chown $USER:$USER /var/lib/knowledge-extractor/uploads
sudo chmod 755 /var/lib/knowledge-extractor/uploads

# Move existing files from /tmp (if any)
mv /tmp/book_uploads/* /var/lib/knowledge-extractor/uploads/
```

---

## Testing Strategy

1. **Unit Tests:**
   - DuplicateCheckService methods
   - File readability checks
   - Path sanitization

2. **Integration Tests:**
   - Upload with no duplicates
   - Upload with readable duplicate
   - Upload with corrupted duplicate
   - List uploaded books

3. **UI Tests:**
   - Display uploaded files
   - Show duplicate warning
   - Handle overwrite scenario

---

## Rollout Plan

### **Phase 1: Backend (Week 1)**
- [ ] Add database columns
- [ ] Create DuplicateCheckService
- [ ] Modify upload endpoint
- [ ] Create list books endpoint
- [ ] Write unit tests

### **Phase 2: Frontend (Week 1)**
- [ ] Add uploaded files section
- [ ] Implement duplicate warning modal
- [ ] Update upload.js
- [ ] Write UI tests

### **Phase 3: Testing & Deployment (Week 2)**
- [ ] Integration testing
- [ ] User acceptance testing
- [ ] Production deployment
- [ ] Monitor for issues

---

**Architecture Status:** ✅ COMPLETE
**Next Phase:** Test Plan Creation
