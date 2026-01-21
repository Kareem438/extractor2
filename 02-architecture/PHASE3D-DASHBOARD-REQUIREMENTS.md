# Phase 3D: Extraction Dashboard Requirements

**Feature:** Extraction Dashboard with Progress Tracking and Diagram Management
**Created:** 2026-01-18
**Status:** REQUIREMENTS COMPLETE - Ready for Implementation
**Prerequisites:** Phase 3B (Extract Knowledge Units) ~85% complete

---

## Overview

Phase 3D enhances the extraction workflow with a comprehensive dashboard that provides:
- Visual progress tracking for OCR and Claude decode operations
- Page thumbnail sidebar with region visualization
- Diagrams table with view/edit/re-decode actions
- API mode selection (Batch vs Direct)
- WebSocket live updates

---

## Detailed Requirements

### 3D.1 Dashboard Layout

**Structure:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: Book Name | API Mode Toggle | Start Extraction Button     │
├──────────────┬──────────────────────────────────────────────────────┤
│              │  Progress Section                                    │
│   Left       │  ┌─────────────────────────────────────────────────┐│
│   Sidebar    │  │ Paragraphs OCR:  [████████░░] 45/120 (37%)     ││
│              │  │ Diagrams Decode: [██████░░░░] 30/80  (38%)     ││
│   Page       │  └─────────────────────────────────────────────────┘│
│   Thumbnails │                                                      │
│   with       │  Summary Table (by L3 Title)                        │
│   Region     │  ┌──────────────────────────────────────────────────┐
│   Boxes      │  │ L3 Title | Para | Diag | Table | Eq | List      │
│              │  ├──────────────────────────────────────────────────┤
│   (vertical  │  │ Ch 1.1   |  12  |   5  |   2   |  1 |   3       │
│    scroll)   │  │ Ch 1.2   |   8  |   3  |   0   |  0 |   1       │
│              │  └──────────────────────────────────────────────────┘
│              │                                                      │
│              │  Diagrams Table                                      │
│              │  ┌──────────────────────────────────────────────────┐
│              │  │ Thumb | Class | Status | Actions                 │
│              │  ├──────────────────────────────────────────────────┤
│              │  │ [img] | diagram | decoded | View Edit Re-decode  │
│              │  │ [img] | table   | pending | View Edit Re-decode  │
│              │  └──────────────────────────────────────────────────┘
│              │  Pagination: [< Prev] Page 1 of 5 [Next >]          │
└──────────────┴──────────────────────────────────────────────────────┘
```

**Left Sidebar (Page Thumbnails):**
- Vertical column of page thumbnails
- Each thumbnail shows the page image with colored region boxes overlaid
- Region colors match class types (diagram=blue, table=green, etc.)
- Click thumbnail to navigate to that page in Layout Review
- Scrollable with page numbers

**Right Content Area:**
- Progress bars section (top)
- Summary table by L3 title (middle)
- Diagrams table with pagination (bottom)

---

### 3D.2 Progress Bars

**Visual Style:** Simple horizontal progress bars with numeric labels

**Paragraphs OCR Progress:**
```
Paragraphs OCR: [████████░░░░░░░░░░░░] 45/120 (37%)
```
- Numerator: Paragraphs with extracted_text populated
- Denominator: Total paragraphs in ready pages
- Percentage: (OCR'd / Total) × 100

**Diagrams Decode Progress:**
```
Diagrams Decode: [██████░░░░░░░░░░░░░░] 30/80 (38%)
```
- Numerator: Diagrams with extracted_text populated (Claude decoded)
- Denominator: Total diagrams/tables/equations/lists in ready pages
- Percentage: (Decoded / Total) × 100

**Update Mechanism:** WebSocket live updates (no polling)

---

### 3D.3 Summary Table

**Columns:**
| Column | Description |
|--------|-------------|
| L3 Title | Title from L3 region (or "Untitled" if none) |
| Paragraphs | Count of paragraph regions |
| Diagrams | Count of diagram regions |
| Tables | Count of table regions |
| Equations | Count of equation regions |
| Lists | Count of list regions (bulleted + numbered + lettered) |
| Questions | Count of question regions |
| Answers | Count of answer regions |

**Data Source:** All ready pages (pages marked "Ready for Extraction")

**Features:**
- Click L3 title row to filter diagrams table to that section
- Totals row at bottom

---

### 3D.4 Diagrams Table

**Columns:**
| Column | Width | Content |
|--------|-------|---------|
| Thumbnail | 60px | Cropped diagram image (small preview) |
| Class | 80px | diagram, table, equation, list_bulleted, etc. |
| Status | 80px | pending, processing, decoded, failed |
| Actions | 150px | View, Edit, Re-decode buttons |

**Pagination:**
- Variable page size (user-configurable: 10, 25, 50, 100)
- Standard pagination controls: Prev, Next, page number input

**Status Colors:**
- `pending` - Gray
- `processing` - Yellow/Orange (pulsing)
- `decoded` - Green
- `failed` - Red

---

### 3D.5 Actions

**View Button:**
- Opens modal showing:
  - Full-size diagram image
  - Extracted text (Claude response)
  - Parent paragraph text (if linked)
  - Page number and class type

**Edit Button:**
- Opens modal with:
  - Extracted text in editable textarea
  - Save and Cancel buttons
  - Saves to extracted_text column

**Re-decode Button:**
- Opens modal with:
  - Diagram image preview
  - Current prompt (from book settings for this class)
  - Editable prompt textarea
  - "Re-decode" button to execute
  - Progress indicator during processing
  - Result displayed in modal after completion
  - "Save" to persist, "Cancel" to discard

---

### 3D.6 API Mode Selection

**Location:** Header area, before "Start Extraction" button

**Options:**
| Mode | Description |
|------|-------------|
| Batch API | 50% cost, async processing, poll for results |
| Direct API | Full cost, immediate results |

**UI Element:** Toggle switch or dropdown

**Default:** Batch API (recommended)

---

### 3D.7 Extraction Trigger

**Button:** "Start Extraction" (or similar)

**Workflow:**
1. Validate all ready pages have no orphan diagrams
2. For each ready page:
   - Run Surya OCR at 600 DPI for paragraphs
   - Crop diagram/table/equation/list images
   - Save to database
3. For diagrams (based on API mode):
   - **Batch API:** Submit batch request, poll for results
   - **Direct API:** Process each diagram sequentially
4. Execute class-specific prompts from book settings:
   - `extraction_prompts.diagram` for diagrams
   - `extraction_prompts.table` for tables
   - `extraction_prompts.equation` for equations
   - `extraction_prompts.list_bulleted` for bulleted lists
   - etc.
5. Store Claude response in `extracted_text` column
6. Update progress via WebSocket

**Note:** Paragraphs get OCR text only, no Claude processing.

---

### 3D.8 WebSocket Integration

**Endpoint:** `/ws/extraction/{book_id}` (new or reuse existing)

**Message Types:**
```json
// Progress update
{
  "type": "progress",
  "data": {
    "paragraphs_ocr": {"completed": 45, "total": 120},
    "diagrams_decode": {"completed": 30, "total": 80},
    "current_page": 12,
    "current_diagram_id": 456
  }
}

