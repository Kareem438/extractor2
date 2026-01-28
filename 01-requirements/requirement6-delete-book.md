# Requirement 6: Delete Book Feature

**Feature:** Safe Book Deletion with Two-Step Confirmation  
**Created:** January 28, 2026  
**Status:** Design Complete - Ready for Implementation

---

## 1. Overview

Implement a secure book deletion feature that removes all database records associated with a book while preserving the original PDF file on disk. The deletion process requires two confirmation steps to prevent accidental data loss.

---

## 2. Clarification Questions & Answers

| # | Question | Answer |
|---|----------|--------|
| Q1 | Where should the Delete button be placed? | **C) Both locations** - Library page (Actions column) AND Book Settings page (Danger Zone section) |
| Q2 | What happens to the PDF file on disk? | **B) Keep PDF on disk** - Only delete database records. Also show PDF file path in Book Settings. |
| Q3 | Should there be deletion restrictions? | **C) Block deletion** for books with active pipeline tasks or worker jobs until tasks complete |
| Q4 | Should ChromaDB data be deleted? | **C) User choice** with checkbox (default: checked = delete ChromaDB data) |
| Q5 | What to show in first confirmation? | **B) Detailed summary** - book name, pages count, knowledge units count, images count |
| Q6 | What happens after successful deletion? | **A) Toast notification** and stay on same page (refresh book list if on Library) |

---

## 3. Feature Details

### 3.1 Delete Button Locations

#### Library Page (Actions Column)
- Add red "Delete" button in the Actions column for each book row
- Button should be disabled (grayed out) if book has active tasks
- Tooltip on disabled button: "Cannot delete - book has active tasks"

#### Book Settings Page (Danger Zone)
- Add new "Danger Zone" section at the bottom of the page
- Red-bordered section with warning styling
- Contains Delete button and explanation text
- Also disabled if book has active tasks

### 3.2 PDF File Path Display (Book Settings)

- Display the full file system path of the PDF file
- Location: Right under the book name at the top of Book Settings page
- Format: "📁 File: H:\path\to\file.pdf"
- Read-only display (not editable)

### 3.3 Two-Step Confirmation Flow

#### Step 1: Summary Confirmation Modal
- Title: "Delete Book: {book_name}"
- Content:
  - Book name
  - Total pages: X
  - Knowledge units: X
  - Images: X
  - Paragraph clips: X
  - Diagram clips: X
- Checkbox: "☑ Also delete ChromaDB embeddings" (default: checked)
- Buttons: "Cancel" | "Continue to Final Confirmation"

#### Step 2: Code Verification Modal
- Title: "Final Confirmation Required"
- Display: 4 random digits (e.g., "7294")
- Input field: "Type the code above to confirm deletion"
- Validation: Only enable Delete button when code matches exactly
- Buttons: "Cancel" | "Delete Book" (disabled until code matches)

### 3.4 Deletion Restrictions

Before allowing deletion, check:
1. `processing_status` in `books_metadata` is NOT 'processing'
2. No pending/running tasks in `{prefix}_task_queue` table
3. Worker is not actively processing this book

If any condition fails:
- Disable Delete button
- Show tooltip explaining why deletion is blocked

### 3.5 What Gets Deleted

#### PostgreSQL Tables (all 17+ book-specific tables):
1. `raw_{prefix}_pages`
2. `raw_{prefix}_knowledge_units`
3. `raw_{prefix}_paragraph_images`
4. `raw_{prefix}_diagram_images`
5. `{prefix}_knowledge_units`
6. `{prefix}_pages`
7. `{prefix}_images`
8. `{prefix}_processing_state`
9. `{prefix}_settings`
10. `{prefix}_hierarchy`
11. `{prefix}_attribute_keys`
12. `{prefix}_pipeline_config`
13. `{prefix}_task_queue`
14. `{prefix}_step_progress`
15. `{prefix}_level1_titles`
16. `{prefix}_level2_titles`
17. Row from `books_metadata` table
18. Rows from `pdf_uploads` table (if multi-PDF)
19. Rows from `cross_book_access_log` table

