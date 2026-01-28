# Design: Safe Book Deletion Feature

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (HTML/JS)                          │
├─────────────────────────────────────────────────────────────────────┤
│  Library Page                    │  Book Settings Page              │
│  ┌─────────────────────────┐    │  ┌─────────────────────────────┐ │
│  │ Actions Column          │    │  │ PDF Path Display            │ │
│  │ [Delete] button         │    │  │ 📁 File: H:\path\file.pdf   │ │
│  └─────────────────────────┘    │  └─────────────────────────────┘ │
│                                  │  ┌─────────────────────────────┐ │
│                                  │  │ Danger Zone Section         │ │
│                                  │  │ [Delete Book] button        │ │
│                                  │  └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                    Confirmation Modals                              │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐│
│  │ Step 1: Summary Modal   │ -> │ Step 2: Code Verification Modal ││
│  │ - Book name             │    │ - Display: "7294"               ││
│  │ - Pages: 150            │    │ - Input: [____]                 ││
│  │ - Knowledge Units: 1250 │    │ - [Cancel] [Delete Book]        ││
│  │ - Images: 45            │    └─────────────────────────────────┘│
│  │ - Paragraph clips: 320  │                                       │
│  │ - Diagram clips: 28     │                                       │
│  │ ☑ Delete ChromaDB       │                                       │
│  │ [Cancel] [Continue]     │                                       │
│  └─────────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend API                                  │
├─────────────────────────────────────────────────────────────────────┤
│  GET /api/books/{book_id}/deletion-preview                          │
│  - Returns counts, file_path, can_delete status, confirmation_code  │
│                                                                      │
│  DELETE /api/books/{book_id}                                        │
│  - Validates confirmation_code                                       │
│  - Checks for active tasks                                          │
│  - Drops all book tables (transaction)                              │
│  - Deletes ChromaDB embeddings (if requested)                       │
│  - Removes books_metadata row                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## API Design

### GET /api/books/{book_id}/deletion-preview

Returns information needed for the deletion confirmation dialog.

**Response:**
```json
{
  "book_id": 1,
  "book_name": "Example Book",
  "file_path": "H:\\12-FILEs\\example.pdf",
  "table_prefix": "book1_example_book",
  "can_delete": true,
  "blocking_reason": null,
  "counts": {
    "pages": 150,
    "knowledge_units": 1250,
    "images": 45,
    "paragraph_clips": 320,
    "diagram_clips": 28,
    "chromadb_embeddings": 1250
  },
  "confirmation_code": "7294"
}
```

**Blocking Reasons:**
- `"processing"` - Book is currently being processed
- `"active_tasks"` - Book has pending/running pipeline tasks

### DELETE /api/books/{book_id}

Deletes all book data from the database.

**Request Body:**
```json
{
  "delete_chromadb": true,
  "confirmation_code": "7294"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Book 'Example Book' deleted successfully",
  "deleted": {
    "book_name": "Example Book",
    "tables_dropped": 17,
    "chromadb_deleted": true,
    "embeddings_removed": 1250
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Cannot delete book with active tasks",
  "active_tasks": 5
}
```

## Database Tables to Delete

For each book with prefix `book{id}_{sanitized_name}`:

### Raw Data Tables (4)
1. `raw_{prefix}_pages`
2. `raw_{prefix}_knowledge_units`
3. `raw_{prefix}_paragraph_images`
4. `raw_{prefix}_diagram_images`

### Processed Data Tables (7)
5. `{prefix}_knowledge_units`
6. `{prefix}_pages`
7. `{prefix}_images`
8. `{prefix}_processing_state`
9. `{prefix}_settings`
10. `{prefix}_hierarchy`
11. `{prefix}_attribute_keys`

### Worker System Tables (3)
12. `{prefix}_pipeline_config`
13. `{prefix}_task_queue`
14. `{prefix}_step_progress`

### Title Hierarchy Tables (2)
15. `{prefix}_level1_titles`
16. `{prefix}_level2_titles`

### Global Table Rows
17. Row from `books_metadata` WHERE book_id = {id}
18. Rows from `pdf_uploads` WHERE book_id = {id}
19. Rows from `cross_book_access_log` WHERE source_book_id = {id} OR target_book_id = {id}

## Frontend Components

### 1. Delete Button in Library (library.html / library.js)

Add to Actions column in `createBookRow()`:
```html
<button class="btn-action btn-delete" 
        onclick="initiateDeleteBook(${book.book_id}, '${escapeHtml(book.book_name)}')"
        ${book.processing_status === 'processing' ? 'disabled title="Cannot delete - book is processing"' : ''}>
    🗑️ Delete
</button>
```

### 2. PDF Path Display in Book Settings (book-settings.html)

