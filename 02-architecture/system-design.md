# System Design - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Architect:** Claude (Architect Agent)
**Version:** 1.0
**Status:** ✅ Architecture Design Complete

---

## 📋 Executive Summary

The Knowledge Extraction System is a desktop application that processes documents using a multi-agent architecture with centralized database storage. The system extracts semantic knowledge units, analyzes images, and provides a visual verification interface for quality assurance.

**Architecture Pattern:** Monolithic Multi-Agent System with Networked Database
**Deployment:** Single-machine desktop application with remote PostgreSQL database
**Primary Language:** Python 3.9+
**Interface:** Web-based UI (localhost) using FastAPI backend + HTML/CSS/JavaScript frontend

---

## 🎯 Key Architecture Decisions

### Decision 1: Localhost Web Interface vs Desktop Application

**DECISION: Localhost Web Interface (FastAPI + HTML/CSS/JavaScript)**

**Rationale:**
- **Simplicity:** No need for Electron, PyQt, or Tkinter complexity
- **Development Speed:** HTML/CSS for UI is faster than desktop GUI frameworks
- **Cross-Platform:** Works on Windows without platform-specific code
- **Maintenance:** Easier to update and debug web interface
- **User Experience:** Modern browser capabilities (split-screen, drag-drop)
- **Single Virtual Environment:** All Python code in one venv

**Trade-off Accepted:** User must open browser to http://localhost:8000 (acceptable for single-user local deployment)

---

### Decision 2: Web Framework Selection

**DECISION: FastAPI (instead of Flask)**

**Rationale:**
- **Async Support:** Native async/await for long-running agent tasks
- **Background Tasks:** Built-in BackgroundTasks for processing
- **WebSocket Support:** Real-time dashboard updates (2-second intervals)
- **Type Safety:** Pydantic models with automatic validation
- **Auto Documentation:** Built-in OpenAPI/Swagger docs
- **Performance:** Faster than Flask for concurrent requests
- **Modern:** Industry standard for new Python web APIs

**Libraries:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `python-multipart` - File upload support
- `websockets` - Real-time updates

---

### Decision 3: PDF Processing Library

**DECISION: PyMuPDF (fitz) - Primary | pdfplumber - Fallback**

**Rationale:**
- **PyMuPDF (fitz):**
  - ✓ Fastest PDF rendering and text extraction
  - ✓ Image extraction capabilities
  - ✓ Page-to-image conversion with high quality
  - ✓ Coordinate-based text positioning (for markers)
  - ✓ Handles large PDFs efficiently (500MB+)
  - ✓ Active maintenance and documentation

- **pdfplumber (fallback):**
  - ✓ Better table detection
  - ✓ More accurate text positioning in complex layouts
  - ✓ Used when PyMuPDF fails or for table-heavy pages

**Strategy:** Try PyMuPDF first, fallback to pdfplumber if extraction confidence < 60%

---

### Decision 4: OCR Library

**DECISION: pytesseract (Tesseract 4.x wrapper)**

**Rationale:**
- **pytesseract:**
  - ✓ Industry standard OCR engine
  - ✓ Excellent Arabic + English support
  - ✓ Configurable quality levels (fast/balanced/high)
  - ✓ Confidence scores per word/line
  - ✓ Free and open-source
  - ✓ Proven reliability

- **Why NOT easyocr:**
  - ✗ Requires PyTorch (large dependency, ~500MB+)
  - ✗ Slower processing time
  - ✗ More complex setup

- **Why NOT PaddleOCR:**
  - ✗ Requires PaddlePaddle framework
  - ✗ Less mature Python bindings
  - ✗ Limited English documentation

**External Dependency:** Tesseract must be installed on system (documented in prerequisites)

---

### Decision 5: Image Processing Library

**DECISION: Pillow (PIL) - Primary | OpenCV - For Markers Only**

