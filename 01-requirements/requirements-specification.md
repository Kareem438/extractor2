# Requirements Specification - Knowledge Extraction System

**Created:** 2025-11-03
**Business Analyst:** Claude (BA Agent)
**Session:** ses-20251103-025443
**Status:** ✅ Approved - 95% Confidence Achieved
**Version:** 1.0

---

## 📋 Executive Summary

The Knowledge Extraction System is a desktop application designed to extract, organize, and verify knowledge from documents (PDF, Word, webpages, and any file format). The system processes documents page-by-page using specialized AI agents, extracts semantic knowledge units (3-5 lines per unit), analyzes images, and stores all data in a networked database for verification and future cross-book linking.

**Key Users:** Content Creators and Analysts
**Primary Goal:** Extract and verify every piece of knowledge from books with visual verification
**Deployment:** Local desktop application with networked database (PostgreSQL + Chroma on separate Windows machine)

---

## 🎯 Functional Requirements

### FR-1: Document Upload & Configuration

**Priority:** Critical
**User Story:** As a Content Creator, I want to upload any type of document and configure processing settings so that the system can extract knowledge according to my preferences.

**Requirements:**
- FR-1.1: Accept ALL file types (PDF, Word, TXT, HTML, EPUB, images, etc.) - agent attempts to read any format
- FR-1.2: Provide drag-and-drop file upload interface
- FR-1.3: Offer processing presets: Quick Scan, Balanced, Deep Analysis
- FR-1.4: Allow partial processing mode (process only first N pages, default 10) for testing settings
- FR-1.5: Provide book-specific instructions text area saved to database and used only for that book
- FR-1.6: Configure language detection (Auto, English, Arabic, Both)
- FR-1.7: Configure extraction sensitivity (Conservative, Balanced, Aggressive)
- FR-1.8: Configure image processing (All Images, Diagrams/Charts Only, Skip Images)
- FR-1.9: Configure OCR quality (Fast, Balanced, High Quality)
- FR-1.10: Configure hierarchy detection (Auto-Detect, Manual Entry, Skip)
- FR-1.11: Save user preferences for future uploads
- FR-1.12: Display estimated processing time and storage requirements

**Acceptance Criteria:**
- ✅ User can upload any file type via drag-and-drop or file picker
- ✅ Partial processing checkbox limits to first N pages
- ✅ Book-specific instructions saved to `book{N}_{name}_settings` table
- ✅ All settings preserved in database for resume functionality

---

### FR-2: Multi-Agent Document Processing

**Priority:** Critical
**User Story:** As a Content Creator, I want the system to automatically process my document using specialized agents so that all text and images are extracted without manual intervention.

**Requirements:**
- FR-2.1: **Reader Agent** - Reads one page at a time, performs OCR on scanned content
  - Detect language (English/Arabic)
  - Extract raw text from page
  - Handle scanned PDFs with OCR (Tesseract or similar)
- FR-2.2: **Splitter Agent** - Splits text into semantic knowledge units
  - Extract 3-5 line chunks related to same idea
  - Respect paragraph boundaries
  - Split multi-idea paragraphs (each idea = 1+ sentences)
  - Use AI semantic analysis to detect boundaries
  - Assign confidence score to each extraction
- FR-2.3: **Marker Agent** - Creates visual markers on page images
  - Generate page image with green rectangles around extracted text
  - Generate page image with orange rectangles around linked text (for images)
  - Save marked images to database
- FR-2.4: **Image-Reader Agent** - Analyzes and describes images
  - Extract all images (diagrams, charts, photos, etc.)
  - Generate detailed AI description
  - Create structured JSON representation
  - Store both description and JSON in database

**Acceptance Criteria:**
- ✅ All four agents run in shared virtual environment
- ✅ Agents process pages sequentially (page-by-page)
- ✅ Each agent saves results to book-specific database tables
- ✅ Processing progress saved to `book{N}_{name}_processing_state` table

---

### FR-3: OCR Retry with Enhancement

**Priority:** High
**User Story:** As a Content Creator, I want the system to automatically retry failed OCR with enhanced quality so that low-quality scans are still readable.

