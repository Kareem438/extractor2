# API Design - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Framework:** FastAPI
**Base URL:** http://localhost:8000
**Status:** ✅ API Design Complete

---

## 📋 Overview

RESTful API with WebSocket support for real-time updates. Single-user local deployment (no authentication required).

**API Style:** REST
**Data Format:** JSON
**Authentication:** None (localhost only)
**CORS:** Restricted to localhost

---

## 🌐 HTTP Endpoints

### 1. Static Pages (HTML Serving)

#### GET /
**Description:** Serve upload page (main entry point)
**Response:** HTML page

#### GET /dashboard
**Description:** Serve processing dashboard
**Response:** HTML page

#### GET /verify/{book_id}
**Description:** Serve verification interface
**Parameters:**
- `book_id` (path, integer): Book ID
**Response:** HTML page

#### GET /library
**Description:** Serve book library dashboard
**Response:** HTML page

#### GET /book-settings/{book_id}
**Description:** Serve book settings page
**Parameters:**
- `book_id` (path, integer): Book ID
**Response:** HTML page

---

### 2. Book Management

#### POST /api/upload
**Description:** Upload file and create book metadata
**Content-Type:** multipart/form-data

**Request Body:**
```json
{
  "file": "binary",  // File upload
  "book_name": "Machine Learning Fundamentals.pdf",
  "language_setting": "auto",  // auto, english, arabic, both
  "extraction_sensitivity": "balanced",  // conservative, balanced, aggressive
  "image_processing": "all",  // all, diagrams_only, skip
  "ocr_quality": "balanced",  // fast, balanced, high
  "hierarchy_detection": "auto",  // auto, manual, skip
  "partial_processing_enabled": false,
  "partial_processing_pages": null,
  "special_instructions": "",
  "attribute_keys": {  // Attributes 9-40 key names (1-8 are system-reserved)
    "9": "Difficulty Level",
    "10": "Topic Category",
    "11": "Importance",
    "12": "Keywords",
    // ... up to 40 (32 user-defined attributes)
  }
}
```

**Response (201 Created):**
```json
{
  "book_id": 1,
  "book_name": "Machine Learning Fundamentals.pdf",
  "sanitized_name": "ml_fundamentals",
  "table_prefix": "book1_ml_fundamentals",
  "file_size_bytes": 52428800,
  "total_pages": 450,
  "upload_date": "2025-11-03T10:30:00Z",
  "processing_status": "uploaded",
  "message": "Book uploaded successfully. Click 'Start Processing' to begin."
}
```

**Errors:**
- 400: Invalid file type or size > 500MB
- 413: File too large
- 500: Server error

---

#### POST /api/start-processing
**Description:** Start processing a book
**Request Body:**
```json
{
  "book_id": 1
}
```

**Response (200 OK):**
```json
{
  "book_id": 1,
  "processing_status": "processing",
  "message": "Processing started. Monitor progress on dashboard.",
  "websocket_url": "ws://localhost:8000/ws/processing/1"
}
```

**Errors:**
- 404: Book not found
- 409: Book already processing
- 500: Processing start failed

---

#### POST /api/pause/{book_id}
**Description:** Pause processing
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "processing_status": "paused",
  "current_page": 45,
  "message": "Processing paused. You can safely shut down the system."
}
```

---

#### POST /api/resume/{book_id}
**Description:** Resume processing
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "processing_status": "processing",
  "current_page": 45,
  "message": "Processing resumed from page 45."
}
```

---

#### GET /api/books
**Description:** List all books
**Query Parameters:**
- `status` (optional): Filter by status (uploaded, processing, paused, completed, error)
- `language` (optional): Filter by language (english, arabic, mixed)
- `limit` (optional, default 20): Number of results
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**
```json
{
  "total": 10,
  "limit": 20,
  "offset": 0,
  "books": [
    {
      "book_id": 1,
      "book_name": "Machine Learning Fundamentals.pdf",
      "file_type": "PDF",
      "total_pages": 450,
      "processing_status": "processing",
      "current_page": 45,
      "progress_percentage": 10.00,
      "total_knowledge_units": 2250,
      "total_images": 180,
      "verified_percentage": 0.00,
      "language": "english",
      "upload_date": "2025-11-03T10:30:00Z"
    }
  ]
}
```