**Rationale:**
- **Pillow:**
  - ✓ Standard Python imaging library
  - ✓ Simple API for image manipulation
  - ✓ Format conversion (PDF → PNG)
  - ✓ Image resizing and optimization
  - ✓ No external system dependencies

- **OpenCV (cv2):**
  - ✓ Used ONLY for drawing markers (rectangles on images)
  - ✓ Better performance for geometric drawing
  - ✓ Anti-aliasing support

**Strategy:** Pillow for all image I/O, OpenCV only for marker drawing

---

### Decision 6: AI Model for Semantic Splitting

**DECISION: sentence-transformers (SBERT) with lightweight model**

**Rationale:**
- ✓ Purpose-built for semantic similarity
- ✓ Pre-trained models available
- ✓ Fast inference on CPU
- ✓ Bilingual support (English + Arabic)
- ✓ Generates embeddings for Chroma vector DB
- ✓ Model: `paraphrase-multilingual-MiniLM-L12-v2` (420MB, supports 50+ languages)

**Fallback:** Simple heuristic splitter using spaCy sentence boundaries if model too large

---

### Decision 7: Database Connection Strategy

**DECISION: SQLAlchemy ORM with Connection Pooling**

**Rationale:**
- **SQLAlchemy:**
  - ✓ Industry-standard Python ORM
  - ✓ Connection pooling built-in
  - ✓ Migration support (Alembic)
  - ✓ Dynamic table creation (for book-specific tables)
  - ✓ Type safety with models
  - ✓ Query optimization

- **Connection Pooling Configuration:**
  - Pool size: 10 connections
  - Max overflow: 20 connections
  - Pool timeout: 30 seconds
  - Recycle connections: 3600 seconds (1 hour)

- **Why NOT Raw SQL:**
  - ✗ Manual connection management
  - ✗ SQL injection risks
  - ✗ No automatic retries
  - ✗ More boilerplate code

**Network Considerations:**
- PostgreSQL on separate Windows machine
- Connection string: `postgresql://user:pass@db-server-ip:5432/knowledge_extraction`
- Automatic reconnection on network failures
- Transaction management for checkpoint saves

---

### Decision 8: Real-time Dashboard Updates

**DECISION: WebSocket (FastAPI WebSocket) with 2-second heartbeat**

**Rationale:**
- **WebSocket:**
  - ✓ True real-time updates (no polling overhead)
  - ✓ Bidirectional communication
  - ✓ Built into FastAPI
  - ✓ Low latency
  - ✓ Efficient for continuous updates

- **Why NOT HTTP Polling:**
  - ✗ Server overhead (requests every 2 seconds)
  - ✗ Higher latency (average 1 second delay)
  - ✗ Wasted bandwidth

**Implementation:**
- WebSocket endpoint: `/ws/processing/{book_id}`
- Server pushes updates when processing state changes
- Client displays: page progress, OCR retries, extracted records count
- Auto-reconnect on connection loss

---

### Decision 9: Image Storage Strategy

**DECISION: PostgreSQL BYTEA (binary blobs) with LZ4 compression**

**Rationale:**
- **Database Storage:**
  - ✓ Transactional consistency with text data
  - ✓ Automatic backup with database
  - ✓ No file system sync issues
  - ✓ Easier deployment (no separate file storage)
  - ✓ No broken file paths

- **Compression:**
  - ✓ LZ4: Fast compression/decompression
  - ✓ 30-50% size reduction for PNG images
  - ✓ Minimal CPU overhead

- **Why NOT File System:**
  - ✗ Sync issues with database
  - ✗ File path management complexity
  - ✗ Backup coordination needed
  - ✗ Potential orphaned files

**Optimization:**
- Store images at 800x600 max resolution (configurable)
- Lazy loading (images fetched only when needed)
- Thumbnail generation (200x200) for library view

---

### Decision 10: Agent Communication Architecture

**DECISION: Direct Database Access (Shared State via PostgreSQL)**

