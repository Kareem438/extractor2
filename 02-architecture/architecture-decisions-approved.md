# Architecture Decisions - All Approved ✅

**Project:** Knowledge Extraction System (12-extractor)
**Date:** 2025-11-05 (Updated: 2025-11-07)
**Status:** All 11 decisions APPROVED by user + Major architecture update
**Review Process:** One-by-one approval with modifications
**Latest Update:** Sequential OCR + Integrated SVG Processing

---

## 📋 Decision Summary Table

| # | Decision | Choice | Status | Notes |
|---|----------|--------|--------|-------|
| 1 | Interface Type | Localhost Web (FastAPI) | ✅ APPROVED | Port 8000, browser-based |
| 2 | Real-time Updates | WebSocket (5-second intervals) | ✅ APPROVED | Modified from 2s to 5s |
| 3 | OCR Strategy | **UPDATED:** Sequential User-Controlled | ✅ APPROVED | 4 buttons, integrated image processing |
| 4 | Image Processing | Pillow + OpenCV (Selective Preprocessing) | ✅ APPROVED | Basic always, aggressive <70% |
| 5 | Semantic Splitting | sentence-transformers (multilingual) | ✅ APPROVED | Quality-first approach |
| 6 | Image Analysis | **UPDATED:** Claude Sonnet 4.5 + SVG | ✅ APPROVED | Comprehensive + SVG generation |
| 7 | Database Access | SQLAlchemy ORM + raw SQL fallback | ✅ APPROVED | Hybrid approach |
| 8 | Real-time Implementation | WebSocket (5s updates) | ✅ APPROVED | Same as Decision 2 |
| 9 | Image Storage | **UPDATED:** PostgreSQL BYTEA + SVG | ✅ APPROVED | Binary + SVG code storage |
| 10 | Agent Communication | Direct PostgreSQL access | ✅ APPROVED | No message queues |
| 11 | Background Processing | FastAPI BackgroundTasks + asyncio | ✅ APPROVED | No Celery needed |

**🔄 Major Architecture Update (2025-11-07):**
Decisions 3, 6, and 9 have been **significantly updated** to implement:
- Sequential OCR processing (user-controlled, 4 buttons)
- Integrated text + image processing (page-by-page)
- Comprehensive SVG generation for all images
- System-reserved attributes (1-7) for OCR results

See **[sequential-ocr-svg-processing.md](sequential-ocr-svg-processing.md)** for complete documentation.

---

## 🔍 Detailed Decisions

### **Decision 1: Interface Type - Localhost Web Application (FastAPI)** ✅

**Approved:** Yes (no modifications)

**Rationale:**
- Faster development time (weeks vs months)
- Cross-platform compatibility (Windows, Linux, macOS)
- Easier to maintain and update
- Modern responsive UI possible
- Desktop app deferred to future phase

**Technology:**
- FastAPI 0.104.1
- Uvicorn 0.24.0 (ASGI server)
- Port: 8000 (configurable)
- Access: http://localhost:8000

**Trade-offs:**
- ✅ Pros: Fast development, cross-platform, easy updates
- ⚠️ Cons: Browser required, not a native Windows app

---

### **Decision 2: Real-time Updates - WebSocket (5-second intervals)** ✅

**Approved:** Yes (MODIFIED from 2 seconds to 5 seconds)

**User Feedback:** "an update every 2 seconds is too much, wouldn't this be an overkill?"

**Final Configuration:**
- WebSocket connection for real-time updates
- Update frequency: Every 5 seconds
- Update data:
  - Current page number
  - Extracted records count
  - Current agent status
  - Processing percentage
  - ETA (estimated time remaining)

**Implementation:**
```python
@app.websocket("/ws/processing/{book_id}")
async def websocket_endpoint(websocket: WebSocket, book_id: int):
    await websocket.accept()
    while True:
        state = await get_processing_state(book_id)
        await websocket.send_json(state)
        await asyncio.sleep(5)  # 5-second intervals
```