**Requirements:**
- FR-3.1: Detect low-quality OCR results (low confidence score)
- FR-3.2: Implement 3-attempt retry strategy:
  - Attempt 1: Standard OCR
  - Attempt 2: Zoom to 200% + highest quality OCR
  - Attempt 3: Segment text regions individually + highest quality OCR
- FR-3.3: Log all retry attempts
- FR-3.4: Track OCR retry count per page in processing state
- FR-3.5: Display OCR retry statistics on processing dashboard

**Acceptance Criteria:**
- ✅ Failed OCR automatically triggers retry with zoom
- ✅ Maximum 3 attempts per page
- ✅ Processing dashboard shows "OCR Retries" count
- ✅ Retry details logged in processing log

---

### FR-4: Pause/Resume with Database Persistence

**Priority:** Critical
**User Story:** As a Content Creator, I want to pause processing and shut down my machine, then resume later from where I left off so that I don't lose progress.

**Requirements:**
- FR-4.1: Save processing progress to database continuously (not in-memory)
- FR-4.2: Checkpoint every 50 pages
- FR-4.3: Save current state:
  - Current page number
  - Agent states (which agents are active)
  - Extracted records count
  - Processing settings
- FR-4.4: Provide Pause button on processing dashboard
- FR-4.5: Provide Resume button when paused
- FR-4.6: Display pause warning explaining system can be shut down safely
- FR-4.7: Resume from exact page where paused (not from last checkpoint)

**Acceptance Criteria:**
- ✅ Pause button saves state to `book{N}_{name}_processing_state` table
- ✅ User can shut down machine after pause
- ✅ Resume button continues from exact page
- ✅ All progress survives machine shutdown

---

### FR-5: Split-Screen Verification Interface

**Priority:** Critical
**User Story:** As an Analyst, I want to verify extracted knowledge units with visual context so that I can confirm accuracy and fix errors.

**Requirements:**
- FR-5.1: **Left Panel (50% width):**
  - Display page image with green rectangle highlights around current extraction
  - Show previous/next extractions as dashed outlines
  - Provide zoom controls (+, -, reset, fit)
  - Show page number (X of Y)
- FR-5.2: **Right Panel (50% width):**
  - Display extracted text content (editable)
  - Show verification checkbox (Verified/Unverified status)
  - Show confidence score with warning if low (<70%)
  - Display document hierarchy (Chapter/Topic/Sub-topic) with edit buttons
  - Display core metadata (page, language, position, confidence)
  - Provide 10 custom attribute fields (key-value pairs, editable)
  - Show notes/comments field
- FR-5.3: **Fixed Navigation Bar (bottom):**
  - Record counter (Record X of Y)
  - Previous button
  - Next button
  - Approve & Next button (marks verified + moves to next)

**Acceptance Criteria:**
- ✅ Left panel shows page image with current extraction highlighted in green
- ✅ Right panel shows all editable fields
- ✅ Navigation buttons work correctly
- ✅ Approve & Next marks record as verified in database

---

### FR-6: Record Merging and Splitting

**Priority:** High
**User Story:** As an Analyst, I want to merge incorrectly split records or split records that contain multiple ideas so that each knowledge unit represents a single complete concept.

**Requirements:**

**Context View:**
- FR-6.1: Display 11 records in context view: 5 before + current + 5 after
- FR-6.2: Highlight current record with distinct visual styling
- FR-6.3: Show all 11 records simultaneously during verification

**Merging:**
- FR-6.4: Allow merging current record with up to 5 previous records (merge backward)
- FR-6.5: Allow merging current record with up to 5 following records (merge forward)
- FR-6.6: Merge buttons with dropdown to select count (1-5)
- FR-6.7: Merged records marked as "disabled" in Attribute 8 (record_status)
- FR-6.8: Target record receives concatenated text from all merged records
- FR-6.9: Source records store reference to target via merged_into_record_id
- FR-6.10: Target record stores list of original IDs in original_record_ids[]
- FR-6.11: Preserve all merged records in database (no deletion, just disable)