**Rationale:**
- **Direct DB Access:**
  - ✓ Simplest architecture
  - ✓ No inter-process communication complexity
  - ✓ Single source of truth (database)
  - ✓ Agents run sequentially (no race conditions)
  - ✓ Easy to debug and monitor

- **Why NOT Message Queue (RabbitMQ/Redis):**
  - ✗ Unnecessary complexity for sequential processing
  - ✗ Additional infrastructure
  - ✗ Not needed for single-user deployment

- **Why NOT API Endpoints Between Agents:**
  - ✗ Overhead of HTTP requests
  - ✗ More error handling needed
  - ✗ Agents run in same Python process

**Architecture:**
```
Reader Agent → Database → Splitter Agent → Database → Marker Agent → Database → Image-Reader Agent
    ↓                          ↓                           ↓                          ↓
  PostgreSQL              PostgreSQL                  PostgreSQL                PostgreSQL
```

All agents share same SQLAlchemy session and connection pool.

---

### Decision 11: Background Processing Strategy

**DECISION: FastAPI BackgroundTasks with ProcessPoolExecutor**

**Rationale:**
- **BackgroundTasks:**
  - ✓ Built into FastAPI
  - ✓ Non-blocking (user gets immediate response)
  - ✓ Easy to implement

- **ProcessPoolExecutor (for agents):**
  - ✓ CPU-intensive OCR runs in separate process
  - ✓ Avoids GIL limitations
  - ✓ Configurable worker count (default: 2)
  - ✓ Easy to pause/resume

- **Why NOT Celery:**
  - ✗ Overkill for single-user system
  - ✗ Requires Redis/RabbitMQ broker
  - ✗ More complex deployment

**Processing Flow:**
1. User uploads file → FastAPI endpoint
2. FastAPI creates background task
3. Background task spawns agent process
4. Agents update database continuously
5. WebSocket pushes updates to frontend
6. User sees real-time progress

---

## 🏗️ System Architecture

### Architecture Pattern

**Monolithic Multi-Agent System** with the following characteristics:

- **Monolithic:** Single Python application with all agents
- **Multi-Agent:** Specialized agents with distinct responsibilities
- **Shared Database:** All agents access same PostgreSQL + Chroma
- **Web Interface:** Browser-based UI (FastAPI backend)
- **Networked Database:** PostgreSQL on separate Windows machine

---

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                               │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────────┐   │
│  │  Upload Page   │  │   Dashboard     │  │  Verification UI   │   │
│  │  (HTML/CSS/JS) │  │  (WebSocket)    │  │  (Split-Screen)    │   │
│  └────────┬───────┘  └────────┬────────┘  └─────────┬──────────┘   │
│           │                   │                      │              │
│           └───────────────────┼──────────────────────┘              │
│                               │                                     │
└───────────────────────────────┼─────────────────────────────────────┘
                                │ HTTP/WebSocket (localhost:8000)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI WEB APPLICATION                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     API Endpoints                             │  │
│  │  /upload  /start  /pause  /resume  /verify  /books  /ws      │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────┴───────────────────────────────────┐  │
│  │              Background Task Manager                          │  │
│  │         (FastAPI BackgroundTasks + ProcessPool)               │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────┴───────────────────────────────────┐  │
│  │                   AGENT ORCHESTRATOR                          │  │
│  │        (Sequential agent execution with checkpoints)          │  │
│  └──────┬────────┬────────┬────────┬───────────────────────────┘   │
│         │        │        │        │                               │
│    ┌────▼────┐ ┌▼────────▼┐ ┌─────▼──────┐ ┌──────────────────┐   │
│    │ Reader  │ │ Splitter │ │  Marker    │ │  Image-Reader    │   │
│    │  Agent  │ │  Agent   │ │  Agent     │ │     Agent        │   │
│    └────┬────┘ └┬─────────┘ └─────┬──────┘ └──────┬───────────┘   │
│         │       │                 │                │               │
│         └───────┴─────────────────┴────────────────┘               │
│                              │                                     │
│  ┌───────────────────────────▼───────────────────────────────────┐  │
│  │                 SQLAlchemy ORM Layer                          │  │
│  │            (Connection Pool + Models + Sessions)              │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
└────────────────────────────────┼─────────────────────────────────────┘
                                │ TCP/IP (psycopg2 driver)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DATABASE SERVER (Separate Windows Machine)             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL 15+                           │   │
