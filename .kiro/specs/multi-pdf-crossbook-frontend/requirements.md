# Requirements: Multi-PDF Upload & Cross-Book Attribute Access - Frontend Implementation

## Overview

This spec covers the frontend implementation for Requirement 5, which adds:
1. Multi-PDF Upload UI - Allow uploading additional PDFs to existing books
2. Cross-Book Attribute Access UI - View audit logs for cross-book writes
3. Template Reference UI - Autocomplete for referencing book attributes in pipeline config

**Note:** Backend APIs are already implemented (`multi_pdf.py`, `cross_book.py`, `template_reference.py`). This spec focuses on frontend integration.

---

## User Stories

### US-1: Multi-PDF Upload
As a user, I want to upload additional PDF files to an existing book so that I can add more pages without creating a new book.

#### Acceptance Criteria
- 1.1 When viewing an existing book in the upload page, I see an "Upload Additional PDF" button
- 1.2 I can specify which PDF page to start counting from (skip cover pages)
- 1.3 I can specify the book page number to assign to the first counted PDF page
- 1.4 The system suggests a starting page based on existing pages
- 1.5 If pages overlap, I see a modal to choose which version to keep
- 1.6 I can apply the same choice to all overlapping pages with a checkbox

### US-2: Cross-Book Access Audit Log
As a user, I want to view a log of all cross-book attribute writes so that I can track which books modified other books' attributes.

#### Acceptance Criteria
- 2.1 I can access an audit log page from the navigation
- 2.2 I can filter the log by source book and/or target book
- 2.3 Each log entry shows: timestamp, source book, target book, attribute, old value, new value, operation type
- 2.4 The log is sorted by most recent first

### US-3: Template Reference Autocomplete
As a user, I want to reference attributes from other books in my pipeline templates using autocomplete so that I can easily build cross-book references.

#### Acceptance Criteria
- 3.1 When I type `@` in a template field, an autocomplete dropdown appears
- 3.2 I can type to filter results in the dropdown
- 3.3 I can click a "Browse All" button to open a full tree browser modal
- 3.4 The tree browser shows: Books > Levels (L1/L2) > Titles > Attributes
- 3.5 Clicking an attribute inserts the reference at cursor position
- 3.6 References are syntax highlighted with different colors for book, level, title, and attribute

---

## Technical Requirements

### TR-1: Reuse Existing Patterns
- Use existing modal patterns from `auto-slicer.html` (`.modal-overlay`, `.modal-content`)
- Use existing button styles (`.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`)
- Use existing form styles (`.form-group`, `.form-row`)
- Use existing table styles (`.page-status-table`)

### TR-2: API Integration
- Multi-PDF: Use existing endpoints in `/api/books/{book_id}/upload-pdf`, `/api/books/{book_id}/pdf-uploads`
- Cross-Book: Use existing endpoints in `/api/cross-book/audit-log`
- Template Reference: Use existing endpoints in `/api/template-reference/search`, `/api/template-reference/tree`

### TR-3: Files to Modify
- `upload.html` - Add multi-PDF upload section
- `pipeline-config.html` - Add template reference autocomplete
- Create new `cross-book-audit.html` - Audit log page
- `main.py` - Add route for audit log page (if not exists)

---

## Out of Scope
- Backend API changes (already implemented)
- Database schema changes (already migrated)
- Writable range UI in auto-slicer (already implemented)
