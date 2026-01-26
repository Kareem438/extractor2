# Requirement 5: Multi-PDF Upload & Cross-Book Attribute Access

**Created:** January 26, 2026  
**Status:** Requirements Gathering  
**Priority:** High  
**Last Updated:** January 26, 2026

---

## 1. Overview

This requirement introduces two major features:
1. **Multi-PDF Upload**: Allow multiple PDF files to be uploaded for the same book (e.g., file 1 covers pages 1-200, file 2 covers pages 201-400)
2. **Cross-Book Attribute Access**: Allow books to read/write custom attributes of L1/L2 titles from other books
3. **Template Reference UI**: Enhanced pipeline-config UI with autocomplete for referencing book attributes

---

## 2. Clarification Questions & Answers

### Batch 1: Multi-PDF Upload

**Q1. When uploading a second PDF for the same book, should the system:**
- a) Automatically detect the page range based on existing pages
- b) Require user to specify the starting page number
- c) Allow both options (auto-detect with manual override)
- d) Other approach

**Answer:** _[PENDING]_

**Q2. If there's a page overlap between PDFs (e.g., PDF1 has pages 1-200, PDF2 has pages 195-400), should the system:**
- a) Reject the upload with an error
- b) Overwrite the overlapping pages with the new PDF
- c) Keep the original pages and skip duplicates
- d) Ask the user which version to keep
- e) Other approach

**Answer:** _[PENDING]_

---

### Batch 2: Cross-Book Attribute Access

**Q3. For cross-book attribute access, should the "last 50 attributes" rule apply to:**
- a) Attributes 151-200 for L1 (total 200) and 101-150 for L2 (total 150)
- b) A configurable range that can be set per book
- c) A fixed range that's the same for all books
- d) Other approach

**Answer:** _[PENDING]_

**Q4. When Book B writes to Book A's attributes, should there be:**
- a) No audit trail (just overwrite)
- b) A simple log of who wrote what and when
- c) Full version history with ability to revert
- d) Other approach

**Answer:** _[PENDING]_

---

### Batch 3: Template Reference UI

**Q5. For the template reference syntax (e.g., `$$book1.L1.ChapterName.attribute22`), should the trigger be:**
- a) `$$` (double dollar sign)
- b) `{{` (double curly braces)
- c) `@` (at sign)
- d) `#` (hash)
- e) Other symbol you prefer

**Answer:** _[PENDING]_

**Q6. When the user types the trigger symbol, should the autocomplete:**
- a) Show a hierarchical dropdown (Book → Level → Title → Attribute)
- b) Show a flat searchable list with all options
- c) Show a modal dialog with a tree view
- d) Other approach

**Answer:** _[PENDING]_

---

### Batch 4: Additional Clarifications

**Q7. For multi-PDF upload, should the system support:**
- a) Only sequential page ranges (no gaps)
- b) Any page ranges (gaps allowed)
- c) Overlapping ranges with merge strategy
- d) Other approach

**Answer:** _[PENDING]_

**Q8. For cross-book access, should there be a permission system:**
- a) All books can access all other books by default
- b) Explicit permission must be granted per book pair
- c) Books in the same "project" can access each other
- d) Other approach

**Answer:** _[PENDING]_

---

### Batch 5: UI/UX Details

**Q9. In the template editor, when a reference is inserted, should it:**
- a) Show the full path (e.g., `$$Book1.L1.Chapter1.attr22`)
- b) Show a shortened version with tooltip (e.g., `$$[Book1.attr22]`)
- c) Show a visual chip/tag that can be clicked to edit
- d) Other approach

**Answer:** _[PENDING]_

**Q10. For the attribute reference, should the syntax use:**
- a) Attribute number (e.g., `attr22`)
- b) Attribute name if defined (e.g., `EnergyLevel`)
- c) Both options (name preferred, number as fallback)
- d) Other approach

**Answer:** _[PENDING]_

---

## 3. Feature Details (To be filled after Q&A)

### 3.1 Multi-PDF Upload
_[Details to be added after clarification]_

### 3.2 Cross-Book Attribute Access
_[Details to be added after clarification]_

### 3.3 Template Reference UI
_[Details to be added after clarification]_

---

## 4. Database Schema Changes (To be designed)

_[To be added after requirements are clarified]_

---

## 5. API Endpoints (To be designed)

_[To be added after requirements are clarified]_

---

## 6. UI Changes (To be designed)

_[To be added after requirements are clarified]_

---

## 7. Dependencies

- Existing upload system (`03-code/src/api/routes/upload.py`)
- Existing books management (`03-code/src/api/routes/books.py`)
- Existing title hierarchy system (`03-code/src/api/routes/title_hierarchy.py`)
- Existing pipeline configuration (`03-code/src/frontend/templates/pipeline-dashboard.html`)
- Existing KU creation service (`03-code/src/services/ku_creation_service.py`)

---

## 8. Out of Scope

_[To be defined after requirements are clarified]_