│  │                  (with pgvector extension)                  │   │
│  │                                                             │   │
│  │  • books_metadata (shared table)                           │   │
│  │  • book{N}_{name}_knowledge_units (per book)               │   │
│  │  • book{N}_{name}_images (per book)                        │   │
│  │  • book{N}_{name}_processing_state (per book)              │   │
│  │  • book{N}_{name}_settings (per book)                      │   │
│  │  • book{N}_{name}_pages (per book)                         │   │
│  │  • book{N}_{name}_hierarchy (per book)                     │   │
│  │  • book{N}_{name}_attribute_keys (per book)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Chroma Vector DB                       │   │
│  │              (for future cross-book similarity)             │   │
│  │  • book{N}_embeddings (per book collection)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Component Specifications

### 1. Web Application Layer (FastAPI)

**Purpose:** HTTP/WebSocket server providing API and serving frontend

**Responsibilities:**
- Serve static HTML/CSS/JavaScript files
- Handle file uploads (multipart/form-data)
- Provide REST API endpoints
- Manage WebSocket connections for real-time updates
- Spawn background tasks for document processing
- Session management (in-memory, single user)

**Key Technologies:**
- FastAPI 0.104+
- Uvicorn ASGI server
- Jinja2 templates (for server-side rendering if needed)
- Static file serving

**Endpoints:**
```
GET  /                          - Serve upload page
GET  /dashboard                 - Serve processing dashboard
GET  /verify/{book_id}          - Serve verification interface
GET  /library                   - Serve book library
GET  /book-settings/{book_id}   - Serve book settings page
POST /api/upload                - Upload file
POST /api/start-processing      - Start processing a book
POST /api/pause/{book_id}       - Pause processing
POST /api/resume/{book_id}      - Resume processing
GET  /api/books                 - List all books
GET  /api/book/{book_id}        - Get book details
GET  /api/records/{book_id}     - Get knowledge units (paginated)
PUT  /api/record/{record_id}    - Update knowledge unit
POST /api/merge                 - Merge two records
WS   /ws/processing/{book_id}   - WebSocket for real-time updates
```

---

### 2. Agent Orchestrator

**Purpose:** Coordinates agent execution and manages processing flow

**Responsibilities:**
- Load book settings from database
- Execute agents sequentially (Reader → Splitter → Marker → Image-Reader)
- Manage checkpoints every 50 pages
- Handle pause/resume state
- Save processing state continuously
- Report progress via WebSocket
- Handle OCR retry logic
- Manage agent failures and error recovery

**Key Logic:**
```python
def process_book(book_id):
    while current_page <= total_pages:
        # Reader Agent
        raw_text = reader_agent.read_page(current_page)

        # Splitter Agent
        knowledge_units = splitter_agent.split(raw_text)

        # Marker Agent
        marked_image = marker_agent.create_markers(current_page, knowledge_units)

        # Image-Reader Agent (if images on page)
        images = image_reader_agent.analyze_images(current_page)

        # Save to database
        save_results(knowledge_units, marked_image, images)

        # Checkpoint every 50 pages
        if current_page % 50 == 0:
            save_checkpoint(book_id, current_page)

        # Check for pause signal
        if check_pause_signal(book_id):
            save_state_and_exit()

        current_page += 1
```

---

### 3. Reader Agent

**Purpose:** Extract raw text from document pages with OCR support

**Responsibilities:**
- Convert PDF pages to images (PyMuPDF)
- Extract text from native PDF text layer
- Perform OCR on scanned content (pytesseract)
- Detect language (English/Arabic/Mixed)
- Extract text coordinates for marker agent
- Implement 3-attempt OCR retry logic with zoom

