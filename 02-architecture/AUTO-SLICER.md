# Auto-Slicer Feature Specification

## Current Understanding Level: ~95% ✓

**Status:** IMPLEMENTATION COMPLETE - Ready for testing

**Last Updated:** 2026-01-12

**Progress Tracking:** See `02-architecture/AUTO-SLICER-PROGRESS.md` for detailed implementation status.

**Access:** http://localhost:7777/book-settings -> Red "Open Auto-Slicer" button

---

## Overview
The Auto-slicer is a new feature that automatically processes an entire book (or specified page range), applying Surya OCR at 600 DPI to each page and storing the results as paragraphs. This enables bulk processing of books for pipeline execution.

## Access Point
- **Location**: Big red button in the Book Settings page labeled "Auto-slicer"
- **Navigation**: Book Settings page -> Click "Open Auto-slicer" button -> Opens dedicated Auto-slicer page
- **Prerequisite**: Book PDF must be uploaded first

## Core Functionality

### 1. Page Processing
- **Page Range**: User specifies start page and end page to process
- **OCR Engine**: Surya OCR at 600 DPI applied to each page
- **Storage**: Each page's OCR result stored as a paragraph
- **Page Number Storage**: Custom attribute 30 (attr30) stores the page number
- **Source Marking**: Custom attribute 29 (attr29) stores 'auto-slicer' to identify source
- **Existing Data**: New paragraphs are added alongside existing paragraphs (no replacement)

### 2. Title Configuration (3 Levels)
- **Levels**: Up to 3 hierarchical levels of titles
- **Multiple Titles Per Level**: Each level can have multiple titles
- **Title Structure**: Each title has:
  - Title text
  - Start page number
  - End page number
- **Storage**: Uses existing columns: level_1_title, level_2_title, level_3_title
- **Overlap Handling**: Allow overlapping page ranges with warning message
- **UI Pattern**: Add/Remove rows dynamically (+ button to add, delete button per row)

### 3. OCR Boundary Configuration
- **Purpose**: Define scan region to exclude headers/footers
- **Selection Method**: Visual rectangle selection on page preview
- **Preview**: Page scaled to fit window with zoom option available
- **Multiple Boundaries**: Different boundaries per page range (start page to end page)
- **Default**: If no boundary defined, scan entire page

### 4. Configuration Storage
- **Location**: New JSON columns in books_metadata table
- **Column Name**: `auto_slicer_config`
- **Persistence**: Saved per book, loaded when user returns

## UI Components

### Auto-slicer Page Layout
1. **Page Range Section**
   - Start page input
   - End page input

2. **Title Configuration Section**
   - Level 1 titles (dynamic rows: title, start page, end page, delete)
   - Level 2 titles (dynamic rows)
   - Level 3 titles (dynamic rows)
   - "+" button to add new title row per level

3. **OCR Boundary Section**
   - List of configured boundaries (page range + coordinates)
   - "Add Boundary" button opens page preview modal
   - Page number input for preview
   - Visual rectangle drawing on page image
   - Zoom controls for preview

4. **Action Section**
   - Big red "Auto-slicer" button
   - Button disabled until: page range specified AND at least one title configured

5. **Progress Section** (shown during execution)
   - Progress bar
   - Page counter: "Processing page X of Y"
   - Real-time updates

6. **Results Section** (shown after completion)
   - Summary: X pages processed, Y paragraphs created
   - Failed pages report with thumbnails
   - "Retry Failed Pages" button

## Execution Flow

1. User configures page range, titles, and optional OCR boundaries
2. User clicks "Auto-slicer" button
3. System validates configuration
4. For each page in range:
   a. Load page image
   b. Apply OCR boundary if configured for this page range
   c. Run Surya OCR at 600 DPI
   d. Determine applicable titles based on page number
   e. Create paragraph_image record
   f. Create knowledge_unit record with titles and OCR text
   g. Update progress bar
5. On completion: Show summary, stay on page
6. Failed pages: Skip and continue, show in report with thumbnails, allow retry

## Error Handling
- **Failed OCR**: Skip page, log error, continue processing
- **Failed Pages Report**: Show thumbnails of failed pages
- **Retry Capability**: Button to retry all failed pages

## Data Created Per Page

### raw_*_paragraph_images table
- page_number
- image_data (full page or bounded region)
- extracted_text (OCR result)
- is_enabled = TRUE
- created_by = 'auto-slicer'

### *_knowledge_units table
- page_number
- text_content (OCR result)
- level_1_title (from title config)
- level_2_title (from title config)
- level_3_title (from title config)
- attr29_value = 'auto-slicer'
- attr30_value = page_number (as string)

## Database Changes Required

### books_metadata table
Add column:
```sql
ALTER TABLE books_metadata ADD COLUMN auto_slicer_config JSONB;
```

