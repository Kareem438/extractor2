# Tasks: Safe Book Deletion Feature

## Task List

- [x] 1. Backend API Implementation
  - [x] 1.1 Create `03-code/src/api/routes/delete_book.py` with deletion preview endpoint
  - [x] 1.2 Add DELETE endpoint with confirmation code validation
  - [x] 1.3 Implement `get_book_counts()` function to count entities
  - [x] 1.4 Implement `drop_book_tables()` function to drop all book tables
  - [x] 1.5 Register delete_book router in `main.py`

- [x] 2. ChromaDB Service Updates
  - [x] 2.1 Add `delete_by_book_id()` method to chroma_service.py
  - [x] 2.2 Add `count_by_book_id()` method to chroma_service.py

- [x] 3. Library Page - Delete Button
  - [x] 3.1 Add Delete button to Actions column in `createBookRow()` function
  - [x] 3.2 Disable button for books with processing status
  - [x] 3.3 Add tooltip for disabled state

- [x] 4. Delete Confirmation Modals (Library)
  - [x] 4.1 Add Step 1 Summary Modal HTML to library.html
  - [x] 4.2 Add Step 2 Code Verification Modal HTML to library.html
  - [x] 4.3 Add modal CSS styles to library.html
  - [x] 4.4 Add toast notification CSS to library.html

- [x] 5. Library JavaScript Functions
  - [x] 5.1 Add `initiateDeleteBook()` function to fetch deletion preview
  - [x] 5.2 Add `showDeleteSummaryModal()` function
  - [x] 5.3 Add `showCodeVerification()` function
  - [x] 5.4 Add `validateConfirmationCode()` function
  - [x] 5.5 Add `executeDelete()` function to call DELETE API
  - [x] 5.6 Add `closeDeleteModals()` function
  - [x] 5.7 Add `showToast()` function for notifications

- [x] 6. Book Settings - PDF Path Display
  - [x] 6.1 Add PDF path display element under book name in book-settings.html
  - [x] 6.2 Add CSS for pdf-path-display
  - [x] 6.3 Update book-settings.js to populate file path from API

- [x] 7. Book Settings - Danger Zone Section
  - [x] 7.1 Add Danger Zone section HTML at bottom of book-settings.html
  - [x] 7.2 Add Danger Zone CSS styles
  - [x] 7.3 Add Delete button with disabled state handling

- [x] 8. Book Settings - Delete Modals
  - [x] 8.1 Add delete modals HTML to book-settings.html (reuse from library)
  - [x] 8.2 Add delete modal JavaScript functions to book-settings.js
  - [x] 8.3 Handle redirect to Library after successful deletion

- [ ] 9. Testing & Validation
  - [ ] 9.1 Test deletion preview API returns correct counts
  - [ ] 9.2 Test deletion blocked for books with active tasks
  - [ ] 9.3 Test confirmation code validation
  - [ ] 9.4 Test all tables are dropped correctly
  - [ ] 9.5 Test ChromaDB deletion when checkbox checked
  - [ ] 9.6 Test ChromaDB preserved when checkbox unchecked
  - [ ] 9.7 Test PDF file preserved on disk after deletion
  - [ ] 9.8 Test toast notification appears after deletion
  - [ ] 9.9 Test book list refreshes after deletion (Library)
  - [ ] 9.10 Test redirect to Library after deletion (Book Settings)
