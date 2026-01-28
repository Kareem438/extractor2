# Tasks: Multi-PDF Upload & Cross-Book Attribute Access - Frontend Implementation

## Task List

- [x] 1. Multi-PDF Upload UI
  - [x] 1.1 Add "Upload Additional PDF" section to upload.html (visible when existing book selected)
  - [x] 1.2 Add PDF list display showing existing PDFs with page ranges
  - [x] 1.3 Add page mapping form (skip pages, starting book page)
  - [x] 1.4 Implement suggested start page auto-fill from API
  - [x] 1.5 Add overlap resolution modal with radio buttons and "apply to all" checkbox
  - [x] 1.6 Connect upload form to POST /api/books/{book_id}/upload-pdf endpoint
  - [x] 1.7 Handle overlap response and show resolution modal when needed

- [x] 2. Cross-Book Audit Log Page
  - [x] 2.1 Create cross-book-audit.html with navigation header
  - [x] 2.2 Add book filter dropdowns (source and target)
  - [x] 2.3 Add audit log table with columns: timestamp, source, target, attribute, values, operation
  - [x] 2.4 Implement loadAuditLog() function to fetch from /api/cross-book/audit-log
  - [x] 2.5 Add filter change handlers to reload data
  - [x] 2.6 Add route in main.py for /cross-book-audit page

- [x] 3. Template Reference Autocomplete
  - [x] 3.1 Add autocomplete dropdown component to pipeline-config.html
  - [x] 3.2 Implement @ trigger detection in textarea
  - [x] 3.3 Implement search-as-you-type with /api/template-reference/search
  - [x] 3.4 Add "Browse All" button that opens tree browser modal
  - [x] 3.5 Create tree browser modal with expandable book/level/title/attribute hierarchy
  - [x] 3.6 Implement click-to-insert for both dropdown and modal
  - [x] 3.7 Add syntax highlighting CSS for reference components (book=blue, level=purple, title=green, attr=orange)

- [x] 4. Navigation Updates
  - [x] 4.1 Add "Audit Log" link to relevant navigation menus
  - [x] 4.2 Update pipeline-config navigation to include new page

- [x] 5. Testing & Validation
  - [x] 5.1 Test multi-PDF upload with various page ranges
  - [x] 5.2 Test overlap resolution modal functionality
  - [x] 5.3 Test audit log filtering
  - [x] 5.4 Test template reference autocomplete and insertion
  - [x] 5.5 Test tree browser modal navigation and selection