**Benefits:**
- 60% reduction in database queries (vs 2s)
- Lower network traffic
- Still feels "real-time" to users
- Reduces server load

---

### **Decision 3: OCR Strategy - 3-Tier Quality-First Approach** ✅

**Approved:** Yes (COMPLETELY REDESIGNED with user specifications)

**User Requirements:**
- GPU acceleration (RTX 4070 Laptop, 8GB VRAM)
- Quality-first (not speed-first)
- Excellent Arabic + English support
- Cross-platform: Ubuntu development → Windows 11 deployment
- PaddleOCR as primary (user request)

**Final 3-Tier Strategy:**

#### **Tier 1: PaddleOCR (GPU, Primary)** 🚀
- Separate models for English and Arabic
- GPU acceleration (CUDA 11.8)
- Confidence threshold: 70%
- Speed: ~0.5-1s per page
- Model sizes: 8GB total (English + Arabic)

```python
# English OCR
paddle_ocr_en = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    use_gpu=True,
    gpu_mem=6000,
    det_db_thresh=0.3,
    rec_batch_num=8
)

# Arabic OCR
paddle_ocr_ar = PaddleOCR(
    use_angle_cls=True,
    lang='arabic',
    use_gpu=True,
    gpu_mem=2000,
    det_db_thresh=0.3,
    rec_batch_num=4
)
```

#### **Tier 2: Surya OCR (GPU, Fallback)** 🎯
- Triggered when PaddleOCR confidence < 70%
- GPU acceleration
- Better quality, slower (3-5s per page)
- Excellent multilingual support
- Confidence threshold: 65%

#### **Tier 3: Tesseract (CPU, Final Fallback)** 🛡️
- Triggered when Surya confidence < 65%
- CPU-based (no GPU required)
- Most stable fallback
- Slower but highly reliable

**Page Rendering:**
- PyMuPDF at 300 DPI for highest quality
- Preprocessing applied conditionally (see Decision 4)

**Documentation:**
- Complete setup guide: [ocr-setup.md](dependencies/ocr-setup.md)
- Includes Ubuntu and Windows 11 installation scripts
- CUDA 11.8 and cuDNN 8.9 setup instructions

---

### **Decision 4: Image Processing - Selective Preprocessing** ✅

**Approved:** Yes (Option A - Selective Preprocessing)

**Strategy:**

#### **Level 1: Always Applied (Fast, <0.5s per page)**
- DPI normalization to 300 DPI
- Grayscale conversion (if beneficial)

#### **Level 2: Conditional (Slower, 2-5s per page)**
Applied ONLY when:
- OCR confidence < 70% (automatic trigger)
- User enables "Force High-Quality Preprocessing" in upload settings