**Dependencies:**
- PyMuPDF (fitz)
- pytesseract (wrapper for Tesseract)
- Pillow (image preprocessing)
- langdetect (language detection)

**OCR Retry Strategy:**
```python
def extract_text_with_retry(page_image):
    # Attempt 1: Standard OCR
    text, confidence = ocr(page_image, quality="balanced")
    if confidence >= 70:
        return text

    # Attempt 2: Zoom 200% + High Quality
    zoomed = resize_image(page_image, scale=2.0)
    text, confidence = ocr(zoomed, quality="high")
    if confidence >= 60:
        return text

    # Attempt 3: Segment regions + High Quality
    regions = segment_text_regions(page_image)
    text = ""
    for region in regions:
        region_text, _ = ocr(region, quality="high")
        text += region_text
    return text
```

---

### 4. Splitter Agent

**Purpose:** Split raw text into semantic knowledge units (3-5 lines each)

**Responsibilities:**
- Analyze text semantically using SBERT
- Split into 3-5 line chunks per idea
- Respect paragraph boundaries
- Detect multi-idea paragraphs and split appropriately
- Assign confidence score to each knowledge unit
- Extract hierarchy (chapter/topic/sub-topic) from headings

**Dependencies:**
- sentence-transformers (SBERT model)
- spaCy (sentence boundaries, fallback)
- Custom heuristics (paragraph detection)

**Splitting Algorithm:**
```python
def split_text(raw_text):
    paragraphs = detect_paragraphs(raw_text)
    knowledge_units = []

    for para in paragraphs:
        sentences = split_sentences(para)

        # Compute semantic similarity between consecutive sentences
        embeddings = sbert_model.encode(sentences)
        similarities = cosine_similarity(embeddings)

        # Find split points where similarity < threshold (0.6)
        split_indices = find_low_similarity_points(similarities)

        # Create knowledge units (3-5 lines each)
        for chunk in create_chunks(sentences, split_indices):
            if 3 <= len(chunk.split('\n')) <= 5:
                knowledge_units.append({
                    'text': chunk,
                    'confidence': calculate_confidence(chunk),
                    'line_count': len(chunk.split('\n'))
                })

    return knowledge_units
```

---

### 5. Marker Agent

**Purpose:** Create visual markers (rectangles) on page images

**Responsibilities:**
- Load page image from PDF
- Draw GREEN rectangles around extracted text regions
- Draw ORANGE rectangles around text linked to images
- Save marked images to database
- Generate thumbnails for verification interface

**Dependencies:**
- OpenCV (cv2) - rectangle drawing
- Pillow - image I/O
- PyMuPDF - coordinate conversion

**Marker Creation:**
```python
def create_markers(page_number, knowledge_units, images):
    page_image = get_page_image(page_number)

    # Draw green rectangles for text
    for ku in knowledge_units:
        x1, y1, x2, y2 = ku['coordinates']
        cv2.rectangle(page_image, (x1, y1), (x2, y2),
                      color=(0, 255, 0), thickness=2)  # Green

    # Draw orange rectangles for image-linked text
    for img in images:
        for linked_text in img['linked_texts']:
            x1, y1, x2, y2 = linked_text['coordinates']
            cv2.rectangle(page_image, (x1, y1), (x2, y2),
                          color=(255, 165, 0), thickness=2)  # Orange

    # Save to database
    save_marked_image(page_number, page_image)
```

---

### 6. Image-Reader Agent

**Purpose:** Analyze and describe images using AI

**Responsibilities:**
- Extract all images from page (diagrams, charts, photos)
- Generate human-readable AI description
- Create structured JSON representation
- Assign confidence score
- Extract image metadata (type, dimensions, file size)
- Store images in database

**Dependencies:**
- PyMuPDF (image extraction)
- transformers (image captioning model: BLIP or similar)
- Pillow (image processing)

