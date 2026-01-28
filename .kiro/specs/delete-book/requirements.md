# Requirements: Safe Book Deletion Feature

## Overview
Implement a secure book deletion feature with two-step confirmation that removes all database records while preserving the original PDF file on disk.

## User Stories

### US-6.1: Delete Book from Library
**As a** user  
**I want to** delete a book directly from the Library page  
**So that** I can quickly remove unwanted books without navigating to settings

**Acceptance Criteria:**
- Delete button visible in Actions column for each book row
- Button disabled (grayed out) for books with active pipeline tasks
- Tooltip shows "Cannot delete - book has active tasks" when disabled
- Clicking triggers two-step confirmation flow
- Book list refreshes after successful deletion
- Success toast notification displayed

### US-6.2: Delete Book from Settings
**As a** user  
**I want to** delete a book from the Book Settings page  
**So that** I can review book details before deciding to delete

**Acceptance Criteria:**
- "Danger Zone" section visible at bottom of Book Settings page
- Red-bordered section with warning styling
- Delete button with red background
- Button disabled for books with active tasks
- Redirects to Library after successful deletion

### US-6.3: View PDF File Location
**As a** user  
**I want to** see where the PDF file is stored on disk  
**So that** I can locate it if needed after deletion

**Acceptance Criteria:**
- File path displayed under book name in Book Settings header
- Format: "📁 File: H:\path\to\file.pdf"
- Path is read-only (not editable)
- Full absolute path shown

### US-6.4: Two-Step Confirmation
**As a** user  
**I want to** confirm deletion with a code verification  
**So that** I don't accidentally delete important data

**Acceptance Criteria:**
- First modal shows deletion summary with counts:
  - Book name
  - Total pages
  - Knowledge units count
  - Images count
  - Paragraph clips count
  - Diagram clips count
- Checkbox for "Also delete ChromaDB embeddings" (default: checked)
- Second modal displays 4 random digits
- Input field to type the code
- Delete button only enabled when code matches exactly
- Cancel button available on both modals

### US-6.5: Deletion Restrictions
**As a** user  
**I want to** be prevented from deleting books with active tasks  
**So that** I don't corrupt ongoing processing

**Acceptance Criteria:**
- Delete button disabled for books being processed
- Check processing_status in books_metadata
- Check for pending/running tasks in task_queue table
- Tooltip explains why deletion is blocked
- API returns error if deletion attempted on active book

### US-6.6: Complete Data Removal
**As a** user  
**I want to** have all book data removed from the database  
**So that** I can free up storage and remove unwanted data

**Acceptance Criteria:**
- All 17+ book-specific PostgreSQL tables dropped
- Row removed from books_metadata table
- Related rows removed from pdf_uploads table
- Related rows removed from cross_book_access_log table
- ChromaDB embeddings deleted (if checkbox checked)
- Original PDF file preserved on disk

## Non-Functional Requirements

### NFR-1: Transaction Safety
All database deletions must be wrapped in a transaction. If any step fails, all changes must be rolled back.

### NFR-2: Performance
Deletion should complete within 30 seconds for books with up to 1000 pages.

### NFR-3: User Feedback
Progress indication should be shown during deletion process.
