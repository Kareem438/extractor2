# Design: Multi-PDF Upload & Cross-Book Attribute Access - Frontend Implementation

## Architecture Overview

This design leverages existing UI patterns and components from the codebase to implement the frontend for Requirement 5.

---

## Component Design

### 1. Multi-PDF Upload UI (upload.html)

#### Location
Add to `03-code/src/frontend/templates/upload.html` in the "Select Existing Book" section.

#### UI Elements
```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Select Existing Book                                      │
├─────────────────────────────────────────────────────────────┤
│ [Book List - existing]                                       │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📄 Upload Additional PDF (visible when book selected)   │ │
│ │                                                         │ │
│ │ Current PDFs: [list of existing PDFs with page ranges]  │ │
│ │                                                         │ │
│ │ [Choose PDF File]                                       │ │
│ │                                                         │ │
│ │ Skip first [___] pages of PDF (default: 0)              │ │
│ │ Starting book page: [___] (suggested: auto-calculated)  │ │
│ │                                                         │ │
│ │ [Upload Additional PDF]                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Overlap Resolution Modal
Reuse `.modal-overlay` pattern from auto-slicer.html:
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Page Overlap Detected                              [X]   │
├─────────────────────────────────────────────────────────────┤
│ The following pages already exist. Choose which to keep:    │
│                                                              │
│ Page 88:  ○ Keep existing (book_part1.pdf)                  │
│           ● Use new (book_part2.pdf)                        │
│                                                              │
│ Page 89:  ● Keep existing (book_part1.pdf)                  │
│           ○ Use new (book_part2.pdf)                        │
│                                                              │
│ ☑ Apply same choice to all remaining pages                  │
│                                                              │
│                              [Cancel] [Resolve Overlaps]    │
└─────────────────────────────────────────────────────────────┘
```

### 2. Cross-Book Audit Log Page (cross-book-audit.html)

#### New Page
Create `03-code/src/frontend/templates/cross-book-audit.html`

#### UI Layout
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Cross-Book Access Audit Log                              │
├─────────────────────────────────────────────────────────────┤
│ Filters:                                                     │
│ Source Book: [All Books ▼]  Target Book: [All Books ▼]      │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Timestamp    │ Source │ Target │ Attr │ Old→New │ Op   │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ 2026-01-26   │ BookB  │ BookA  │ 155  │ null→5  │ write│ │
│ │ 10:30:00     │        │ L1:Ch1 │      │         │      │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ 2026-01-26   │ BookC  │ BookA  │ 160  │ 5→6     │ incr │ │
│ │ 10:25:00     │        │ L1:Ch2 │      │         │      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 3. Template Reference Autocomplete (pipeline-config.html)

#### Location
Modify `03-code/src/frontend/templates/pipeline-config.html` to add autocomplete to prompt template textarea.

#### Autocomplete Dropdown
```
┌─────────────────────────────────────────────────────────────┐
│ Prompt Template:                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Analyze this text: {{text_content}}                     │ │
│ │ Reference value: @|                                     │ │
│ │                   ┌───────────────────────────────────┐ │ │
│ │                   │ 🔍 Type to search...              │ │ │
│ │                   ├───────────────────────────────────┤ │ │
│ │                   │ @Physics101.L1.Energy.attr22(Lvl) │ │ │
│ │                   │ @Physics101.L1.Energy.attr23      │ │ │
│ │                   │ @Math200.L2.Calc.attr10(Type)     │ │ │
│ │                   ├───────────────────────────────────┤ │ │
│ │                   │ [Browse All...]                   │ │ │
│ │                   └───────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Tree Browser Modal
```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Browse Attribute References                        [X]   │
├─────────────────────────────────────────────────────────────┤
│ 🔍 [Search attributes...]                                   │
│                                                              │
│ ▼ Physics 101                                               │
│   ▼ L1 Titles                                               │
│     ▼ Energy Chapter (pp. 1-50)                             │
│       • attr1 - Type                                        │
│       • attr22 - EnergyLevel ✏️ (writable)                  │
│       • attr23 ✏️ (writable)                                │
│     ▶ Motion Chapter (pp. 51-100)                           │
│   ▶ L2 Titles                                               │
│ ▶ Math 200                                                  │
│                                                              │
│                                              [Cancel]       │
└─────────────────────────────────────────────────────────────┘
```

#### Syntax Highlighting Colors
- Book name: `#3498db` (blue)
- Level (L1/L2): `#9b59b6` (purple)
- Title name: `#27ae60` (green)
- Attribute: `#e67e22` (orange)

---

## Implementation Details

### CSS Classes to Reuse

From `auto-slicer.html`:
- `.modal-overlay` - Modal backdrop
- `.modal-content` - Modal container
- `.modal-header` - Modal title bar
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger` - Buttons
- `.form-group`, `.form-row` - Form layouts

From `pipeline-dashboard.html`:
- `.page-status-table` - Table styling
- `.alert`, `.alert-success`, `.alert-error` - Alerts

### JavaScript Patterns to Follow

1. **Modal Management** (from auto-slicer.js):
```javascript
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}
```

2. **API Calls** (from pipeline-config.html):
```javascript
async function fetchData(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch');
    return await response.json();
}
```

3. **Book Selection** (from pipeline-dashboard.html):
```javascript
async function loadBooks() {
    const response = await fetch('/api/books');
    const data = await response.json();
    // Populate select dropdown
}
```

---

## API Endpoints Used

### Multi-PDF Upload
- `GET /api/books/{book_id}/pdf-uploads` - List existing PDFs
- `GET /api/books/{book_id}/suggested-start-page` - Get suggested start page
- `POST /api/books/{book_id}/upload-pdf` - Upload new PDF
- `POST /api/books/{book_id}/resolve-overlaps` - Resolve page conflicts

### Cross-Book Audit
- `GET /api/cross-book/audit-log?source_book_id=X&target_book_id=Y&limit=100`

### Template Reference
- `GET /api/template-reference/search?query=X&limit=20` - Autocomplete search
- `GET /api/template-reference/tree` - Full tree for modal browser

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `upload.html` | Modify | Add multi-PDF upload section |
| `pipeline-config.html` | Modify | Add template reference autocomplete |
| `cross-book-audit.html` | Create | New audit log page |
| `main.py` | Modify | Add route for audit log page |

---

## Correctness Properties

### P1: Multi-PDF Upload Validation
- Uploaded PDF must be valid (parseable by PyMuPDF)
- Page mapping must be consistent (no negative pages)
- Overlap resolution must handle all conflicting pages

### P2: Audit Log Accuracy
- All displayed logs must match database records
- Filters must correctly narrow results
- Timestamps must be in user's local timezone

### P3: Template Reference Syntax
- Generated references must follow format: `@BookName.Level.TitleName.attrN(Name)`
- Inserted references must be valid and resolvable
- Autocomplete must only show existing books/titles/attributes