**Future Enhancement:**
- Use OpenAI Vision API or similar for high-quality descriptions
- Current: Use local BLIP model for privacy

**Image Analysis:**
```python
def analyze_image(image_data):
    # Generate AI description
    description = blip_model.generate_description(image_data)

    # Create structured JSON (extract text from charts, etc.)
    structured_data = extract_structured_data(image_data)

    # Detect image type
    image_type = classify_image(image_data)  # diagram|chart|photo

    return {
        'ai_description': description,
        'structured_json': structured_data,
        'image_type': image_type,
        'confidence': calculate_confidence(description),
        'dimensions': get_dimensions(image_data)
    }
```

---

### 7. Database Access Layer (SQLAlchemy)

**Purpose:** Provide ORM interface to PostgreSQL database

**Responsibilities:**
- Define data models for all tables
- Manage database connections (connection pooling)
- Handle dynamic table creation (book-specific tables)
- Provide CRUD operations
- Manage transactions and rollbacks
- Support migrations (Alembic)

**Key Models:**
- `BooksMetadata` - Shared table for all books
- `KnowledgeUnit` - Base model, dynamically mapped to book-specific tables
- `Image` - Base model for images
- `ProcessingState` - Tracks processing progress
- `BookSettings` - Book-specific configuration
- `Page` - Stores marked page images
- `Hierarchy` - Document structure
- `AttributeKey` - Book-level attribute names (1-30)

**Connection Configuration:**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@db-server-ip:5432/knowledge_extraction",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False  # Set True for debugging
)
```

---

### 8. Frontend (HTML/CSS/JavaScript)

**Purpose:** Provide user interface in browser

**Responsibilities:**
- Upload page with drag-and-drop
- Processing dashboard with real-time progress
- Split-screen verification interface
- Book library dashboard
- Book settings page
- WebSocket client for real-time updates

**Technologies:**
- Vanilla JavaScript (no frameworks - simplicity first)
- CSS3 with Flexbox/Grid
- Fetch API for HTTP requests
- WebSocket API for real-time updates
- LocalStorage for UI preferences

**Key Features:**
- Responsive layout (1920x1080 target)
- RTL support for Arabic text
- Color-coded UI (green/orange/blue/red)
- Image zoom/pan controls
- Keyboard shortcuts for navigation

---

## 📊 Data Flow Diagram

### Upload & Processing Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Upload file + settings
     ▼
┌────────────────┐
│  Upload Page   │
│  (Frontend)    │
└────┬───────────┘
     │ 2. POST /api/upload
     ▼
┌────────────────────┐
│  FastAPI Backend   │
│  • Validate file   │
│  • Assign book_id  │
│  • Create tables   │
└────┬───────────────┘
     │ 3. Save metadata
     ▼
┌─────────────────────┐
│  books_metadata     │
│  (PostgreSQL)       │
└─────────────────────┘
     │ 4. User clicks "Start Processing"
     ▼
┌────────────────────────┐
│  Agent Orchestrator    │
│  (Background Process)  │
└────┬───────────────────┘
     │ 5. For each page:
     │
     ├──> Reader Agent ──> Extract text ──> DB
     │
     ├──> Splitter Agent ──> Split text ──> DB
     │
     ├──> Marker Agent ──> Draw markers ──> DB
     │
     └──> Image-Reader ──> Analyze images ──> DB

     │ 6. Real-time updates
     ▼
┌──────────────────────┐
│  WebSocket Stream    │
│  (to Dashboard)      │
└──────────────────────┘
     │ 7. User verifies
     ▼
┌──────────────────────────┐
│  Verification Interface  │
│  • View records          │
│  • Edit metadata         │
│  • Merge records         │
│  • Approve/reject        │
└──────────────────────────┘
```

---

## 🔐 Security Considerations

**Deployment Context:** Single-user local desktop application