---

#### GET /api/book/{book_id}
**Description:** Get detailed book information
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "book_name": "Machine Learning Fundamentals.pdf",
  "sanitized_name": "ml_fundamentals",
  "table_prefix": "book1_ml_fundamentals",
  "file_type": "PDF",
  "file_size_bytes": 52428800,
  "total_pages": 450,
  "processing_status": "processing",
  "current_page": 45,
  "progress_percentage": 10.00,
  "last_checkpoint_page": 0,
  "language": "english",
  "total_knowledge_units": 2250,
  "total_images": 180,
  "verified_units": 0,
  "verified_percentage": 0.00,
  "upload_date": "2025-11-03T10:30:00Z",
  "processing_started_at": "2025-11-03T10:35:00Z",
  "settings": {
    "special_instructions": "",
    "extraction_sensitivity": "balanced",
    "ocr_quality": "balanced"
  }
}
```

**Errors:**
- 404: Book not found

---

#### DELETE /api/book/{book_id}
**Description:** Delete book and all related data
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "message": "Book 1 deleted successfully.",
  "tables_dropped": 7
}
```

**Errors:**
- 404: Book not found
- 409: Cannot delete while processing

---

### 3. Knowledge Unit Management

#### GET /api/records/{book_id}
**Description:** Get knowledge units for a book (paginated)
**Parameters:**
- `book_id` (path, integer): Book ID

**Query Parameters:**
- `page` (optional, default 1): Page number
- `limit` (optional, default 20): Records per page
- `verified` (optional): Filter by verified status (true/false)
- `page_number` (optional): Filter by source page number
- `confidence_min` (optional): Minimum confidence score (0-100)

**Response (200 OK):**
```json
{
  "book_id": 1,
  "total_records": 2250,
  "page": 1,
  "limit": 20,
  "total_pages": 113,
  "records": [
    {
      "id": 123,
      "text_content": "Machine learning is...",
      "page_number": 15,
      "language": "english",
      "confidence_score": 92.50,
      "chapter": "Chapter 1: Introduction",
      "topic": "Types of Machine Learning",
      "verified": true,
      "attributes": {
        "related_image": null,
        "Difficulty Level": "Beginner",
        "Topic Category": "Theory",
        "Importance": "High"
      },
      "created_at": "2025-11-03T11:15:00Z"
    }
  ]
}
```

---

#### GET /api/record/{record_id}
**Description:** Get single knowledge unit with context (5 before + current + 5 after = 11 records)
**Parameters:**
- `record_id` (path, integer): Record ID

**Query Parameters:**
- `book_id` (required): Book ID (for table lookup)
- `show_disabled` (optional, default false): Include disabled records in context

**Response (200 OK):**
```json
{
  "current": {
    "id": 150,
    "text_content": "Machine learning is...",
    "page_number": 15,
    "language": "english",
    "confidence_score": 92.50,
    "chapter": "Chapter 1: Introduction",
    "topic": "Types of Machine Learning",
    "verified": true,
    "attr8_value": "enabled",
    "merged_into_record_id": null,
    "original_record_ids": null,
    "attributes": {
      "related_image": null,
      "record_status": "enabled",
      "Difficulty Level": "Beginner",
      "Topic Category": "Theory"
    },
    "created_at": "2025-11-03T11:15:00Z"
  },
  "context_before": [
    /* 5 records before current (id 145-149) */
  ],
  "context_after": [
    /* 5 records after current (id 151-155) */
  ],
  "page_image_url": "/api/page-image/1/15",
  "marked_page_url": "/api/page-marked/1/15"
}
```

---

#### PUT /api/record/{record_id}
**Description:** Update knowledge unit
**Parameters:**
- `record_id` (path, integer): Record ID

**Query Parameters:**
- `book_id` (required): Book ID

