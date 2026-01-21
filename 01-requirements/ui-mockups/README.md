# UI Mockups - Knowledge Extraction System

**Created:** 2025-11-03
**Business Analyst Phase** - Requirements Gathering
**Status:** Ready for Review

---

## 📋 Overview

This folder contains **5 comprehensive UI mockups** for the Knowledge Extraction System. These mockups are SVG-based HTML wireframes that demonstrate the complete user workflow from document upload through verification.

---

## 🎨 Mockup Files

### 1. **01-upload-page.html** - Upload & Configuration
**Purpose:** Initial document upload and processing settings

**Key Features:**
- **NEW:** Working file picker with drag & drop
- **NEW:** Accept ALL file types (not just PDF/Word) - agent will attempt to read any format
- **NEW:** Partial processing mode - process only first N pages (default 10) for testing
- **NEW:** Book-specific instructions text box - saved to DB and used only for this book
- Processing presets (Quick Scan, Balanced, Deep Analysis)
- Detailed settings configuration:
  - Language detection (Auto, English, Arabic, Both)
  - Extraction sensitivity
  - Image processing options
  - OCR quality settings
  - Hierarchy detection
- Save preferences option
- Estimated time/storage display

**User Flow:**
1. Upload document (any file type)
2. Optionally enable partial processing (first 10 pages)
3. Optionally add book-specific instructions
4. Choose preset or customize settings
5. Start processing

---

### 2. **02-processing-dashboard.html** - Real-Time Processing Monitor
**Purpose:** Show processing progress with agent activity

**Key Features:**
- Overall progress bar (page X of Y)
- Statistics cards:
  - Pages processed
  - Knowledge units extracted
  - Images analyzed
  - Low confidence flags
- Live agent status:
  - Reader Agent (reading + OCR)
  - Splitter Agent (semantic analysis)
  - Marker Agent (creating highlights)
  - Image-Reader Agent (analyzing images)
  - Database Writer (saving records)
- Real-time processing log
- Action buttons:
  - Continue in background
  - Pause
  - Stop & save progress

**User Flow:**
- Monitor real-time progress
- Option to leave and return
- Background processing support

**UPDATED VERSION:** [02-processing-dashboard-UPDATED.html](02-processing-dashboard-UPDATED.html)
- Added OCR Enhancement Agent showing retry logic with zoom
- Added checkpoint information (every 50 pages)
- Added Similarity Engine for post-processing
- Enhanced statistics to show OCR retries count
- **NEW:** Pause/Resume functionality with database persistence
- **NEW:** Processing survives system shutdown - can pause and resume anytime
- **NEW:** Interactive pause button that shows resume option
- **NEW:** "⚙️ Book Settings" button to access attribute name editing during processing

---

### 3. **03-verification-interface.html** - Main Verification (Split-Screen)
**Purpose:** Core verification interface for reviewing extracted knowledge units

**Key Features:**
- **Left Panel (50%):** Page image with green rectangle highlights
  - Zoom controls
  - Current extraction highlighted in green
  - Other extractions shown as dashed outlines
  - Page navigation
- **Right Panel (50%):** Knowledge unit details
  - Extracted text display
  - Verification checkbox
  - Hierarchy fields (Chapter/Topic/Sub-topic) with edit buttons
  - Core metadata (page, language, position, confidence)
  - 10 custom attributes (key-value pairs)
    - Attribute 1 reserved for image relationships
  - Notes/comments field
- **Fixed Navigation Bar (bottom):**
  - Record counter
  - Previous button
  - Next button
  - Approve & Next button

**User Flow:**
1. View page image with highlighted text
2. Review extracted text in right panel
3. Edit hierarchy if needed
4. Add/edit custom attributes
5. Mark as verified or skip to next
6. Navigate using Previous/Next/Approve & Next

**UPDATED VERSION:** [03-verification-interface-UPDATED.html](03-verification-interface-UPDATED.html)
- Added Merge Context section showing Previous/Current/Next records
- Added merge buttons to combine incorrectly split records
- Added low confidence warning indicators
- **REMOVED:** Cross-book similarity feature (deferred to future phase per user request)

---

### 4. **04-book-library.html** - Book Library Dashboard
**Purpose:** Manage all uploaded books and their status

**Key Features:**
- **Header Statistics:**
  - Total books
  - Total knowledge units
  - Total images
  - Verification percentage
- **Sidebar Navigation:**
  - All Books
  - Verified
  - Needs Review
  - Processing
  - Linked Content
  - Categories (ML, Programming, Data Science, etc.)
- **Search & Filter:**
  - Search box
  - Filter chips (All, English, Arabic, PDF, Word, Recently Added)
- **Book Cards (Grid):**
  - Book title and metadata
  - Statistics (knowledge units, images, verified %)
  - Progress bars
  - Language indicator
  - Status badges (Complete, In Review, Processing)
  - Action buttons (Verify, View, Pause, Monitor, Find Links)
- Upload new book button
- Pagination

**User Flow:**
1. View all books in library
2. Filter by language, type, or status
3. Click to verify or view book details
4. Monitor processing books
5. Upload new documents

---

### 5. **05-image-detail-view.html** - Image Analysis Detail
**Purpose:** Detailed view of analyzed images with AI descriptions

**Key Features:**
- **Left Section:**
  - Large image display
  - Metadata grid (ID, page, type, dimensions, size, confidence)
  - Action buttons (Edit, Link to Text, Download)