Add under book name in `.book-info` section:
```html
<div class="pdf-path-display" id="pdf-path-display">
    📁 File: <span id="pdf-file-path">Loading...</span>
</div>
```

### 3. Danger Zone Section in Book Settings (book-settings.html)

Add at bottom of `.book-content`:
```html
<div class="danger-zone-section">
    <h2>⚠️ Danger Zone</h2>
    <p>Permanently delete this book and all associated data.</p>
    <button class="btn-danger" id="btn-delete-book" onclick="initiateDeleteBook()">
        🗑️ Delete This Book
    </button>
</div>
```

### 4. Confirmation Modals (shared component)

**Step 1 Modal - Summary:**
```html
<div class="modal-overlay" id="delete-summary-modal">
    <div class="modal-content delete-modal">
        <div class="modal-header">
            <h3>🗑️ Delete Book</h3>
            <button class="modal-close" onclick="closeDeleteModals()">&times;</button>
        </div>
        <div class="modal-body">
            <p class="delete-warning">You are about to delete:</p>
            <div class="delete-summary">
                <div class="summary-item"><strong>Book:</strong> <span id="delete-book-name"></span></div>
                <div class="summary-item"><strong>Pages:</strong> <span id="delete-pages-count"></span></div>
                <div class="summary-item"><strong>Knowledge Units:</strong> <span id="delete-ku-count"></span></div>
                <div class="summary-item"><strong>Images:</strong> <span id="delete-images-count"></span></div>
                <div class="summary-item"><strong>Paragraph Clips:</strong> <span id="delete-para-count"></span></div>
                <div class="summary-item"><strong>Diagram Clips:</strong> <span id="delete-diag-count"></span></div>
            </div>
            <div class="chromadb-option">
                <label>
                    <input type="checkbox" id="delete-chromadb-checkbox" checked>
                    Also delete ChromaDB embeddings (<span id="delete-embeddings-count"></span> vectors)
                </label>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-modal btn-modal-cancel" onclick="closeDeleteModals()">Cancel</button>
            <button class="btn-modal btn-modal-danger" onclick="showCodeVerification()">Continue</button>
        </div>
    </div>
</div>
```

**Step 2 Modal - Code Verification:**
```html
<div class="modal-overlay" id="delete-code-modal">
    <div class="modal-content delete-modal">
        <div class="modal-header">
            <h3>🔐 Final Confirmation</h3>
            <button class="modal-close" onclick="closeDeleteModals()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Type the following code to confirm deletion:</p>
            <div class="confirmation-code" id="confirmation-code-display">7294</div>
            <input type="text" id="confirmation-code-input" 
                   placeholder="Enter code" maxlength="4"
                   oninput="validateConfirmationCode()">
            <p class="code-hint">This action cannot be undone.</p>
        </div>
        <div class="modal-footer">
            <button class="btn-modal btn-modal-cancel" onclick="closeDeleteModals()">Cancel</button>
            <button class="btn-modal btn-modal-danger" id="btn-confirm-delete" 
                    onclick="executeDelete()" disabled>Delete Book</button>
        </div>
    </div>
</div>
```

## CSS Styles

```css
/* Danger Zone Section */
.danger-zone-section {
    background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%);
    border: 2px solid #f44336;
    border-radius: 8px;
    padding: 30px;
    margin-top: 30px;
}
.danger-zone-section h2 {
    color: #c62828;
    margin-top: 0;
    border-bottom: 2px solid #f44336;
    padding-bottom: 10px;
}
.btn-danger {
    background: #f44336;
    color: white;
    padding: 12px 24px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
}
.btn-danger:hover { background: #d32f2f; }
.btn-danger:disabled { background: #ccc; cursor: not-allowed; }

/* PDF Path Display */
.pdf-path-display {
    color: #666;
    font-size: 13px;
    margin-top: 8px;
    padding: 8px 12px;
    background: #f5f5f5;
    border-radius: 4px;
    font-family: monospace;
}

/* Delete Modal Styles */
.delete-modal { max-width: 500px; }
.delete-warning { color: #c62828; font-weight: bold; margin-bottom: 15px; }
.delete-summary {
    background: #f5f5f5;
    padding: 15px;
    border-radius: 4px;
    margin-bottom: 15px;
}
.summary-item { margin: 8px 0; }
.chromadb-option { margin: 15px 0; }
.confirmation-code {
    font-size: 48px;
    font-weight: bold;
    text-align: center;
    color: #f44336;
    letter-spacing: 10px;
    margin: 20px 0;
    font-family: monospace;
}
#confirmation-code-input {
    width: 100%;
    padding: 15px;
    font-size: 24px;
    text-align: center;
    letter-spacing: 10px;
    border: 2px solid #e0e0e0;
    border-radius: 4px;
}
.code-hint { color: #999; font-size: 12px; text-align: center; margin-top: 10px; }
.btn-modal-danger { background: #f44336; color: white; }
.btn-modal-danger:disabled { background: #ccc; }

/* Toast Notification */
.toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 15px 25px;
    border-radius: 4px;
    color: white;
    font-weight: bold;
    z-index: 10000;
    animation: slideIn 0.3s ease;
}
.toast-success { background: #4CAF50; }
.toast-error { background: #f44336; }
@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
```

