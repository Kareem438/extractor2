# Duplicate File Upload Prevention - Requirements

**Date:** 2025-11-11
**Priority:** High
**Status:** Draft

---

## Business Requirements

### **BR-1: Duplicate Detection**
- **Requirement:** System must detect if a file with the same name and size has been uploaded before
- **Rationale:** Prevent accidental duplicate uploads and data inconsistency
- **Success Criteria:** System accurately identifies duplicates based on filename + file size

### **BR-2: File Integrity Validation**
- **Requirement:** System must verify if previously uploaded file is still readable/accessible
- **Rationale:** Allow re-upload if original file was corrupted or deleted
- **Success Criteria:** System can validate file existence and readability

### **BR-3: Upload Prevention for Valid Duplicates**
- **Requirement:** If duplicate exists and is readable, prevent upload with clear message
- **Rationale:** Avoid wasting storage and processing resources
- **Success Criteria:** User receives clear error message explaining why upload was blocked

### **BR-4: Allow Re-upload for Corrupted Files**
- **Requirement:** If duplicate exists but is NOT readable, allow upload and overwrite
- **Rationale:** Enable recovery from file corruption scenarios
- **Success Criteria:** System successfully overwrites corrupted files

### **BR-5: Display Uploaded Files List**
- **Requirement:** Show list of already uploaded files on the upload page
- **Rationale:** Help users avoid duplicate uploads by showing what's already uploaded
- **Success Criteria:** Upload page displays all previously uploaded books with key metadata

---

## Functional Requirements

### **FR-1: Duplicate Check Logic**
```
Input: filename, file_size
Process:
  1. Query books_metadata for matching filename AND file_size
  2. If no match: proceed with upload
  3. If match found: check file readability
  4. If file readable: reject upload with message
  5. If file not readable: allow upload and overwrite
Output: Upload decision (allow/reject) + message
```

### **FR-2: File Storage Path Tracking**
- **Current:** Files stored in `/tmp/book_uploads/` (temporary, can be deleted)
- **Proposed:** Store file path in `books_metadata` table for validation
- **New field needed:** `file_path` (VARCHAR 500)

### **FR-3: File Readability Check**
```python
def is_file_readable(file_path: str) -> bool:
    try:
        if not os.path.exists(file_path):
            return False
        with open(file_path, 'rb') as f:
            f.read(1024)  # Try reading first 1KB
        return True
    except:
        return False
```

### **FR-4: Uploaded Files Display**
- **Location:** Upload page (`/upload`)
- **Display:** Table or card grid showing:
  - Book name
  - Upload date
  - File size
  - File type
  - Processing status
  - Actions (View, Delete)
- **Sorting:** Most recent first
- **Pagination:** Show 10 per page

### **FR-5: Error Messages**
- **Duplicate exists (readable):** "This file has already been uploaded. Book: '{book_name}' (uploaded on {date}). Please use the existing book or rename your file."
- **Duplicate exists (not readable):** "Previous upload was corrupted. Re-uploading and overwriting..."
- **Upload successful:** "File uploaded successfully! Book ID: {book_id}"

---

## Non-Functional Requirements

### **NFR-1: Performance**
- Duplicate check must complete in < 100ms
- File readability check must complete in < 500ms
- Uploaded files list must load in < 1s

### **NFR-2: Storage**
- Move from `/tmp` (temporary) to permanent storage location
- Suggested: `/var/lib/knowledge-extractor/uploads/` or user-configurable path

### **NFR-3: Data Integrity**
- File path must be validated before storage
- Broken file paths must be detected and handled gracefully

---

## User Stories

### **US-1: Prevent Duplicate Upload**
**As a** user
**I want** the system to warn me if I'm uploading a duplicate file
**So that** I don't waste time and resources processing the same document twice

**Acceptance Criteria:**
- [ ] System detects when filename + size match existing upload
- [ ] User receives clear error message
- [ ] Upload is blocked for valid duplicates

### **US-2: View Uploaded Files**
**As a** user
**I want** to see a list of files I've already uploaded
**So that** I can avoid duplicate uploads and manage my books

**Acceptance Criteria:**
- [ ] Upload page shows list of all uploaded books
- [ ] List displays book name, date, size, and status
- [ ] List is sorted by most recent first

### **US-3: Recover from Corrupted Upload**
**As a** user
**I want** to re-upload a file if the previous upload was corrupted
**So that** I can recover from failed uploads without manual intervention

**Acceptance Criteria:**
- [ ] System detects when stored file is not readable
- [ ] User can re-upload and overwrite corrupted file
- [ ] Success message confirms overwrite

---

## Technical Considerations

### **Database Changes**
1. Add `file_path` column to `books_metadata` table
2. Create index on (`book_name`, `file_size_bytes`) for fast duplicate detection

### **API Changes**
1. New endpoint: `GET /api/books/uploaded` - List uploaded books
2. Modified endpoint: `POST /api/upload` - Add duplicate check

### **Frontend Changes**
1. Add "Uploaded Files" section to upload page
2. Add duplicate warning modal/alert
3. Update upload JavaScript to handle duplicate errors

---

## Open Questions

1. **File naming strategy:** Should we use original filename or sanitized name for comparison?
2. **Storage location:** Should permanent storage path be configurable via environment variable?
3. **Delete action:** Should users be able to delete uploaded files from the UI?
4. **Size threshold:** What file size difference should we consider as "same file"? (exact match vs ±1KB tolerance)

---

**Next Steps:**
1. ✅ Requirements documented
2. ⏳ Architecture design
3. ⏳ Test plan creation
4. ⏳ Implementation
5. ⏳ Deployment