### Config JSON Structure
```json
{
  "page_range": {
    "start": 1,
    "end": 100
  },
  "titles": {
    "level1": [
      {"title": "Introduction", "start_page": 1, "end_page": 10},
      {"title": "Chapter 1", "start_page": 11, "end_page": 50}
    ],
    "level2": [...],
    "level3": [...]
  },
  "batches": [
    {"start_page": 1, "end_page": 50},
    {"start_page": 51, "end_page": 100}
  ],
  "ocr_boundaries": [
    {
      "start_page": 1,
      "end_page": 100,
      "rectangles": [
        {
          "label": "Main Text",
          "x": 50,
          "y": 100,
          "width": 700,
          "height": 900,
          "target": "text_content"
        },
        {
          "label": "Sidebar Notes",
          "x": 760,
          "y": 100,
          "width": 200,
          "height": 900,
          "target": "attr31"
        }
      ]
    }
  ],
  "execution_state": {
    "status": "paused",
    "last_completed_page": 45,
    "current_batch_index": 0,
    "started_at": "2024-01-12T10:30:00Z",
    "paused_at": "2024-01-12T10:35:00Z"
  },
  "last_run": {
    "timestamp": "2024-01-12T10:30:00Z",
    "pages_processed": 95,
    "pages_failed": 5,
    "failed_pages": [12, 45, 67, 89, 92]
  }
}
```

## Questions and Answers Summary

| Question | Answer |
|----------|--------|
| OCR boundary scope | Different boundaries per page range |
| Title overlap handling | Allow overlap with warning |
| Page processing range | User specifies start/end pages |
| Title config UI location | On the same Auto-slicer page |
| Title storage columns | level_1_title, level_2_title, level_3_title |
| Boundary input method | Visual rectangle selection |
| Progress display | Progress bar with page counter |
| Existing paragraphs | Add alongside existing (no replacement) |
| Boundary page assignment | Start page to end page range |
| Button enable condition | Require page range AND at least one title |
| Config persistence | Save to database per book |
| Title UI pattern | Add/Remove rows dynamically |
| Config storage location | New columns in books_metadata table |
| Paragraph source marking | Mark in attr29='auto-slicer' |
| Navigation to Auto-slicer | Big button in Book Settings page |
| Preview image size | Scaled to fit with zoom option |
| Error handling | Skip failed, continue, show report with retry |
| Completion action | Show summary and stay on page |
| Knowledge unit creation | Yes, create both paragraph_image and knowledge_unit |
| Default OCR boundary | Scan entire page |
| Progress updates | WebSocket real-time |
| Cancel/Pause | Both supported, progress saved to DB |
| Pipeline integration | Separate (Auto-slicer creates data, pipeline processes later) |
| Large books batching | Optional user-defined batches (start page + end page rows) |
| Concurrency | One book at a time |
| Multiple rectangles | Yes, all visible on same preview |
| Rectangle labels | User names each rectangle |
| Default rectangle | Stores to text_content |
| Additional rectangles | User selects target attribute (attr31-80 only) |
| Reserved attributes | attr1-30 (all reserved for other features) |
| Batch config | Optional (no batches = process all at once) |
| Pause state | Save progress to database (survives restarts) |

## Advanced Features

### 5. WebSocket Progress Updates
- Real-time progress pushed to browser via WebSocket
- Connection endpoint: `/ws/auto-slicer/{book_id}`
- Messages include: current page, total pages, status, errors

### 6. Cancel and Pause Functionality
- **Cancel Button**: Stops processing immediately, keeps completed work
- **Pause Button**: Pauses processing, saves state to database
- **Resume**: Can resume from last completed page even after browser/server restart
- Progress state stored in `auto_slicer_config.execution_state`

### 7. Batch Processing (Optional)
- User can define custom batches with dynamic rows
- Each batch row contains: Start Page, End Page
- If no batches defined, all pages processed in one go
- Brief pause between batches to prevent resource exhaustion
- UI: "Add Batch" button, delete button per row

### 8. Multiple OCR Rectangles
- **Default Rectangle**: First rectangle stores OCR to `text_content` (like manual scanning)
- **Additional Rectangles**: User specifies target custom attribute (attr31-80 only)
- **Labels**: User names each rectangle (e.g., "Main Text", "Sidebar", "Footer Note")
- **Drawing UI**: All rectangles visible simultaneously on page preview
- **Reserved Attributes**: attr1-30 are reserved for system use, not selectable

### 9. Concurrency Control
- Only one Auto-slicer job can run at a time (across all books)
- If user tries to start another, show warning message
- Current job status visible on Book Settings page

## Implementation Tasks

1. **Database Migration**
   - Add auto_slicer_config column to books_metadata

2. **Backend API Endpoints**
   - GET /api/auto-slicer/{book_id}/config - Get saved config
   - POST /api/auto-slicer/{book_id}/config - Save config
   - POST /api/auto-slicer/{book_id}/run - Execute auto-slicer
   - GET /api/auto-slicer/{book_id}/status - Get execution status
   - POST /api/auto-slicer/{book_id}/retry - Retry failed pages

3. **Frontend Pages**
   - auto-slicer.html - Main Auto-slicer page
   - auto-slicer.js - JavaScript for the page
   - Update book-settings.html - Add "Open Auto-slicer" button

4. **Services**
   - Auto-slicer service for processing logic
   - Integration with existing Surya OCR service

## Related Files
- `03-code/src/frontend/templates/auto-slicer.html` (new)
- `03-code/src/frontend/static/js/auto-slicer.js` (new)
- `03-code/src/api/routes/auto_slicer.py` (new)
- `03-code/src/services/auto_slicer_service.py` (new)
- `03-code/src/frontend/templates/book-settings.html` (update)
- `03-code/migrate_add_auto_slicer.py` (new)