- **Right Section:**
  - **AI-Generated Description:**
    - Summary
    - Components identified (with structured breakdown)
    - Connections/relationships
    - Context
  - **Structured JSON Data:**
    - Machine-readable format
    - Component details
    - Image type classification
  - **Related Text Units:**
    - Links to knowledge units that reference this image
    - View/remove link options
  - **Tags:** User-defined tags for categorization
- Breadcrumb navigation

**User Flow:**
1. View image and AI description
2. Review structured data
3. Edit description if needed
4. Link to related text units
5. Add tags for organization

**UPDATED VERSION:** [05-image-detail-view-UPDATED.html](05-image-detail-view-UPDATED.html)
- **NEW:** Multi-page display showing original image page + linked text pages
- **NEW:** Color-coded markers:
  - Green rectangle = Original image location (Page 136)
  - Orange rectangles = Linked text locations (Pages 142, 144, etc.)
- **NEW:** Page preview grid (2 columns) showing all related pages
- **NEW:** Visual legend explaining green vs orange markers
- **NEW:** Each linked text shows page preview with orange highlight around the text

---

### 6. **06-book-settings.html** - Book Settings (Edit Attribute Names)
**Purpose:** Edit book-level attribute key names post-upload

**Key Features:**
- **Breadcrumb Navigation:** Back to Book Library
- **Book Information Bar:** Book name, ID, upload date, processing status
- **30 Attribute Name Fields:**
  - Attribute 1: System-defined "related_image" (locked with 🔒 icon)
  - Attributes 2-30: User-editable with pencil icon (✏️)
- **Editing Workflow:**
  - Click pencil icon to enable editing
  - Field highlights in orange when editable
  - Visual feedback for edited attributes
- **Action Buttons:**
  - Save Changes (only activates when edits are made)
  - Cancel (reverts all unsaved changes)
  - Back to Library
- **Floating Changes Indicator:** Shows count of modified attributes
- **Info Boxes:**
  - How-to instructions
  - Warning about database updates
- **Accessible From:**
  - Book Library: "⚙️ Settings" button on book cards
  - Processing Dashboard: "⚙️ Book Settings" button

**User Flow:**
1. Access from Book Library or Processing Dashboard
2. View current attribute names
3. Click pencil icon next to attribute name to edit
4. Modify attribute name
5. Save changes OR Cancel to revert
6. Changes reflected in verification interface immediately

---

## 🎯 Design Principles Applied

1. **Split-Screen Verification:** Left panel shows source, right panel shows extracted data
2. **Color Coding:**
   - Green: Verified/Active/Success
   - Orange: Processing/Warning
   - Blue: Information/Navigation
   - Red: Delete/Critical
   - Purple: Advanced features (linking)
3. **Multi-Day Workflow:** Verification status saved, can resume anytime
4. **Bilingual Support:** English and Arabic text examples
5. **Responsive Actions:** Clear next steps with prominent buttons
6. **Real-Time Feedback:** Progress indicators and status updates
7. **Editable Everything:** Users can modify hierarchy, attributes, descriptions
8. **Visual Verification:** See extracted text overlaid on original page

---

## 🔧 Technical Notes

- All mockups are standalone HTML files with embedded SVG graphics
- No external dependencies required
- Can be opened directly in any modern web browser
- Use monospace fonts for code/JSON displays
- Responsive grid layouts where applicable
- Simulated data for demonstration purposes

---

## 📝 Review Checklist

Please review each mockup and provide feedback on:

- [ ] **Layout & Navigation:** Is the information hierarchy clear?
- [ ] **Workflow Logic:** Do the flows make sense for your use case?
- [ ] **Feature Completeness:** Are all required features represented?
- [ ] **Visual Design:** Does the aesthetic meet your expectations?
- [ ] **Button Placement:** Are action buttons in logical locations?
- [ ] **Data Display:** Is metadata presented clearly?
- [ ] **Edit Capabilities:** Are all editable fields clearly marked?
- [ ] **Arabic Support:** Is RTL text support adequately shown?
- [ ] **Mobile Considerations:** Should we add mobile-specific views?
- [ ] **Missing Features:** What's missing from these mockups?

---

## 📞 Next Steps

After reviewing these mockups:

1. Provide feedback on each screen
2. Request modifications or additional screens
3. Confirm approval to reach 95% BA confidence
4. Proceed to Architecture phase

---

## 📂 File Structure

```
01-requirements/ui-mockups/
├── README.md (this file)
├── 01-upload-page.html (UPDATED - 30 attributes, file picker, all types, partial processing, instructions)
├── 02-processing-dashboard-UPDATED.html (OCR retry + checkpoints + pause/resume + Book Settings link)
├── 03-verification-interface-UPDATED.html (merge context, 30 attributes, removed cross-book similarity)
├── 04-book-library.html (Settings button on book cards)
├── 05-image-detail-view-UPDATED.html (multi-page display with color-coded markers)
└── 06-book-settings.html (NEW - Edit 30 attribute names with pencil icon workflow)
```

**Note:** Old mockup versions (02-processing-dashboard.html, 03-verification-interface.html, 05-image-detail-view.html) have been removed to keep the folder clean. Only UPDATED versions are retained.

---

**Created by:** Business Analyst Agent
**Session:** ses-20251103-025443
**Date:** 2025-11-03