// Status change
{
  "type": "status_change",
  "data": {
    "diagram_id": 456,
    "old_status": "processing",
    "new_status": "decoded"
  }
}

// Completion
{
  "type": "completed",
  "data": {
    "paragraphs_ocr": 120,
    "diagrams_decoded": 78,
    "diagrams_failed": 2,
    "duration_seconds": 180
  }
}

// Error
{
  "type": "error",
  "data": {
    "message": "Rate limit exceeded",
    "diagram_id": 456
  }
}
```

---

### 3D.9 Re-decode Modal

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Re-decode Diagram                                         [X]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐  Prompt:                              │
│  │                      │  ┌────────────────────────────────┐   │
│  │   Diagram Image      │  │ Analyze this diagram and       │   │
│  │   (preview)          │  │ provide a detailed             │   │
│  │                      │  │ description...                 │   │
│  │                      │  │                                │   │
│  └──────────────────────┘  └────────────────────────────────┘   │
│                                                                  │
│  Parent Paragraph:                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ "The following diagram illustrates the data flow..."     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [ Reset to Default ]           [ Cancel ]  [ Re-decode ]       │
├─────────────────────────────────────────────────────────────────┤
│  Result:                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ (Claude response appears here after re-decode)           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│                                 [ Discard ]  [ Save Result ]    │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Shows diagram image preview
- Editable prompt textarea (pre-filled with class prompt from book settings)
- Parent paragraph context (read-only)
- "Reset to Default" button to restore original prompt
- "Re-decode" button triggers Claude API call
- Progress indicator during processing
- Result section appears after completion
- "Save Result" persists to extracted_text, "Discard" closes modal

---

## API Endpoints

### New Endpoints Required

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extraction/{book_id}/dashboard` | GET | Get dashboard data (progress, summary, diagrams list) |
| `/api/extraction/{book_id}/start` | POST | Start extraction (with API mode parameter) |
| `/api/extraction/{book_id}/diagram/{id}/view` | GET | Get diagram details for view modal |
| `/api/extraction/{book_id}/diagram/{id}/edit` | PUT | Update diagram extracted_text |
| `/api/extraction/{book_id}/diagram/{id}/redecode` | POST | Re-decode single diagram with custom prompt |
| `/ws/extraction/{book_id}` | WebSocket | Live progress updates |