**Request Body:**
```json
{
  "text_content": "Updated text...",
  "chapter": "Chapter 1: Introduction",
  "topic": "ML Types",
  "sub_topic": null,
  "verified": true,
  "attributes": {
    "2": "Intermediate",  // attr2_value
    "3": "Practice",      // attr3_value
    "4": "Medium"         // attr4_value
  },
  "notes": "Reviewed and approved"
}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "message": "Record updated successfully.",
  "verified": true,
  "updated_at": "2025-11-03T14:30:00Z"
}
```

---

#### POST /api/record/merge
**Description:** Merge current record with previous or next records (up to 5 in each direction)
**Request Body:**
```json
{
  "book_id": 1,
  "target_record_id": 150,  // Current record (will receive merged text)
  "merge_direction": "next",  // "previous" or "next"
  "merge_count": 2  // How many records to merge (1-5)
}
```

**Example - Merge with Next 2:**
- Target record 150 gets text from 150 + 151 + 152
- Records 151 and 152 marked as disabled (attr8_value = 'disabled')
- Records 151 and 152 set merged_into_record_id = 150
- Target record 150 sets original_record_ids = [150, 151, 152]

**Response (200 OK):**
```json
{
  "target_record_id": 150,
  "merged_text": "Combined text from all 3 records...",
  "disabled_record_ids": [151, 152],
  "original_record_ids": [150, 151, 152],
  "message": "Successfully merged 2 records into record 150."
}
```

**Errors:**
- 400: Invalid merge_count (must be 1-5)
- 400: Not enough records available in specified direction
- 400: Target record is disabled (must unmerge first)
- 404: Target record not found
- 500: Database transaction failed

---

#### POST /api/record/split
**Description:** Split current record into multiple records at specified split points
**Request Body:**
```json
{
  "book_id": 1,
  "record_id": 200,
  "split_points": [25, 52]  // Character positions to split at
}
```

**Example - Split into 3 parts:**
- Original text: "Neural networks learn patterns. They use backpropagation. Training requires large datasets."
- Split points: [25, 52] (after "patterns." and after "backpropagation.")
- Result: 3 records

**Response (200 OK):**
```json
{
  "original_record_id": 200,
  "new_record_ids": [200, 201, 202],
  "split_count": 3,
  "message": "Record 200 split into 3 records.",
  "created_records": [
    {
      "id": 200,
      "text_content": "Neural networks learn patterns.",
      "original_record_ids": ["200"]
    },
    {
      "id": 201,
      "text_content": "They use backpropagation.",
      "original_record_ids": ["200"]
    },
    {
      "id": 202,
      "text_content": "Training requires large datasets.",
      "original_record_ids": ["200"]
    }
  ]
}
```

**Errors:**
- 400: Invalid split_points (must be within text length)
- 400: Record is disabled (cannot split disabled records)
- 404: Record not found
- 500: Database transaction failed

---

#### POST /api/record/unmerge
**Description:** Restore merged records (undo merge operation)
**Request Body:**
```json
{
  "book_id": 1,
  "merged_record_id": 150  // The target record that received merged text
}
```

**Response (200 OK):**
```json
{
  "restored_record_ids": [151, 152],
  "target_record_id": 150,
  "message": "Successfully restored 2 records that were merged into record 150."
}
```

**Errors:**
- 400: Record has no merge history (original_record_ids is null)
- 404: Record not found
- 500: Database transaction failed

---

#### POST /api/record/unsplit
**Description:** Recombine split records (undo split operation)
**Request Body:**
```json
{
  "book_id": 1,
  "record_ids": [200, 201, 202]  // All records created from split
}
```

**Response (200 OK):**
```json
{
  "combined_record_id": 200,
  "deleted_record_ids": [201, 202],
  "combined_text": "Full original text...",
  "message": "Successfully recombined 3 records into record 200."
}
```

**Errors:**
- 400: Records do not share same original_record_ids
- 404: One or more records not found
- 500: Database transaction failed

---

#### GET /api/records/{book_id}/filter
**Description:** Get records filtered by status (enabled/disabled/all)
**Parameters:**
- `book_id` (path, integer): Book ID

**Query Parameters:**
- `filter` (required): "enabled", "disabled", or "all"
- `page` (optional, default 1): Page number
- `limit` (optional, default 20): Records per page