**Splitting:**
- FR-6.12: Allow user to split current record into multiple records
- FR-6.13: User defines split points within text
- FR-6.14: Create new records for each segment (all marked "enabled")
- FR-6.15: Track original record ID in original_record_ids[] for all split records

**System-Reserved Attribute 8:**
- FR-6.16: Attribute 8 is system-reserved for record_status
- FR-6.17: Default value: "enabled" for all new records
- FR-6.18: Value: "disabled" for records merged into another
- FR-6.19: Not editable by users

**Filtering:**
- FR-6.20: Toggle filter: Enabled Only / All Records / Disabled Only
- FR-6.21: Default verification view: Show enabled records only
- FR-6.22: Allow users to view disabled records to see merge history

**Undo Operations:**
- FR-6.23: Unmerge: Restore all merged records to "enabled" status
- FR-6.24: Unsplit: Delete split records, restore original record
- FR-6.25: Display undo buttons when merge/split history exists

**Acceptance Criteria:**
- ✅ Context view shows 5 before + current + 5 after (11 total)
- ✅ Merge backward and forward work correctly (up to 5 in each direction)
- ✅ Merged records marked as "disabled" in Attribute 8
- ✅ Target record stores original_record_ids array
- ✅ Source records reference target via merged_into_record_id
- ✅ Split creates multiple enabled records with original_record_ids tracking
- ✅ Filter toggle shows enabled/all/disabled records
- ✅ Undo merge and undo split restore original state
- ✅ Attribute 8 system-reserved and not editable
- ✅ Database indexes on attr8_value for fast filtering

---

### FR-7: Image Detail View with Multi-Page Markers

**Priority:** Medium
**User Story:** As an Analyst, I want to see which text units link to an image so that I understand the context and relationships.

**Requirements:**
- FR-7.1: Display large image with AI-generated description
- FR-7.2: Show structured JSON data
- FR-7.3: Display image metadata (ID, page, type, dimensions, size, confidence)
- FR-7.4: **Multi-page preview grid:**
  - Show original image page with GREEN rectangle around image
  - Show all linked text pages with ORANGE rectangles around linked text
  - Display 2-column grid layout
  - Include visual legend (Green = image, Orange = linked text)
- FR-7.5: Provide link/unlink buttons for text relationships
- FR-7.6: Allow editing of AI description
- FR-7.7: Support user-defined tags

**Acceptance Criteria:**
- ✅ Image detail shows original page + linked text pages
- ✅ Green rectangle marks image location
- ✅ Orange rectangles mark all linked text locations
- ✅ Legend clearly explains color coding

---

### FR-8: Book Library Dashboard

**Priority:** Medium
**User Story:** As a Content Creator, I want to see all my books and their processing status so that I can manage multiple documents.

**Requirements:**
- FR-8.1: Display header statistics (total books, knowledge units, images, verified %)
- FR-8.2: Sidebar navigation (All Books, Verified, Needs Review, Processing, Linked Content, Categories)
- FR-8.3: Search and filter (by language, type, status, recently added)
- FR-8.4: Book cards showing:
  - Title and metadata
  - Statistics (knowledge units, images, verified %)
  - Progress bars
  - Language indicator
  - Status badges (Complete, In Review, Processing)
  - Action buttons (Verify, View, Pause, Monitor, Find Links)
- FR-8.5: Upload new book button
- FR-8.6: Pagination

**Acceptance Criteria:**
- ✅ Dashboard shows all books from `books_metadata` table
- ✅ Filters work correctly
- ✅ Action buttons navigate to correct screens
- ✅ Statistics update in real-time

---

### FR-9: Database Structure with Book Prefixes

**Priority:** Critical
**User Story:** As a Developer, I want each book to have isolated database tables with clear naming so that data is organized and pause/resume works reliably.

**Requirements:**
- FR-9.1: **Table Naming Convention:** `book{N}_{sanitized_name}_{purpose}`
  - Examples: `book1_ml_fundamentals_knowledge_units`, `book2_deep_learning_python_images`