Operations:
- Denoising (Non-Local Means)
- Contrast enhancement (CLAHE)
- Deskewing (with RTL language support)
- Binarization (Otsu's method)

**Libraries:**
- **Pillow 10.1.0:** Basic operations (I/O, resize, rotate)
- **OpenCV 4.8.1:** Advanced operations (denoising, CLAHE, deskewing)

**Implementation:**
```python
async def preprocess_for_ocr(
    self,
    image: np.ndarray,
    confidence_score: Optional[float] = None,
    force_aggressive: bool = False,
    preserve_rtl: bool = True
) -> np.ndarray:
    # Level 1: Always
    processed = self._ensure_dpi(image, target_dpi=300)
    processed = self._convert_to_grayscale_if_needed(processed)

    # Level 2: Conditional
    needs_aggressive = (
        (confidence_score is not None and confidence_score < 70) or
        force_aggressive
    )

    if needs_aggressive:
        processed = self._denoise(processed)
        processed = self._enhance_contrast(processed)
        processed = self._deskew(processed, preserve_rtl=preserve_rtl)

    return processed
```

**Documentation:**
- Complete setup guide: [image-preprocessing-setup.md](dependencies/image-preprocessing-setup.md)

---

### **Decision 5: Semantic Splitting - sentence-transformers** ✅

**Approved:** Yes (quality-first approach)

**User Feedback:** "I focus on the quality first, much more than speed or light-weight so I approve decision 5"

**Technology:**
- **Library:** sentence-transformers 2.2.2
- **Model:** paraphrase-multilingual-mpnet-base-v2
- **Model Size:** ~420MB
- **Languages:** 50+ languages (including English and Arabic)

**Purpose:**
- Split text into 3-5 line semantic chunks
- Detect idea boundaries using AI
- Assign confidence scores to splits
- Respect paragraph boundaries

**Features:**
- Semantic similarity scoring
- Multi-language support
- Sentence boundary detection
- Confidence scoring (0-100%)

**Implementation:**
```python
from sentence_transformers import SentenceTransformer

class SemanticSplitter:
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

    async def split_text(self, text: str, language: str) -> List[KnowledgeUnit]:
        # Split into sentences
        sentences = self._split_sentences(text, language)

        # Compute embeddings
        embeddings = self.model.encode(sentences)

        # Find semantic boundaries
        chunks = self._find_boundaries(sentences, embeddings)

        return chunks
```

---

### **Decision 6: Image Analysis - Claude Sonnet 4.5 API** ✅

**Approved:** Yes (user specification)

**User Feedback:** "I want you to rely on claude code as I have a maximum subscription, and I want to rely on it, probably images/diagrams will be extracted in a file on the local system and then images will be sent one-by-one to Sonnet 4.5"

**Architecture:**
1. Extract image from PDF → save to PostgreSQL as BYTEA
2. Image-Reader Agent reads BYTEA → write to temporary file
3. Send temporary file to Claude Sonnet 4.5 API
4. Receive AI description + structured JSON
5. Update database record with description
6. Delete temporary file

**Why Claude Sonnet 4.5:**
- User has Claude Code Pro subscription
- Highest quality image understanding
- Excellent diagram, chart, and photo analysis
- Structured JSON output support
- Multi-language support (English + Arabic)

**API Integration:**
```python
import anthropic

class ImageAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def analyze_image(self, image_path: str) -> dict:
        # Send image to Claude API
        response = await self.client.messages.create(
            model="claude-sonnet-4.5-20250929",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "path",
                            "path": image_path
                        }
                    },
                    {
                        "type": "text",
                        "text": "Analyze this image and provide a description + structured JSON"
                    }
                ]
            }]
        )

        return {
            "description": response.content[0].text,
            "confidence": 95,
            "structured_json": {...}
        }
```

**Benefits:**
- Highest quality image analysis
- No local model training required
- Multi-language descriptions
- Structured output support

---

### **Decision 7: Database Access - SQLAlchemy ORM + Raw SQL Fallback** ✅

**Approved:** Yes (hybrid approach)

**User Question:** "can you please identify pros and cons compared to PostgreSQL?"

**Clarification Provided:** Decision 7 is about the ACCESS LAYER (how to interact with PostgreSQL), not the database choice itself. PostgreSQL was already selected in BA phase.

**Hybrid Approach:**

#### **Primary: SQLAlchemy ORM**
Used for:
- Simple CRUD operations
- Standard queries
- Relationships and joins
- Type safety

#### **Fallback: Raw SQL**
Used for:
- Complex queries (window functions, CTEs)
- Bulk operations
- Performance-critical queries
- pgvector operations

**Example:**
```python
from sqlalchemy.orm import Session
from sqlalchemy import text

class DatabaseService:
    def __init__(self, session: Session):
        self.session = session

    # ORM for simple operations
    def get_knowledge_unit(self, unit_id: int) -> KnowledgeUnit:
        return self.session.query(KnowledgeUnit).filter_by(id=unit_id).first()

    # Raw SQL for complex operations
    def find_similar_units(self, embedding: list, book_id: int) -> List[dict]:
        query = text("""
            SELECT id, text, 1 - (embedding <=> :embedding) AS similarity
            FROM book_knowledge_units
            WHERE book_id = :book_id
            ORDER BY embedding <=> :embedding
            LIMIT 10
        """)
        return self.session.execute(query, {
            "embedding": embedding,
            "book_id": book_id
        }).fetchall()
```

**Libraries:**
- SQLAlchemy 2.0.23 (ORM + Core)
- psycopg2-binary 2.9.9 (PostgreSQL driver)

---

### **Decision 8: Real-time Updates Implementation** ✅

**Approved:** Yes (same as Decision 2)

**User Question:** "sorry, where is decision 8?"

**Clarification:** Decision 8 (Real-time Updates Implementation) was already covered in Decision 2. The WebSocket implementation with 5-second intervals applies here.

**User Confirmation:** "for decision 8 it's ok, 5 seconds is good"

**Implementation Details:**
- WebSocket protocol (ws://)
- FastAPI WebSocket endpoint
- 5-second update intervals
- JSON message format
- Automatic reconnection on disconnect

**Message Format:**
```json
{
  "book_id": 1,
  "current_page": 142,
  "total_pages": 500,
  "extracted_count": 1847,
  "status": "processing",
  "current_agent": "splitter",
  "progress_percentage": 28.4,
  "eta_seconds": 1830
}
```

---

### **Decision 9: Image Storage - PostgreSQL BYTEA** ✅

**Approved:** Yes (after clarification)

**User Question:** "will it be possible to send the images 1-by-1 to claude code for analysis if we use PostgreSQL BYTEA"

**Answer:** Yes, absolutely! The workflow is:
1. Store image as BYTEA in PostgreSQL
2. Read BYTEA → write to temporary file
3. Send temporary file to Claude API
4. Update database with description
5. Delete temporary file

**Benefits of BYTEA Storage:**
- Database is source of truth (no orphaned files)
- Atomic transactions (image + metadata together)
- Easy retry on failures
- Crash recovery friendly
- Network deployment compatible (DB on separate machine)

**Schema:**
```sql
CREATE TABLE book1_mybook_images (
    id SERIAL PRIMARY KEY,
    image_id VARCHAR(50) UNIQUE NOT NULL,
    page_number INTEGER NOT NULL,
    image_data BYTEA NOT NULL,  -- Binary image data
    image_type VARCHAR(50),
    ai_description TEXT,
    structured_json JSONB,
    confidence_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Image Extraction Workflow:**
```python
async def analyze_image_with_claude(self, image_id: str):
    # Read from database
    result = await db.execute(
        "SELECT image_data FROM book1_mybook_images WHERE image_id = %s",
        (image_id,)
    )
    image_bytes = result[0][0]

    # Write to temp file
    temp_file = f"/tmp/img-{image_id}.png"
    with open(temp_file, 'wb') as f:
        f.write(image_bytes)

    # Analyze with Claude
    description = await claude_api.analyze(temp_file)

    # Update database
    await db.execute(
        "UPDATE book1_mybook_images SET ai_description = %s WHERE image_id = %s",
        (description, image_id)
    )

    # Cleanup
    os.remove(temp_file)
```

---

### **Decision 10: Agent Communication - Direct PostgreSQL Access** ✅

**Approved:** Yes (no modifications)

**Approach:** All agents (Reader, Splitter, Marker, Image-Reader) communicate via direct PostgreSQL database access.

**How It Works:**
1. Reader Agent writes OCR text to `book1_mybook_knowledge_units`
2. Splitter Agent reads unprocessed records, splits them, updates database
3. Marker Agent reads records, generates marked images, saves to `book1_mybook_pages`
4. Image-Reader Agent reads image records, analyzes with Claude API, updates descriptions

**No Message Queues Needed:**
- No Redis
- No RabbitMQ
- No Celery queues
- No additional infrastructure

**Benefits:**
- ✅ Simple architecture (fewer moving parts)
- ✅ PostgreSQL ACID guarantees (reliability)
- ✅ Easy debugging (just query database)
- ✅ Perfect for single-machine deployment
- ✅ No additional services to manage

**State Management:**
```sql
CREATE TABLE book1_mybook_processing_state (
    id SERIAL PRIMARY KEY,
    current_page INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,
    current_agent VARCHAR(50),
    status VARCHAR(20),  -- 'uploading', 'processing', 'paused', 'complete'
    last_updated TIMESTAMP DEFAULT NOW()
);
```

**Agent Coordination:**
- Agents check database for work
- Update state after each operation
- No complex message passing
- Simple polling (every 1 second during processing)

---

### **Decision 11: Background Processing - FastAPI BackgroundTasks + asyncio** ✅

**Approved:** Yes (no modifications)

**Approach:** Use FastAPI's built-in BackgroundTasks with asyncio for all background processing.

**Implementation:**
```python
from fastapi import BackgroundTasks

@app.post("/upload")
async def upload_book(file: UploadFile, background_tasks: BackgroundTasks):
    # Save file and create book record
    book_id = await save_book(file)

    # Start background processing
    background_tasks.add_task(process_book, book_id)

    return {"book_id": book_id, "status": "processing"}

async def process_book(book_id: int):
    try:
        # Run agents sequentially
        await reader_agent.process(book_id)
        await splitter_agent.process(book_id)
        await marker_agent.process(book_id)
        await image_reader_agent.process(book_id)

        # Mark complete
        await update_status(book_id, "complete")
    except Exception as e:
        await update_status(book_id, "error")
        await log_error(book_id, str(e))
```

**Pause/Resume Support:**
- Processing state saved to database every 5 seconds
- Resume from exact page (not last checkpoint)
- Survives application shutdown
- Database-driven (not in-memory)

**Checkpoint Strategy:**
```python
async def checkpoint(book_id: int, page_num: int):
    await db.execute("""
        UPDATE book_processing_state
        SET current_page = %s, last_checkpoint_page = %s, last_updated = NOW()
        WHERE book_id = %s
    """, (page_num, page_num, book_id))
```

**Benefits:**
- ✅ Built into FastAPI (no Celery overhead)
- ✅ Simple to implement and debug
- ✅ Works perfectly with pause/resume
- ✅ Async/await for efficient I/O
- ✅ No additional services to manage

**Trade-offs:**
- ⚠️ Not suitable for distributed systems (not needed here)
- ⚠️ Single machine only (acceptable for deployment)

---

## 🎯 Key User Modifications

1. **Decision 2:** Changed WebSocket interval from 2 seconds to 5 seconds (user request)
2. **Decision 3:** Completely redesigned OCR strategy to:
   - Use GPU acceleration (RTX 4070)
   - Prioritize quality over speed
   - Use PaddleOCR as primary (user request)
   - Add Surya OCR as fallback
   - Document cross-platform setup (Ubuntu dev → Windows 11 deployment)
3. **Decision 6:** Changed from local models to Claude Sonnet 4.5 API (user has Pro subscription)

---

## ✅ Next Steps

All architecture decisions are approved. The next phase is:

1. ✅ Document all decisions (this file)
2. 🔄 Complete system architecture diagram
3. 🔄 Design detailed database schema
4. 🔄 Break down implementation into code chunks
5. 🔄 Create dependency graph
6. 🔄 Prepare handoff to Tester Agent (test case generation)
7. 🔄 Prepare handoff to Developer Agent (chunk-by-chunk implementation)

---

## 📚 Related Documentation

- [Technology Stack](technology-stack.md) - Detailed library specifications
- [OCR Setup Guide](dependencies/ocr-setup.md) - Complete OCR installation
- [Image Preprocessing Setup](dependencies/image-preprocessing-setup.md) - Image processing guide
- [BA Handoff Manifest](../01-requirements/.handoff/ba-to-architect.json) - Requirements from BA phase

---

**Approval Date:** 2025-11-05
**Approved By:** User (one-by-one review)
**Status:** 100% APPROVED ✅