**Security Measures:**
1. **No Authentication:** Single user, localhost only
2. **Database Credentials:** Stored in config file (user's machine)
3. **Network Security:** Database on same local network (firewall protected)
4. **Input Validation:** FastAPI Pydantic models validate all inputs
5. **SQL Injection:** SQLAlchemy ORM prevents injection
6. **File Upload:** Validate file types and size (max 500MB)
7. **CORS:** Restrict to localhost origin only

**Not Required:**
- Multi-user authentication
- Session management
- API rate limiting
- OAuth/JWT
- HTTPS (localhost HTTP is fine)

---

## ⚡ Performance Optimizations

### 1. Database Optimizations
- **Indexes:** Created on frequently queried columns
  - `book_id` on all book-specific tables
  - `page_number` on knowledge_units, pages, images
  - `verified` on knowledge_units (for filtering)
- **Connection Pooling:** Reuse connections (10 pool size)
- **Batch Inserts:** Insert 50 records at a time
- **Lazy Loading:** Images loaded only when viewed

### 2. Processing Optimizations
- **Page Parallel:** Process pages in parallel (2 workers)
- **Image Compression:** LZ4 compression for blobs
- **Thumbnail Generation:** 200x200 thumbnails for library
- **Checkpoint Batching:** Save every 50 pages (not every page)

### 3. Frontend Optimizations
- **Pagination:** 20 records per page in verification
- **Virtual Scrolling:** For long lists
- **Image Lazy Loading:** Load images as user scrolls
- **WebSocket Throttling:** Updates every 2 seconds (not every change)

---

## 🎯 Quality Attributes

### Reliability
- **Crash Recovery:** 100% (database persistence)
- **Checkpoint Frequency:** Every 50 pages
- **OCR Retry:** 3 attempts with escalation
- **Database Reconnection:** Automatic on network failure

### Scalability
- **Books:** Unlimited (isolated tables)
- **Pages per Book:** 1,000 max
- **Concurrent Users:** 1 (single user)
- **Database Growth:** ~1GB per 500-page book

### Maintainability
- **Code Style:** PEP8 compliant
- **Architecture:** Modular agents (SOLID principles)
- **Documentation:** Inline docstrings + architecture docs
- **Testing:** Unit tests for each agent (Tester phase)

### Usability
- **Interface:** Modern web UI
- **Feedback:** Real-time progress updates
- **Error Messages:** Clear and actionable
- **Help:** Inline tooltips and documentation

---

## 📁 File Structure

```
12-extractor/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py       # SQLAlchemy engine + session
│   │   ├── models.py           # ORM models
│   │   ├── schema.py           # Pydantic schemas
│   │   └── migrations/         # Alembic migrations
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Agent coordination
│   │   ├── reader.py           # Reader Agent
│   │   ├── splitter.py         # Splitter Agent
│   │   ├── marker.py           # Marker Agent
│   │   └── image_reader.py     # Image-Reader Agent
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints
│   │   ├── websocket.py        # WebSocket handlers
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ocr.py              # OCR utilities
│   │   ├── image_processing.py # Image utilities
│   │   ├── text_processing.py  # Text utilities
│   │   └── validation.py       # Input validation
│   └── frontend/
│       ├── static/
│       │   ├── css/
│       │   │   └── styles.css
│       │   └── js/
│       │       ├── upload.js
│       │       ├── dashboard.js
│       │       ├── verify.js
│       │       ├── library.js
│       │       └── websocket.js
│       └── templates/
│           ├── upload.html
│           ├── dashboard.html
│           ├── verify.html
│           ├── library.html
│           └── book-settings.html
├── tests/
│   ├── test_agents/
│   ├── test_api/
│   └── test_database/
├── requirements.txt
├── setup.sh
├── config.yaml
└── README.md
```

---

## 🚀 Deployment Architecture

### Local Machine (Windows VM)

```
┌────────────────────────────────────────────┐
│         Windows Virtual Machine            │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  Python 3.9+ Virtual Environment     │  │
│  │                                      │  │
│  │  • FastAPI application (uvicorn)    │  │
│  │  • All agents in same process       │  │
│  │  • Static file serving              │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  System Dependencies                │  │
│  │  • Python 3.9+                      │  │
│  │  • Tesseract OCR                    │  │
│  │  • Browser (Chrome/Firefox/Edge)    │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  User accesses: http://localhost:8000     │
└────────────────┬───────────────────────────┘
                 │
                 │ TCP/IP (Local Network)
                 │ Port: 5432 (PostgreSQL)
                 │
┌────────────────▼───────────────────────────┐
│    Database Server (Windows Machine)       │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  PostgreSQL 15+                      │  │
│  │  • pgvector extension                │  │
│  │  • knowledge_extraction database     │  │
│  │  • Port: 5432                        │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │  Chroma Vector Database              │  │
│  │  • Future: cross-book similarity     │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

### Startup Process

1. **Database Server:** Start PostgreSQL (always running)
2. **Application VM:**
   - Activate virtual environment: `source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows)
   - Start FastAPI: `python src/main.py` or `uvicorn src.main:app --reload`