- FR-9.2: **Standard Tables per Book:**
  - `book{N}_{name}_knowledge_units` - Extracted text records
  - `book{N}_{name}_images` - Extracted images with AI descriptions
  - `book{N}_{name}_processing_state` - Current processing status and agent states
  - `book{N}_{name}_settings` - Book-specific instructions and configuration
  - `book{N}_{name}_pages` - Page images with green/orange rectangle markers
  - `book{N}_{name}_hierarchy` - Chapter/topic/sub-topic structure
- FR-9.3: **Shared Metadata Table:** `books_metadata`
  - Tracks all books with book_id, original filename, sanitized name, table prefix, upload date, file type, total pages, processing status, language
- FR-9.4: **Database Location:** Separate Windows machine on same network
  - PostgreSQL with pgvector extension (main relational database)
  - Chroma (vector database for similarity search)
- FR-9.5: **Book Number Assignment:**
  - Sequential integers (1, 2, 3, ...)
  - Never reuse book numbers (even if book deleted)
  - Assigned when user clicks "Start Processing"

**Acceptance Criteria:**
- ✅ All tables follow naming convention
- ✅ Book numbers never reused
- ✅ Database accessible from processing VM over network
- ✅ All CRUD operations work on networked database

---

### FR-10: Hierarchy Detection & Editing

**Priority:** Medium
**User Story:** As an Analyst, I want the system to auto-detect document hierarchy and allow me to edit it so that knowledge units are properly organized.

**Requirements:**
- FR-10.1: Auto-detect chapter/topic/sub-topic from headers and table of contents
- FR-10.2: Store hierarchy in `book{N}_{name}_hierarchy` table
- FR-10.3: Associate each knowledge unit with hierarchy levels
- FR-10.4: Provide edit buttons for each hierarchy level in verification interface
- FR-10.5: Allow manual override of detected hierarchy

**Acceptance Criteria:**
- ✅ Hierarchy auto-detected during processing
- ✅ Each knowledge unit linked to chapter/topic/sub-topic
- ✅ Users can edit hierarchy from verification interface
- ✅ Changes saved to database

---

### FR-11: Custom Attributes (40 per Record with Book-Level Key Names)

**Priority:** High
**User Story:** As an Analyst, I want to add custom metadata to knowledge units with pre-defined attribute names so that I can categorize and tag content consistently across the entire book.

**Requirements:**
- FR-11.1: Provide **40 custom attribute fields** per knowledge unit (increased from 30)
- FR-11.2: **Book-level attribute key names configuration:**
  - User defines attribute key names (1-40) at book upload time
  - Key names stored in `book{N}_{name}_attribute_keys` table
  - Database records store only VALUES (not keys)
  - Example: If user sets key3="Author Opinion", records store only the value in attr3_value column
- FR-11.3: **Attributes 1-8 reserved for system use:**
  - Attribute 1: `related_image` - Image linking
  - Attributes 2-4: OCR text results (paddleocr, surya, tesseract)
  - Attributes 5-7: OCR confidence scores
  - Attribute 8: `record_status` - Record status (enabled/disabled for merge tracking)
  - All 8 are system-defined and not editable
- FR-11.4: **Upload page attribute configuration section:**
  - Display 40 text input fields for attribute key names
  - Pre-fill attributes 1-8 with system-reserved names (disabled/read-only)
  - Allow user to name attributes 9-40 (32 custom attributes, optional, can leave blank)
  - Common examples shown as placeholder text (e.g., "Difficulty Level", "Topic Category", "Importance", etc.)
  - Save key names to database before processing starts
- FR-11.5: **Verification interface displays key names:**
  - Show attribute key names (from book-level configuration) as labels
  - Display only configured attributes (hide unused attributes)
  - Allow editing of attribute VALUES only (keys are book-level, not per-record)
- FR-11.6: **Book Settings page for editing attribute key names:**
  - Accessible from two locations:
    - Book Library via "⚙️ Settings" button on each book card
    - Processing Dashboard via "⚙️ Book Settings" button in action buttons
  - Display all 40 attribute key names with edit capability
  - Pencil icon (✏️) next to each user-defined attribute name (9-40 only)
  - Attributes 1-8 shown as locked/disabled (system-reserved)
  - Click pencil to enable editing of attribute key name
  - Save button (only activated when edits are made)
  - Cancel button to revert all changes
  - Update `book{N}_{name}_attribute_keys` table on save
  - Changes reflected immediately in verification interface labels