**Response (200 OK):**
```json
{
  "book_id": 1,
  "filter": "enabled",
  "total_records": 2200,  // Only enabled records
  "total_disabled": 50,   // Count of disabled records
  "page": 1,
  "limit": 20,
  "records": [
    /* Same format as GET /api/records/{book_id} */
  ]
}
```

---

### 4. Image Management

#### GET /api/images/{book_id}
**Description:** Get images for a book
**Parameters:**
- `book_id` (path, integer): Book ID

**Query Parameters:**
- `page_number` (optional): Filter by page
- `image_type` (optional): Filter by type (diagram, chart, photo, etc.)
- `limit` (optional, default 20): Results per page
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**
```json
{
  "total": 180,
  "images": [
    {
      "id": 68,
      "image_id": "IMG-068",
      "page_number": 136,
      "image_type": "diagram",
      "ai_description": "A flowchart diagram...",
      "confidence_score": 92.30,
      "figure_number": "Figure 5.3",
      "linked_text_count": 3,
      "thumbnail_url": "/api/image-thumbnail/1/68"
    }
  ]
}
```

---

#### GET /api/image/{book_id}/{image_id}
**Description:** Get full image details with linked texts
**Parameters:**
- `book_id` (path, integer): Book ID
- `image_id` (path, integer): Image database ID

**Response (200 OK):**
```json
{
  "id": 68,
  "image_id": "IMG-068",
  "page_number": 136,
  "ai_description": "A detailed flowchart...",
  "structured_json": { /* extracted data */ },
  "image_type": "diagram",
  "confidence_score": 92.30,
  "figure_number": "Figure 5.3",
  "image_url": "/api/image-data/1/68",
  "linked_texts": [
    { "id": 245, "text_preview": "As shown in Figure 5.3..." },
    { "id": 246, "text_preview": "The pipeline illustrated..." }
  ],
  "marker_pages": {
    "green_page": "/api/page-marked/1/136",  // Original image page with GREEN marker
    "orange_pages": [  // All linked text pages with ORANGE markers
      { "page_number": 135, "url": "/api/page-marked/1/135" },
      { "page_number": 137, "url": "/api/page-marked/1/137" }
    ]
  }
}
```

---

#### GET /api/image-data/{book_id}/{image_id}
**Description:** Get raw image data (binary)
**Parameters:**
- `book_id` (path, integer): Book ID
- `image_id` (path, integer): Image ID

**Response:** Binary image data (PNG)
**Content-Type:** image/png

---

#### GET /api/image-thumbnail/{book_id}/{image_id}
**Description:** Get image thumbnail (200x200)
**Parameters:**
- `book_id` (path, integer): Book ID
- `image_id` (path, integer): Image ID

**Response:** Binary thumbnail data
**Content-Type:** image/png

---

### 5. Page Image Management

#### GET /api/page-image/{book_id}/{page_number}
**Description:** Get original page image
**Parameters:**
- `book_id` (path, integer): Book ID
- `page_number` (path, integer): Page number

**Response:** Binary page image (PNG)
**Content-Type:** image/png

---

#### GET /api/page-marked/{book_id}/{page_number}
**Description:** Get marked page image (with green/orange rectangles)
**Parameters:**
- `book_id` (path, integer): Book ID
- `page_number` (path, integer): Page number

**Response:** Binary marked page image (PNG)
**Content-Type:** image/png

---

### 6. Book Settings

#### GET /api/settings/{book_id}
**Description:** Get book settings
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "settings": {
    "special_instructions": "Focus on code examples...",
    "language_setting": "english",
    "extraction_sensitivity": "balanced",
    "ocr_quality": "high",
    "partial_processing_enabled": true,
    "partial_processing_pages": 10
  }
}
```

---

#### PUT /api/settings/{book_id}
**Description:** Update book settings (only if not processing)
**Parameters:**
- `book_id` (path, integer): Book ID

**Request Body:**
```json
{
  "special_instructions": "Updated instructions..."
}
```

**Response (200 OK):**
```json
{
  "message": "Settings updated successfully."
}
```

**Errors:**
- 409: Cannot update settings while processing

---

#### GET /api/attribute-keys/{book_id}
**Description:** Get attribute key names for book
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "attribute_keys": {
    "1": "related_image",  // System-defined, not editable
    "2": "Difficulty Level",
    "3": "Topic Category",
    "4": "Importance",
    "5": "Keywords",
    "6": "",  // Empty = not used
    // ... up to 30
  }
}
```