## JavaScript Functions

### library.js additions:
```javascript
// State for deletion
let deleteBookData = null;

// Initiate delete from Library
async function initiateDeleteBook(bookId, bookName) {
    try {
        const response = await fetch(`/api/books/${bookId}/deletion-preview`);
        const data = await response.json();
        
        if (!data.can_delete) {
            alert(`Cannot delete: ${data.blocking_reason}`);
            return;
        }
        
        deleteBookData = data;
        showDeleteSummaryModal(data);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function showDeleteSummaryModal(data) {
    document.getElementById('delete-book-name').textContent = data.book_name;
    document.getElementById('delete-pages-count').textContent = data.counts.pages;
    document.getElementById('delete-ku-count').textContent = data.counts.knowledge_units;
    document.getElementById('delete-images-count').textContent = data.counts.images;
    document.getElementById('delete-para-count').textContent = data.counts.paragraph_clips;
    document.getElementById('delete-diag-count').textContent = data.counts.diagram_clips;
    document.getElementById('delete-embeddings-count').textContent = data.counts.chromadb_embeddings;
    
    document.getElementById('delete-summary-modal').classList.add('active');
}

function showCodeVerification() {
    document.getElementById('delete-summary-modal').classList.remove('active');
    document.getElementById('confirmation-code-display').textContent = deleteBookData.confirmation_code;
    document.getElementById('confirmation-code-input').value = '';
    document.getElementById('btn-confirm-delete').disabled = true;
    document.getElementById('delete-code-modal').classList.add('active');
}

function validateConfirmationCode() {
    const input = document.getElementById('confirmation-code-input').value;
    const expected = deleteBookData.confirmation_code;
    document.getElementById('btn-confirm-delete').disabled = (input !== expected);
}

async function executeDelete() {
    const deleteChromadb = document.getElementById('delete-chromadb-checkbox').checked;
    const code = document.getElementById('confirmation-code-input').value;
    
    try {
        const response = await fetch(`/api/books/${deleteBookData.book_id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                delete_chromadb: deleteChromadb,
                confirmation_code: code
            })
        });
        
        const result = await response.json();
        
        closeDeleteModals();
        
        if (result.success) {
            showToast(`Book "${deleteBookData.book_name}" deleted successfully`, 'success');
            loadBooks(); // Refresh the list
        } else {
            showToast(result.error, 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

function closeDeleteModals() {
    document.getElementById('delete-summary-modal').classList.remove('active');
    document.getElementById('delete-code-modal').classList.remove('active');
    deleteBookData = null;
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}
```

## Backend Implementation

### File: `03-code/src/api/routes/delete_book.py`

```python
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
import random
from src.database.connection import engine, SessionLocal
from src.services.chroma_service import chroma_service

router = APIRouter()

class DeleteBookRequest(BaseModel):
    delete_chromadb: bool = True
    confirmation_code: str

# Store confirmation codes temporarily (in production, use Redis/cache)
confirmation_codes = {}

@router.get("/books/{book_id}/deletion-preview")
async def get_deletion_preview(book_id: int):
    """Get deletion preview with counts and confirmation code."""
    db = SessionLocal()
    try:
        # Get book info
        book = db.execute(
            text("SELECT book_id, book_name, file_path, table_prefix, processing_status FROM books_metadata WHERE book_id = :id"),
            {"id": book_id}
        ).fetchone()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Check if can delete
        can_delete = True
        blocking_reason = None
        
        if book.processing_status == 'processing':
            can_delete = False
            blocking_reason = "Book is currently being processed"
        
        # Check for active tasks
        task_table = f"{book.table_prefix}_task_queue"
        try:
            active_tasks = db.execute(
                text(f"SELECT COUNT(*) FROM {task_table} WHERE status IN ('pending', 'running')")
            ).scalar()
            if active_tasks > 0:
                can_delete = False
                blocking_reason = f"Book has {active_tasks} active pipeline tasks"
        except:
            pass  # Table might not exist
        
        # Get counts
        counts = get_book_counts(db, book.table_prefix, book_id)
        
        # Generate confirmation code
        code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        confirmation_codes[book_id] = code
        
        return {
            "book_id": book_id,
            "book_name": book.book_name,
            "file_path": book.file_path,
            "table_prefix": book.table_prefix,
            "can_delete": can_delete,
            "blocking_reason": blocking_reason,
            "counts": counts,
            "confirmation_code": code
        }
    finally:
        db.close()

@router.delete("/books/{book_id}")
async def delete_book(book_id: int, request: DeleteBookRequest):
    """Delete a book and all associated data."""
    # Verify confirmation code
    if book_id not in confirmation_codes or confirmation_codes[book_id] != request.confirmation_code:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    
    db = SessionLocal()
    try:
        # Get book info
        book = db.execute(
            text("SELECT book_name, table_prefix FROM books_metadata WHERE book_id = :id"),
            {"id": book_id}
        ).fetchone()
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Drop all book tables
        tables_dropped = drop_book_tables(db, book.table_prefix)
        
        # Delete from global tables
        db.execute(text("DELETE FROM pdf_uploads WHERE book_id = :id"), {"id": book_id})
        db.execute(text("DELETE FROM cross_book_access_log WHERE source_book_id = :id OR target_book_id = :id"), {"id": book_id})
        db.execute(text("DELETE FROM books_metadata WHERE book_id = :id"), {"id": book_id})
        
        db.commit()
        
        # Delete ChromaDB embeddings
        embeddings_removed = 0
        if request.delete_chromadb:
            embeddings_removed = chroma_service.delete_by_book_id(book_id)
        
        # Clean up confirmation code
        del confirmation_codes[book_id]
        
        return {
            "success": True,
            "message": f"Book '{book.book_name}' deleted successfully",
            "deleted": {
                "book_name": book.book_name,
                "tables_dropped": tables_dropped,
                "chromadb_deleted": request.delete_chromadb,
                "embeddings_removed": embeddings_removed
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def get_book_counts(db, table_prefix, book_id):
    """Get counts of various entities for a book."""
    counts = {
        "pages": 0,
        "knowledge_units": 0,
        "images": 0,
        "paragraph_clips": 0,
        "diagram_clips": 0,
        "chromadb_embeddings": 0
    }
    
    try:
        counts["pages"] = db.execute(text(f"SELECT COUNT(*) FROM raw_{table_prefix}_pages")).scalar() or 0
    except: pass
    
    try:
        counts["knowledge_units"] = db.execute(text(f"SELECT COUNT(*) FROM {table_prefix}_knowledge_units")).scalar() or 0
    except: pass
    
    try:
        counts["images"] = db.execute(text(f"SELECT COUNT(*) FROM {table_prefix}_images")).scalar() or 0
    except: pass
    
    try:
        counts["paragraph_clips"] = db.execute(text(f"SELECT COUNT(*) FROM raw_{table_prefix}_paragraph_images")).scalar() or 0
    except: pass
    
    try:
        counts["diagram_clips"] = db.execute(text(f"SELECT COUNT(*) FROM raw_{table_prefix}_diagram_images")).scalar() or 0
    except: pass
    
    # ChromaDB count
    try:
        counts["chromadb_embeddings"] = chroma_service.count_by_book_id(book_id)
    except: pass
    
    return counts

def drop_book_tables(db, table_prefix):
    """Drop all tables for a book."""
    tables = [
        f"raw_{table_prefix}_pages",
        f"raw_{table_prefix}_knowledge_units",
        f"raw_{table_prefix}_paragraph_images",
        f"raw_{table_prefix}_diagram_images",
        f"{table_prefix}_knowledge_units",
        f"{table_prefix}_pages",
        f"{table_prefix}_images",
        f"{table_prefix}_processing_state",
        f"{table_prefix}_settings",
        f"{table_prefix}_hierarchy",
        f"{table_prefix}_attribute_keys",
        f"{table_prefix}_pipeline_config",
        f"{table_prefix}_task_queue",
        f"{table_prefix}_step_progress",
        f"{table_prefix}_level1_titles",
        f"{table_prefix}_level2_titles",
    ]
    
    dropped = 0
    for table in tables:
        try:
            db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            dropped += 1
        except:
            pass
    
    return dropped
```

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `03-code/src/api/routes/delete_book.py` | Create | New API routes for deletion |
| `03-code/src/main.py` | Modify | Register delete_book router |
| `03-code/src/frontend/templates/library.html` | Modify | Add delete modals HTML |
| `03-code/src/frontend/static/js/library.js` | Modify | Add delete button and modal functions |
| `03-code/src/frontend/templates/book-settings.html` | Modify | Add PDF path display and Danger Zone |
| `03-code/src/frontend/static/js/book-settings.js` | Modify | Add delete functions for settings page |
| `03-code/src/services/chroma_service.py` | Modify | Add delete_by_book_id and count_by_book_id methods |