- FR-11.7: Allow both Content Creator and Analyst to edit attribute VALUES
- FR-11.8: Each record has unique database ID

**Acceptance Criteria:**
- ✅ 40 attribute fields available per record
- ✅ Upload page shows 40 key name input fields
- ✅ Attributes 1-8 pre-filled with system-reserved names (read-only)
- ✅ Attributes 9-40 available for user definition (32 custom attributes)
- ✅ Key names saved to `book{N}_{name}_attribute_keys` table
- ✅ Knowledge units table stores only VALUES (attr1_value, attr2_value, ..., attr40_value)
- ✅ Verification interface shows configured key names as labels
- ✅ Unused attributes (blank key names) are hidden in verification UI
- ✅ Book Settings page accessible from Book Library with "⚙️ Settings" button
- ✅ Book Settings page accessible from Processing Dashboard with "⚙️ Book Settings" button
- ✅ Pencil icon next to user-defined attributes (9-40) enables editing
- ✅ System-reserved attributes (1-8) shown as locked
- ✅ Save button only activates when edits are made
- ✅ Cancel button reverts all unsaved changes
- ✅ Attribute key name changes persist to database and update verification interface
- ✅ All attribute values editable from verification interface
- ✅ Each record has unique ID in database

---

### FR-12: Virtual Environment & Dependencies

**Priority:** Critical
**User Story:** As a Developer, I want all agents to run in a shared virtual environment with proper dependency management so that installation is clean and reproducible.

**Requirements:**
- FR-12.1: Create single virtual environment for entire application
- FR-12.2: All agents (Reader, Splitter, Marker, Image-Reader) share same venv
- FR-12.3: Install dependencies automatically:
  - PDF processing (PyPDF2, pdfplumber, or similar)
  - Word processing (python-docx or similar)
  - OCR (Tesseract, pytesseract)
  - Image processing (Pillow, OpenCV)
  - AI/ML libraries (transformers, sentence-transformers for embeddings)
  - Web framework (Flask or FastAPI for web interface)
  - Database connectors (psycopg2 for PostgreSQL, chromadb)
- FR-12.4: Database located OUTSIDE virtual environment (on separate Windows machine)
- FR-12.5: Use requirements.txt for dependency tracking

**Acceptance Criteria:**
- ✅ Single venv contains all dependencies
- ✅ All agents run in same venv
- ✅ Database connection works over network
- ✅ requirements.txt created and maintained

---

### FR-13: Bilingual Support (English + Arabic)

**Priority:** High
**User Story:** As a Content Creator, I want to process books in both English and Arabic so that I can work with content in multiple languages.

**Requirements:**
- FR-13.1: Auto-detect language per page
- FR-13.2: Support English-only, Arabic-only, and mixed-language documents
- FR-13.3: Handle right-to-left (RTL) text for Arabic
- FR-13.4: Use appropriate OCR models for each language
- FR-13.5: Display language indicator in verification interface
- FR-13.6: Store language metadata per knowledge unit

**Acceptance Criteria:**
- ✅ System correctly detects English and Arabic
- ✅ Arabic text displays correctly (RTL)
- ✅ OCR works for both languages
- ✅ Language stored in database per record

---

### FR-14: Cross-Book Similarity (DEFERRED TO FUTURE PHASE)

**Priority:** Low (Future Phase)
**User Story:** As an Analyst, I want to find similar text across different books so that I can link related concepts.

**Requirements:**
- FR-14.1: **DEFERRED** - Not implemented in initial version
- FR-14.2: Future implementation will include:
  - Auto-suggest similar text (70-90% threshold)
  - AI-generated similarity reasons
  - Manual linking capability
  - Store similarity scores and reasons

**Acceptance Criteria:**
- ✅ Feature explicitly deferred to future phase
- ✅ Database schema designed to support future implementation
- ✅ Chroma vector database prepared for embeddings