3. **Browser:** Open http://localhost:8000
4. **Processing:** Upload file → Start processing → View real-time progress

### Shutdown Process

1. **Pause processing** (if active) → Saves state to database
2. **Close browser** (optional)
3. **Stop FastAPI** (Ctrl+C)
4. **Database** continues running (no shutdown needed)
5. **Next session:** Resume from exact page where paused

---

## 📊 Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Backend Framework** | FastAPI | 0.104+ | Web API + WebSocket |
| **ASGI Server** | Uvicorn | 0.24+ | Production ASGI server |
| **Database** | PostgreSQL | 15+ | Primary database |
| **Vector Extension** | pgvector | 0.5+ | Vector similarity (future) |
| **Vector Database** | Chroma | 0.4+ | Future cross-book linking |
| **ORM** | SQLAlchemy | 2.0+ | Database ORM |
| **Migration** | Alembic | 1.12+ | Schema migrations |
| **PDF Library** | PyMuPDF (fitz) | 1.23+ | PDF processing |
| **PDF Fallback** | pdfplumber | 0.10+ | Complex layouts |
| **OCR** | pytesseract | 0.3.10+ | OCR wrapper |
| **OCR Engine** | Tesseract | 4.x | System dependency |
| **Image Processing** | Pillow | 10.1+ | Image I/O |
| **Marker Drawing** | OpenCV (cv2) | 4.8+ | Rectangle drawing |
| **AI Splitting** | sentence-transformers | 2.2+ | Semantic analysis |
| **NLP Fallback** | spaCy | 3.7+ | Sentence boundaries |
| **Language Detection** | langdetect | 1.0.9+ | Detect English/Arabic |
| **Image AI** | transformers (BLIP) | 4.35+ | Image captioning |
| **Compression** | lz4 | 4.3+ | Image compression |
| **Frontend** | Vanilla JS | ES6+ | No framework |
| **Python Version** | Python | 3.9+ | Minimum version |

---

## 🎯 Next Steps (for Developer Agent)

1. **Setup Environment:**
   - Create virtual environment
   - Install dependencies (requirements.txt)
   - Install Tesseract OCR
   - Configure PostgreSQL connection

2. **Database Setup:**
   - Create database schema
   - Test connection from VM to database server
   - Create initial migrations

3. **Implement Code Chunks:**
   - Follow dependency order (Foundation → Core → Services → Presentation)
   - Implement 30-50 LOC chunks sequentially
   - Run tests before moving to next chunk

4. **Frontend Development:**
   - Create HTML templates
   - Implement WebSocket client
   - Build verification interface

5. **Integration Testing:**
   - Test agent orchestration
   - Test pause/resume
   - Test verification workflow

6. **Deployment:**
   - Create startup scripts
   - Document user instructions
   - Package for distribution

---

**Architecture Design Complete:** ✅
**Ready for:** Code Chunk Breakdown + Technology Stack Details + Database Schema Design