#### ChromaDB (if checkbox checked):
- Delete all embeddings with `book_id` metadata matching the deleted book

#### NOT Deleted:
- Original PDF file(s) on disk (preserved for potential re-upload)

### 3.6 Post-Deletion Behavior

- Show success toast: "Book '{book_name}' deleted successfully"
- If on Library page: Refresh the book list
- If on Book Settings page: Redirect to Library page
- Update header stats (total books, units, images counts)

---

## 4. User Stories

### US-6.1: Delete Book from Library
**As a** user  
**I want to** delete a book directly from the Library page  
**So that** I can quickly remove unwanted books without navigating to settings

**Acceptance Criteria:**
- [ ] Delete button visible in Actions column for each book
- [ ] Button disabled for books with active tasks
- [ ] Clicking triggers two-step confirmation flow
- [ ] Book list refreshes after successful deletion

### US-6.2: Delete Book from Settings
**As a** user  
**I want to** delete a book from the Book Settings page  
**So that** I can review book details before deciding to delete

**Acceptance Criteria:**
- [ ] Danger Zone section visible at bottom of Book Settings
- [ ] Delete button with warning styling
- [ ] Button disabled for books with active tasks
- [ ] Redirects to Library after successful deletion

### US-6.3: View PDF File Location
**As a** user  
**I want to** see where the PDF file is stored on disk  
**So that** I can locate it if needed after deletion

**Acceptance Criteria:**
- [ ] File path displayed under book name in Book Settings
- [ ] Path is read-only (not editable)
- [ ] Full absolute path shown

### US-6.4: Two-Step Confirmation
**As a** user  
**I want to** confirm deletion with a code verification  
**So that** I don't accidentally delete important data

**Acceptance Criteria:**
- [ ] First modal shows deletion summary with counts
- [ ] ChromaDB checkbox available (default checked)
- [ ] Second modal requires typing 4-digit code
- [ ] Delete button only enabled when code matches

### US-6.5: Deletion Restrictions
**As a** user  
**I want to** be prevented from deleting books with active tasks  
**So that** I don't corrupt ongoing processing

**Acceptance Criteria:**
- [ ] Delete button disabled for books being processed
- [ ] Tooltip explains why deletion is blocked
- [ ] API returns error if deletion attempted on active book

---

## 5. API Design

### DELETE /api/books/{book_id}

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
  "message": "Book deleted successfully",
  "deleted": {
    "book_name": "Example Book",
    "tables_dropped": 17,
    "chromadb_deleted": true,
    "embeddings_removed": 1250
  }
}
```

**Response (Error - Active Tasks):**
```json
{
  "success": false,
  "error": "Cannot delete book with active tasks",
  "active_tasks": 5
}
```

### GET /api/books/{book_id}/deletion-preview

**Response:**
```json
{
  "book_id": 1,
  "book_name": "Example Book",
  "file_path": "H:\\path\\to\\file.pdf",
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

---

## 6. Technical Notes

### Database Tables to Drop
Use `DROP TABLE IF EXISTS {table_name} CASCADE` for each book-specific table.

### Table Prefix Pattern
Tables follow pattern: `book{id}_{sanitized_name}_{table_type}`
Example: `book1_mybook_knowledge_units`

### ChromaDB Deletion
Use ChromaDB's `delete()` method with filter: `{"book_id": book_id}`

### Transaction Safety
Wrap all deletions in a database transaction. If any step fails, rollback all changes.

---

## 7. UI Mockup References

- Library page Actions column: See existing button patterns in `library.html`
- Book Settings Danger Zone: Similar to GitHub's repository danger zone
- Confirmation modals: Reuse existing modal patterns from `auto-slicer.html`

---

## 8. Dependencies

- Existing: `books_metadata` table, `table_creator.py`, `chroma_service.py`
- New: Delete book API endpoint, deletion preview API endpoint