---

#### PUT /api/attribute-keys/{book_id}
**Description:** Update attribute key names (2-30, cannot edit key 1)
**Parameters:**
- `book_id` (path, integer): Book ID

**Request Body:**
```json
{
  "attribute_keys": {
    "2": "Complexity Level",  // Renamed
    "11": "Source Reference"  // Added new key
  }
}
```

**Response (200 OK):**
```json
{
  "message": "Attribute keys updated successfully.",
  "updated_keys": [2, 11]
}
```

**Errors:**
- 400: Attempt to edit attr1 (not allowed)

---

### 7. Processing State

#### GET /api/processing-state/{book_id}
**Description:** Get current processing state
**Parameters:**
- `book_id` (path, integer): Book ID

**Response (200 OK):**
```json
{
  "book_id": 1,
  "status": "processing",
  "current_page": 45,
  "total_pages": 450,
  "progress_percentage": 10.00,
  "pages_processed": 44,
  "knowledge_units_extracted": 2200,
  "images_extracted": 72,
  "ocr_retry_count": 5,
  "avg_page_processing_time": 12.50,
  "estimated_time_remaining": 5062,  // seconds
  "agent_states": {
    "reader": {"status": "processing", "current_page": 45},
    "splitter": {"status": "idle", "current_page": 44}
  },
  "last_checkpoint_page": 0,
  "last_updated_at": "2025-11-03T11:00:00Z"
}
```

---

## 🔌 WebSocket Endpoints

### WS /ws/processing/{book_id}
**Description:** Real-time processing updates (2-second interval)
**Parameters:**
- `book_id` (path, integer): Book ID

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/processing/1');
```

**Server Messages:**
```json
{
  "event": "processing_update",
  "book_id": 1,
  "current_page": 46,
  "progress_percentage": 10.22,
  "knowledge_units_extracted": 2300,
  "images_extracted": 74,
  "estimated_time_remaining": 5000,
  "timestamp": "2025-11-03T11:00:30Z"
}
```

**Checkpoint Event:**
```json
{
  "event": "checkpoint_saved",
  "book_id": 1,
  "checkpoint_page": 50,
  "timestamp": "2025-11-03T11:05:00Z"
}
```

**Completion Event:**
```json
{
  "event": "processing_complete",
  "book_id": 1,
  "total_pages": 450,
  "total_knowledge_units": 22500,
  "total_images": 1800,
  "timestamp": "2025-11-03T14:00:00Z"
}
```

**Error Event:**
```json
{
  "event": "processing_error",
  "book_id": 1,
  "error_message": "OCR failed after 3 attempts on page 78",
  "current_page": 78,
  "timestamp": "2025-11-03T12:30:00Z"
}
```

**Client Commands:**
```json
// Client can send commands
{
  "command": "pause",
  "book_id": 1
}

{
  "command": "resume",
  "book_id": 1
}
```

---

## 📊 Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Success |
| 201 | Created - Resource created |
| 204 | No Content - Success, no response body |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource not found |
| 409 | Conflict - State conflict (e.g., already processing) |
| 413 | Payload Too Large - File > 500MB |
| 500 | Internal Server Error - Server failure |

---

## 🔒 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Only localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## ✅ API Design Checklist

- [x] All CRUD endpoints defined
- [x] WebSocket real-time updates specified
- [x] Request/response schemas documented
- [x] Error codes defined
- [x] Pagination support
- [x] File upload endpoint
- [x] Binary data endpoints (images)
- [x] Filtering and querying support
- [x] No authentication (single-user local)
- [x] CORS configured for localhost

---

**API Design Complete:** ✅
**Total Endpoints:** 25+ HTTP + 1 WebSocket
**Ready for:** Code Chunk Breakdown