---

## 🔧 Non-Functional Requirements

### NFR-1: Performance

- NFR-1.1: Process 200-500 page documents within reasonable time (quality over speed)
- NFR-1.2: Handle documents up to 500MB file size
- NFR-1.3: Checkpoint every 50 pages (max 2-minute checkpoint overhead)
- NFR-1.4: Real-time progress updates every 2 seconds on dashboard
- NFR-1.5: Database queries respond within 1 second for verification interface

### NFR-2: Reliability

- NFR-2.1: No data loss on application crash (continuous database persistence)
- NFR-2.2: No data loss on system shutdown (pause/resume capability)
- NFR-2.3: Automatic OCR retry on failures (max 3 attempts)
- NFR-2.4: Processing state saved every 50 pages minimum

### NFR-3: Usability

- NFR-3.1: Desktop application (preferred) or localhost web interface (acceptable)
- NFR-3.2: Single-user deployment (no multi-user authentication required)
- NFR-3.3: Intuitive split-screen verification interface
- NFR-3.4: Clear visual feedback (green/orange color coding)
- NFR-3.5: Processing can continue in background

### NFR-4: Scalability

- NFR-4.1: Support unlimited number of books
- NFR-4.2: Support documents up to 1000 pages
- NFR-4.3: Database on separate machine allows future scaling
- NFR-4.4: Isolated tables per book prevent cross-contamination

### NFR-5: Security

- NFR-5.1: Local desktop deployment (no internet exposure)
- NFR-5.2: Network database connection secured (same local network)
- NFR-5.3: No sensitive data stored in application code

### NFR-6: Maintainability

- NFR-6.1: Code follows PEP8 standards (Python)
- NFR-6.2: SOLID principles applied
- NFR-6.3: Simplicity-first architecture (minimal libraries)
- NFR-6.4: Standard library preferred over third-party when possible
- NFR-6.5: Virtual environment for clean dependency management

---

## 👥 User Personas

### Persona 1: Content Creator
- **Role:** Uploads and processes documents
- **Goals:** Extract all knowledge from books efficiently
- **Pain Points:** Manual extraction is time-consuming
- **Needs:**
  - Easy file upload (any format)
  - Configurable processing settings
  - Reliable pause/resume
  - Book-specific instructions
  - Partial processing for testing

### Persona 2: Analyst
- **Role:** Verifies and enriches extracted knowledge
- **Goals:** Ensure accuracy, add metadata, fix errors
- **Pain Points:** Need visual context to verify extractions
- **Needs:**
  - Split-screen verification interface
  - Ability to merge incorrect splits
  - Edit hierarchy and attributes
  - Multi-day workflow support
  - Clear visual markers

---

## 📊 System Constraints

1. **Single-user deployment:** No multi-user support required
2. **Network database:** Database must be accessible from processing VM
3. **Storage:** No limit on storage requirements
4. **Quality over speed:** Processing time not critical
5. **Desktop preference:** Desktop app preferred if development time allows
6. **Virtual environment:** All Python dependencies in single venv
7. **Book-specific tables:** Each book gets isolated tables with `book{N}_` prefix

---

## ✅ Acceptance Criteria Summary

**Business Analyst Confidence Level:** 95%

**Requirements Validation:**
- ✅ All 14 functional requirements documented
- ✅ All 6 non-functional requirements documented
- ✅ 2 user personas defined
- ✅ 7 system constraints identified
- ✅ 5 UI mockups created and approved
- ✅ Database naming convention documented
- ✅ All user questions answered (12 questions in 4 batches + 5 clarifying questions)
- ✅ Cross-book similarity deferred to future phase (per user request)

**Ready for Architecture Phase:** ✅ YES

---

## 📎 Related Documents

- [UI Mockups](ui-mockups/) - 5 comprehensive HTML/SVG wireframes
- [Database Naming Convention](database-naming-convention.md) - Table naming rules
- User Stories & Acceptance Criteria (to be created)
- BA→Architect Handoff Manifest (to be created)

---

**Approved by:** User
**Date:** 2025-11-03
**Next Phase:** Architecture & Design