### Existing Endpoints to Reuse

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extraction/{book_id}/ready-pages` | GET | Get pages ready for extraction |
| `/api/extraction/{book_id}/summary` | GET | Summary by L3 title |
| `/api/extraction/{book_id}/extract` | POST | Extract paragraphs/diagrams |
| `/api/extraction/{book_id}/decode-batch` | POST | Submit batch decode |
| `/api/extraction/{book_id}/decode-direct` | POST | Direct decode |

---

## Database Changes

### No Schema Changes Required

All data stored in existing columns:
- `raw_{prefix}_paragraph_images.extracted_text` - Surya OCR text
- `raw_{prefix}_diagram_images.extracted_text` - Claude decode result

---

## UI Components

### New Components

| Component | Description |
|-----------|-------------|
| `ExtractionDashboard` | Main dashboard container |
| `PageThumbnailSidebar` | Left sidebar with page thumbnails |
| `ProgressBars` | OCR and Decode progress bars |
| `SummaryTable` | Counts by L3 title |
| `DiagramsTable` | Paginated diagrams table with actions |
| `ViewModal` | View diagram details |
| `EditModal` | Edit extracted text |
| `RedecodeModal` | Re-decode with prompt editor |

### Styling

- Use existing dark theme from Layout Review page
- Consistent with Auto-Slicer styling
- Responsive layout (sidebar collapses on mobile)

---

## Implementation Priority

| Priority | Task | Description |
|----------|------|-------------|
| 1 | Dashboard layout | Basic structure with sidebar + content area |
| 2 | Progress bars | OCR and Decode progress with WebSocket |
| 3 | Summary table | Counts by L3 title (all region types) |
| 4 | Diagrams table | Paginated table with thumbnails |
| 5 | View modal | View diagram details |
| 6 | Edit modal | Edit extracted text |
| 7 | Re-decode modal | Re-decode with prompt editor |
| 8 | API mode toggle | Batch vs Direct selection |
| 9 | Start extraction | Trigger extraction workflow |
| 10 | WebSocket integration | Live updates |

---

## Test Plan

**Test Book:** Book ID 1

**Test Scenarios:**
1. Load dashboard - verify layout renders correctly
2. Start extraction with Batch API - verify progress updates
3. Start extraction with Direct API - verify immediate results
4. View diagram - verify modal shows correct data
5. Edit diagram - verify save works
6. Re-decode diagram - verify prompt editor and result
7. Summary table - verify counts are accurate
8. Pagination - verify page navigation works
9. WebSocket - verify live updates without refresh
10. Error handling - verify failed decodes show error state

---

## References

- Phase 3B Progress: `02-architecture/PHASE3-EXTRACTION-PROGRESS.md`
- Phase 3B Requirements: `02-architecture/PHASE3-EXTRACTION-URGENT.md`
- Auto-Boundaries Progress: `02-architecture/AUTO-BOUNDARIES-PROGRESS.md`
- Existing extraction code: `03-code/src/services/extraction_service.py`
- Existing batch service: `03-code/src/services/claude_batch_service.py`
