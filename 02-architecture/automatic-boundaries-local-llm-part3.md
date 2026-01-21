# Automatic Boundaries Implementation Requirements

## Document Purpose

This is the **primary requirements specification** for implementing automatic boundary detection using DocLayout-YOLO integrated with the Auto-Slicer feature. This document consolidates all requirements gathered through detailed Q&A sessions.

**Version:** 1.0
**Created:** January 2026
**Status:** APPROVED FOR IMPLEMENTATION

---

## EXECUTION ORDER - READ FIRST

```
┌─────────────────────────────────────────────────────────────────┐
│                    PREREQUISITE CHECK                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Before starting this implementation, verify:                    │
│                                                                  │
│  [?] Auto-Slicer Testing Complete                               │
│      └── See: 02-architecture/AUTO-SLICER-PROGRESS.md           │
│      └── 8 tests must pass                                       │
│                                                                  │
│  [?] Auto-Slicer Bugs Fixed                                     │
│      └── All issues from testing resolved                        │
│                                                                  │
│  [?] Auto-Slicer STABLE                                         │
│      └── Ready for enhancement                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

WHY THIS ORDER?
- This feature ENHANCES the Auto-Slicer page
- It USES Auto-Slicer's OCR pipeline (Surya at 600 DPI)
- It REUSES WebSocket, pause/resume, progress tracking
- Bugs in Auto-Slicer will CASCADE into this feature
```

### Related Documents

| Document | Purpose | Location |
|----------|---------|----------|
| Auto-Slicer Progress | Check prerequisite status | `02-architecture/AUTO-SLICER-PROGRESS.md` |
| Auto-Slicer Spec | Foundation feature spec | `02-architecture/AUTO-SLICER.md` |
| Research (Part 1) | Model analysis, hardware | `02-architecture/automatic-boundaries-local-llm.md` |
| Integration (Part 2) | FastAPI analysis, options | `02-architecture/automatic-boundaries-local-llm-part2.md` |
| **This Document** | **Full requirements** | `02-architecture/automatic-boundaries-local-llm-part3.md` |
| Progress Tracking | Implementation status | `02-architecture/AUTO-BOUNDARIES-PROGRESS.md` (create when starting) |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Workflow Specification](#workflow-specification)
4. [Region Detection Classes](#region-detection-classes)
5. [Fine-Tuning System](#fine-tuning-system)
6. [Model Management](#model-management)
7. [Review Interface Requirements](#review-interface-requirements)
8. [Title Detection & Mapping](#title-detection--mapping)
9. [Diagram-Paragraph Linking](#diagram-paragraph-linking)
10. [Confidence & Thresholds](#confidence--thresholds)
11. [Error Handling](#error-handling)
12. [Data Storage](#data-storage)
13. [Progress & Feedback](#progress--feedback)
14. [Export & Portability](#export--portability)
15. [Configuration Options](#configuration-options)
16. [API Endpoints](#api-endpoints)
17. [Database Schema](#database-schema)
18. [Implementation Phases](#implementation-phases)

---

## Executive Summary

### Approved Approach

**Option 1: Enhance Auto-Slicer with YOLO Detection**

The system will enhance the existing Auto-Slicer feature with DocLayout-YOLO-based automatic boundary detection, followed by Surya OCR at 600 DPI for text extraction.

### Core Workflow

```
Auto-Slicer Page
├── [1] Configure page range (existing)
├── [2] Click "Detect Layout" (NEW)
│       → YOLO processes pages → Unloads from GPU
├── [3] Review N pages with detected boxes
│       → Adjust/classify regions on canvas
├── [4] Click "Run Auto-Slicer" (existing)
│       → Surya OCR processes all pages
└── [5] Results saved to paragraph_images/diagram_images
```

### Key Decisions Summary

| Decision Area | Chosen Option |
|---------------|---------------|
| Model Inheritance | Allow selecting similar book's model as starting point |
| Diagram-Paragraph Linking | Reference detection (Figure 1, Table 2, etc.) |
| Review Mode | Configurable N pages OR review all in batches |
| Fine-Tuning Trigger | Manual with reminder after 25 corrections |
| Model Storage | Shared folder + DB reference |
| Workflow | Always separate steps (Detect → Review → OCR) |
| Training Mode | User choice + continue working during training |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTO-SLICER ENHANCED                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ 1. CONFIG    │───▶│ 2. DETECT    │───▶│ 3. REVIEW    │                  │
│  │ Page range   │    │ DocLayout-   │    │ N pages or   │                  │
│  │ Classes      │    │ YOLO         │    │ All batches  │                  │
│  │ Settings     │    │ (~4GB VRAM)  │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ 6. SAVE      │◀───│ 5. OCR       │◀───│ 4. CONFIRM   │                  │
│  │ paragraph_   │    │ Surya OCR    │    │ Apply        │                  │
│  │ images +     │    │ 600 DPI      │    │ corrections  │                  │
│  │ diagram_     │    │ (~2GB VRAM)  │    │              │                  │
│  │ images       │    │              │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FINE-TUNING SUBSYSTEM                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │ Collect     │─▶│ Remind at   │─▶│ Train       │─▶│ Deploy     │  │   │
│  │  │ Corrections │  │ 25 correct. │  │ (User init) │  │ New Model  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### GPU Memory Management

| Step | Model | VRAM | Status |
|------|-------|------|--------|
| Detection | DocLayout-YOLO | ~2-4 GB | Loaded → Process → Unloaded |
| OCR | Surya | ~2-3 GB | Loaded → Process → Unloaded |
| Training | DocLayout-YOLO | ~4-6 GB | Background (batch=4, amp=True) |

**Sequential Processing:** Only one model loaded at a time to fit 8GB VRAM.

---

## Workflow Specification

### Review Mode Options

Users can choose between two review modes:

#### Mode A: Review N Pages Then Auto-Process

```
┌─────────────────────────────────────────────────────────────────┐
│ User sets N = 10 (configurable 1-50)                            │
├─────────────────────────────────────────────────────────────────┤
│ [Detect Layout] → Process all pages                             │
│      │                                                          │
│      ▼                                                          │
│ [Review Pages 1-10] → User corrects boundaries                  │
│      │                                                          │
│      ▼                                                          │
│ [Auto-Process Pages 11-500] → Uses templates from corrections   │
│      │                                                          │
│      ▼                                                          │
│ [Run OCR] → Surya processes all regions                         │
└─────────────────────────────────────────────────────────────────┘
```

#### Mode B: Review All Pages in Batches

```
┌─────────────────────────────────────────────────────────────────┐
│ User sets batch size = 20 (configurable 5-50)                   │
├─────────────────────────────────────────────────────────────────┤
│ [Detect Layout] → Process all pages                             │
│      │                                                          │
│      ▼                                                          │
│ [Review Batch 1: Pages 1-20] → Correct → Confirm                │
│      │                                                          │
│      ▼                                                          │
│ [Review Batch 2: Pages 21-40] → Correct → Confirm               │
│      │                                                          │
│      ▼                                                          │
│ ... continue for all batches ...                                │
│      │                                                          │
│      ▼                                                          │
│ [Run OCR] → Surya processes all reviewed regions                │
└─────────────────────────────────────────────────────────────────┘
```

### Template Learning (Mode A)

When user corrects boundaries in N review pages, the system:

1. **Stores corrections as templates** with position/size patterns
2. **Matches similar layouts** in subsequent pages
3. **Applies same adjustments** automatically
4. **Marks auto-applied corrections** as "suggested" for verification
5. **Logs all auto-applications** for training data

---

## Region Detection Classes

### Core Classes

| Class ID | Class Name | Description | Default Enabled |
|----------|------------|-------------|-----------------|
| 0 | `title_level_1` | Main chapter/section titles | Yes |
| 1 | `title_level_2` | Sub-section titles | Yes |
| 2 | `title_level_3` | Sub-sub-section titles | Yes |
| 3 | `paragraph` | Text blocks | Yes |
| 4 | `diagram` | Images, charts, diagrams | Yes |
| 5 | `table` | Tabular data | Yes |
| 6 | `equation` | Mathematical formulas | Yes |
| 7 | `list_bulleted` | Bullet point lists | Yes |
| 8 | `list_numbered` | Numbered lists | Yes |
| 9 | `list_lettered` | Lettered lists (a, b, c) | Yes |
| 10 | `list_item` | Individual list item | Yes |
| 11 | `header` | Page header | Yes |
| 12 | `footer` | Page footer | Yes |
| 13 | `reference` | Bibliography/citation entries | Yes |
| 14 | `caption` | Figure/table captions | Yes |

### Book-Specific Class Configuration

Each book can enable/disable classes based on content type:

```json
{
  "book_id": 123,
  "enabled_classes": [
    "title_level_1", "title_level_2", "paragraph",
    "diagram", "table", "equation"
  ],
  "disabled_classes": [
    "title_level_3", "reference", "header", "footer"
  ]
}
```

### List Detection Behavior

Lists are detected at two levels:
1. **List container** - The entire list region
2. **List items** - Individual items within the list

```
┌─────────────────────────────┐
│ list_bulleted (container)   │
│ ┌─────────────────────────┐ │
│ │ list_item: • Item 1     │ │
│ ├─────────────────────────┤ │
│ │ list_item: • Item 2     │ │
│ ├─────────────────────────┤ │
│ │ list_item: • Item 3     │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### Header/Footer Processing Options

Configurable per book:

| Option | Behavior |
|--------|----------|
| `exclude` | Detect and mark as 'ignore', no OCR |
| `extract` | OCR and store in separate DB fields |
| `extract_with_page_numbers` | OCR + detect/extract page numbers |

### Table Structure Detection

Configurable per book (default: full extraction):

| Option | Behavior |
|--------|----------|
| `boundary_only` | Detect table as single region, store as image |
| `full_structure` | Detect rows, columns, cells + extract data (DEFAULT) |

### Equation Handling

Equations are processed as:
1. **Detected as diagram type** - Stored in diagram_images table
2. **Parallel extraction attempt** - Try to extract formula text
3. **Store in manual_text field** - Using existing extractor infrastructure
4. **LLM reading later** - Can be interpreted by Claude API

---

## Fine-Tuning System

### Per-Book Model Concept

Each book can have its own fine-tuned model optimized for its specific layout patterns:

```
Book A (Math Textbook)     → models/book_123_v1.pt
Book B (History Textbook)  → models/book_456_v2.pt
Book C (Technical Manual)  → models/book_789_v1.pt
```

### Model Inheritance

When starting a new book, user can:

1. **Start from base model** - DocLayout-YOLO pre-trained weights
2. **Inherit from similar book** - Select existing book's fine-tuned model

```
┌─────────────────────────────────────────────────────────────────┐
│ New Book Setup                                                   │
├─────────────────────────────────────────────────────────────────┤
│ Base Model:                                                      │
│ ○ DocLayout-YOLO (default pre-trained)                          │
│ ● Inherit from: [Book 123 - Math Textbook v2] ▼                 │
│                                                                  │
│ Similar books detected:                                          │
│   • Book 123 - Math Textbook (92% layout similarity)            │
│   • Book 456 - Physics Textbook (87% layout similarity)         │
└─────────────────────────────────────────────────────────────────┘
```

### Fine-Tuning Trigger

| Trigger | Behavior |
|---------|----------|
| **Manual** | User clicks "Train Model" button |
| **Reminder** | System shows notification after 25 corrections |
| **No auto-train** | Never trains automatically without user consent |

### Training Configuration

```python
# Optimized for RTX 4070 (8GB VRAM)
training_config = {
    "batch_size": 4,
    "image_size": 640,
    "epochs": 50,
    "amp": True,  # Mixed precision
    "patience": 10,  # Early stopping
    "lr0": 0.001,
    "workers": 4
}
```

### Training Metrics Tracking

After each training cycle, display:

| Metric | Description |
|--------|-------------|
| `mAP@0.5` | Mean Average Precision at IoU 0.5 |
| `mAP@0.5:0.95` | Mean AP across IoU thresholds |
| Per-class accuracy | Accuracy for each enabled class |
| Improvement % | Comparison with previous model version |
| Training loss curve | Visual graph of loss over epochs |

### Training Mode Options

User chooses per training session:

| Option | Behavior |
|--------|----------|
| **Run Now** | Train immediately, blocks ~30 min |
| **Schedule for Later** | Queue training for off-hours |

**During Training:** User can continue reviewing/correcting other pages of the book.

---

## Model Management

### Storage Structure

```
03-code/
├── models/
│   ├── base/
│   │   └── doclayout_yolo_docsynth300k.pt    # Base pre-trained model
│   ├── fine_tuned/
│   │   ├── book_123_v1.pt                     # Book 123, version 1
│   │   ├── book_123_v2.pt                     # Book 123, version 2
│   │   ├── book_456_v1.pt                     # Book 456, version 1
│   │   └── ...
│   └── exports/
│       └── book_123_export_2026-01-13.zip    # Exported packages
```

### Database Reference

```sql
-- Model metadata table
CREATE TABLE layout_models (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books_metadata(book_id),
    model_version INTEGER NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    parent_model_id INTEGER REFERENCES layout_models(id),  -- For inheritance
    base_model VARCHAR(100) DEFAULT 'doclayout_yolo_docsynth300k',

    -- Training metadata
    training_images INTEGER,
    training_corrections INTEGER,
    training_epochs INTEGER,
    training_duration_seconds INTEGER,

    -- Metrics
    map_score FLOAT,
    per_class_accuracy JSONB,
    improvement_percent FLOAT,

    -- Status
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(book_id, model_version)
);
```

---

## Review Interface Requirements

### Canvas Adjustment Tools

**Full editing suite with keyboard shortcuts:**

| Tool | Mouse Action | Keyboard Shortcut |
|------|--------------|-------------------|
| Select | Click region | - |
| Resize | Drag corners/edges | - |
| Move | Drag region | - |
| Delete | - | `D` or `Delete` |
| Merge | Select multiple | `M` |
| Split | - | `S` |
| Draw new | Click + drag | `N` |
| Copy to next page | - | `C` |
| Reclassify | - | `1-9` (class numbers) |
| Undo | - | `Ctrl+Z` |
| Redo | - | `Ctrl+Y` |
| Next page | - | `→` or `Page Down` |
| Previous page | - | `←` or `Page Up` |
| Accept page | - | `Enter` |

### Class Quick-Select Shortcuts

| Key | Class |
|-----|-------|
| `1` | title_level_1 |
| `2` | title_level_2 |
| `3` | title_level_3 |
| `4` | paragraph |
| `5` | diagram |
| `6` | table |
| `7` | equation |
| `8` | list (cycle types) |
| `9` | reference |
| `0` | header/footer |

### Region Overlap Handling

When regions overlap:

1. **Keep both with parent-child relationship**
   - Diagram can be child of paragraph (embedded image)
   - Paragraph CANNOT be child of diagram

2. **Flag for manual resolution** if relationship unclear

```
┌─────────────────────────────────────┐
│ paragraph (parent)                   │
│                                      │
│   ┌─────────────────┐               │
│   │ diagram (child) │               │
│   │                 │               │
│   └─────────────────┘               │
│                                      │
│ Text continues after diagram...      │
└─────────────────────────────────────┘
```

---

## Title Detection & Mapping

### Hybrid Title Detection

User can define titles at different levels:

| Level | Source | Example |
|-------|--------|---------|
| Level 1 | User-defined (existing Auto-Slicer) | "Chapter 5: Advanced Topics" |
| Level 2 | YOLO-detected + OCR | "5.1 Introduction" |
| Level 3 | YOLO-detected + OCR | "5.1.1 Background" |

### Title Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Title Detection Flow                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. User defines Level 1 titles (manual, existing feature)        │
│    └── "Chapter 1" covers pages 1-50                            │
│    └── "Chapter 2" covers pages 51-100                          │
│                                                                  │
│ 2. YOLO detects title_level_2 and title_level_3 regions         │
│    └── Page 15: Detected region at (100, 200, 400, 50)          │
│                                                                  │
│ 3. Surya OCR reads text from detected title regions              │
│    └── OCR result: "1.3 Data Structures"                        │
│                                                                  │
│ 4. System maps to knowledge_unit titles                          │
│    └── level_1_title: "Chapter 1" (user-defined)                │
│    └── level_2_title: "1.3 Data Structures" (YOLO+OCR)          │
│    └── level_3_title: NULL (not detected on this page)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Title Scope Propagation

When a Level 2 or Level 3 title is detected:
- It applies to all subsequent paragraphs
- Until a new title of same or higher level is detected
- Resets at Level 1 boundaries (chapter changes)

---

## Diagram-Paragraph Linking

### Reference Detection System

The system detects references in paragraph text to link diagrams:

#### Standard Patterns (Built-in)

| Language | Pattern | Matches |
|----------|---------|---------|
| English | `Figure \d+` | Figure 1, Figure 23 |
| English | `Fig\. \d+` | Fig. 1, Fig. 23 |
| English | `Table \d+` | Table 1, Table 5 |
| English | `Tab\. \d+` | Tab. 1, Tab. 5 |
| English | `Diagram \d+` | Diagram 1 |
| English | `Chart \d+` | Chart 1 |
| English | `Equation \d+` | Equation 1 |
| English | `Eq\. \d+` | Eq. 1 |
| Arabic | `شكل \d+` | شكل 1 (Figure 1) |
| Arabic | `جدول \d+` | جدول 1 (Table 1) |
| Arabic | `رسم \d+` | رسم 1 (Diagram 1) |
| Arabic | `معادلة \d+` | معادلة 1 (Equation 1) |

#### Custom Patterns (Per Book)

Users can add book-specific patterns:

```json
{
  "book_id": 123,
  "custom_reference_patterns": [
    {"pattern": "Exhibit [A-Z]", "type": "diagram"},
    {"pattern": "Chart \\d+-\\d+", "type": "diagram"},
    {"pattern": "Formula \\(\\d+\\)", "type": "equation"}
  ]
}
```

### Linking Process

```
┌─────────────────────────────────────────────────────────────────┐
│ Reference Linking Flow                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. OCR paragraph text                                            │
│    └── "As shown in Figure 3, the results indicate..."          │
│                                                                  │
│ 2. Extract references                                            │
│    └── Found: "Figure 3"                                        │
│                                                                  │
│ 3. Search for matching diagram label                             │
│    └── Look in same page diagrams for "Figure 3" caption        │
│                                                                  │
│ 4. If found: Create link                                         │
│    └── paragraph_id: 456 → diagram_id: 789                      │
│                                                                  │
│ 5. If NOT found: Flag as unlinked                               │
│    └── Add to review queue for manual resolution                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Unlinked References

When a reference is found but no matching diagram exists:
- **Flag as "unlinked"**
- **Show in review queue**
- **Manual resolution required**

---

## Confidence & Thresholds

### Adaptive Threshold System

The system learns optimal thresholds from user corrections over time:

```
┌─────────────────────────────────────────────────────────────────┐
│ Adaptive Threshold Learning                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Initial Thresholds (per class):                                  │
│ ┌─────────────────┬────────────┬────────────┬────────────┐      │
│ │ Class           │ Auto-Accept│ Review     │ Reject     │      │
│ ├─────────────────┼────────────┼────────────┼────────────┤      │
│ │ title_level_1   │ > 85%      │ 60-85%     │ < 60%      │      │
│ │ paragraph       │ > 80%      │ 55-80%     │ < 55%      │      │
│ │ diagram         │ > 85%      │ 60-85%     │ < 60%      │      │
│ │ table           │ > 80%      │ 55-80%     │ < 55%      │      │
│ └─────────────────┴────────────┴────────────┴────────────┘      │
│                                                                  │
│ After N corrections, system adjusts:                             │
│ - If user often accepts low-confidence detections → lower thresh │
│ - If user often rejects high-confidence detections → raise thresh│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Detection Failures

| Scenario | Behavior |
|----------|----------|
| No regions detected | Flag page for manual review |
| Low confidence (below reject threshold) | Skip region, flag page |
| VRAM error | Retry with batch=1, if fails flag page |
| Model load failure | Show error, allow retry or skip |

### Flagged Pages Queue

Pages flagged for review are stored in a queue:

```sql
-- Flagged pages table
CREATE TABLE layout_flagged_pages (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    flag_reason VARCHAR(100),  -- 'no_detection', 'low_confidence', 'error'
    flag_details JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Data Storage

### Dual Storage Strategy

Detection results are stored in two locations:

#### 1. Active Session (auto_slicer_config JSON)

```json
{
  "detection_results": {
    "page_1": {
      "regions": [
        {"class": "paragraph", "x": 100, "y": 200, "w": 400, "h": 150, "conf": 0.92},
        {"class": "diagram", "x": 100, "y": 400, "w": 300, "h": 200, "conf": 0.88}
      ],
      "status": "reviewed",
      "corrections_applied": 2
    }
  }
}
```

#### 2. Historical Tracking (layout_detections table)

```sql
-- Per-book layout detections table
CREATE TABLE raw_{table_prefix}_layout_detections (
    id SERIAL PRIMARY KEY,
    page_number INTEGER NOT NULL,

    -- Detection info
    class_name VARCHAR(50) NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    confidence FLOAT,

    -- Correction tracking
    original_x INTEGER,
    original_y INTEGER,
    original_width INTEGER,
    original_height INTEGER,
    original_class VARCHAR(50),
    was_corrected BOOLEAN DEFAULT FALSE,
    correction_type VARCHAR(20),  -- 'moved', 'resized', 'reclassified', 'deleted', 'added'

    -- Relationships
    parent_region_id INTEGER REFERENCES raw_{table_prefix}_layout_detections(id),
    linked_paragraph_id INTEGER,
    linked_diagram_id INTEGER,

    -- Metadata
    model_version INTEGER,
    detected_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    exported_for_training BOOLEAN DEFAULT FALSE
);
```

---

## Progress & Feedback

### WebSocket Progress Updates

During detection, show:

1. **Page progress:** "Processing page 45 of 500"
2. **Regions found:** "Detected 8 regions on page 45"
3. **Visual thumbnail:** Small preview of page with detected boxes

### Progress Message Format

```json
{
  "type": "detection_progress",
  "book_id": 123,
  "current_page": 45,
  "total_pages": 500,
  "regions_detected": 8,
  "thumbnail_base64": "data:image/png;base64,...",
  "classes_found": {
    "paragraph": 5,
    "diagram": 2,
    "title_level_2": 1
  },
  "elapsed_seconds": 23,
  "estimated_remaining_seconds": 234
}
```

---

## Export & Portability

### Full Export Package

Export includes:

```
book_123_export_2026-01-13.zip
├── model/
│   └── book_123_v2.pt                    # Fine-tuned model weights
├── training_data/
│   ├── images/
│   │   ├── page_001.png
│   │   └── ...
│   └── labels/
│       ├── page_001.txt                  # YOLO format labels
│       └── ...
├── corrections/
│   └── corrections.json                  # All user corrections
├── config/
│   ├── class_config.json                 # Enabled classes
│   ├── reference_patterns.json           # Custom patterns
│   └── thresholds.json                   # Learned thresholds
└── metadata.json                         # Export metadata
```

### Import Functionality

When importing:
1. **Validate package** - Check all required files present
2. **User confirmation** - Show what will be imported
3. **Merge or replace** - Option to merge with existing or replace
4. **Version control** - Create new version if model exists

---

## Configuration Options

### Book-Level Settings

```json
{
  "book_id": 123,
  "layout_detection_config": {
    // Review mode
    "review_mode": "n_pages",  // or "all_batches"
    "review_n_pages": 10,
    "batch_size": 20,

    // Classes
    "enabled_classes": ["paragraph", "diagram", "table", "title_level_1", "title_level_2"],

    // Language
    "primary_language": "arabic",  // or "english"

    // Headers/Footers
    "header_footer_mode": "extract_with_page_numbers",

    // Tables
    "table_extraction_mode": "full_structure",

    // Reference patterns
    "reference_patterns": {
      "use_standard": true,
      "custom_patterns": []
    },

    // Model
    "model_source": "inherit",  // or "base"
    "inherit_from_book_id": 456,

    // Training
    "training_reminder_threshold": 25
  }
}
```

---

## API Endpoints

### New Endpoints for Layout Detection

```python
# Detection endpoints
POST   /api/auto-slicer/{book_id}/detect-layout
GET    /api/auto-slicer/{book_id}/detection-status
GET    /api/auto-slicer/{book_id}/detected-regions
GET    /api/auto-slicer/{book_id}/detected-regions/{page_number}
POST   /api/auto-slicer/{book_id}/confirm-regions
DELETE /api/auto-slicer/{book_id}/detected-region/{region_id}
PUT    /api/auto-slicer/{book_id}/detected-region/{region_id}
POST   /api/auto-slicer/{book_id}/add-region

# Correction endpoints
POST   /api/layout-corrections/{book_id}/save
GET    /api/layout-corrections/{book_id}/list
GET    /api/layout-corrections/{book_id}/stats

# Model management endpoints
GET    /api/layout-models/{book_id}/list
GET    /api/layout-models/{book_id}/active
POST   /api/layout-models/{book_id}/train
GET    /api/layout-models/{book_id}/training-status
POST   /api/layout-models/{book_id}/activate/{version}
GET    /api/layout-models/available-for-inheritance

# Export/Import endpoints
GET    /api/layout-models/{book_id}/export
POST   /api/layout-models/import

# Reference linking endpoints
GET    /api/layout-references/{book_id}/unlinked
POST   /api/layout-references/{book_id}/link
GET    /api/layout-references/{book_id}/patterns
POST   /api/layout-references/{book_id}/patterns

# Flagged pages endpoints
GET    /api/layout-flagged/{book_id}/list
POST   /api/layout-flagged/{book_id}/resolve/{page_number}

# WebSocket
WS     /ws/layout-detection/{book_id}
WS     /ws/layout-training/{book_id}
```

---

## Database Schema

### New Tables Summary

| Table | Purpose |
|-------|---------|
| `layout_models` | Store model metadata and versions |
| `layout_detection_config` | Per-book configuration |
| `raw_{prefix}_layout_detections` | Detection results + corrections |
| `layout_flagged_pages` | Pages needing manual review |
| `layout_reference_patterns` | Custom reference patterns |
| `layout_reference_links` | Diagram-paragraph links |
| `layout_training_history` | Training run history |

### Migration Script Required

```python
# migrate_add_layout_detection.py
# Creates all new tables for layout detection feature
```

---

## Implementation Phases

### Phase 1: Core Detection (Priority: HIGH)

| Task | Effort | Description |
|------|--------|-------------|
| YOLO Service | 8h | Model loading, inference, unloading |
| Detection API | 8h | Endpoints for detect, status, regions |
| WebSocket Progress | 4h | Real-time progress updates |
| Basic Review UI | 12h | Canvas with detected boxes |
| Database Schema | 4h | Core tables + migration |

**Total Phase 1: ~36 hours**

### Phase 2: Review Interface (Priority: HIGH)

| Task | Effort | Description |
|------|--------|-------------|
| Canvas Editing | 16h | Resize, move, delete, add regions |
| Keyboard Shortcuts | 4h | All shortcuts implementation |
| Class Selection | 4h | Quick-select and reclassify |
| Batch Review Mode | 8h | Navigate through batches |
| Confirmation Flow | 4h | Accept page/batch workflow |

**Total Phase 2: ~36 hours**

### Phase 3: Fine-Tuning System (Priority: MEDIUM)

| Task | Effort | Description |
|------|--------|-------------|
| Correction Tracking | 8h | Store original + corrected |
| Training Export | 8h | Export to YOLO format |
| Training Script | 4h | Fine-tuning execution |
| Training UI | 8h | Progress, metrics display |
| Model Management | 8h | Versions, activation, inheritance |

**Total Phase 3: ~36 hours**

### Phase 4: Advanced Features (Priority: MEDIUM)

| Task | Effort | Description |
|------|--------|-------------|
| Reference Detection | 12h | Pattern matching, linking |
| Title Mapping | 8h | Hybrid detection + OCR |
| Template Learning | 12h | Apply corrections to similar pages |
| Adaptive Thresholds | 8h | Learn from corrections |
| Header/Footer Config | 4h | Configurable processing |

**Total Phase 4: ~44 hours**

### Phase 5: Export & Polish (Priority: LOW)

| Task | Effort | Description |
|------|--------|-------------|
| Full Export | 8h | Package model + data + config |
| Import | 8h | Validate and import packages |
| Metrics Dashboard | 8h | Detailed training metrics |
| Documentation | 4h | User guide, API docs |
| Testing | 12h | End-to-end testing |

**Total Phase 5: ~40 hours**

---

### Total Estimated Effort

| Phase | Hours | Priority |
|-------|-------|----------|
| Phase 1: Core Detection | 36h | HIGH |
| Phase 2: Review Interface | 36h | HIGH |
| Phase 3: Fine-Tuning | 36h | MEDIUM |
| Phase 4: Advanced Features | 44h | MEDIUM |
| Phase 5: Export & Polish | 40h | LOW |
| **Total** | **192 hours** | - |

---

## Appendix: Requirements Traceability

| Requirement ID | Description | Source |
|----------------|-------------|--------|
| REQ-001 | Sequential GPU processing (YOLO then Surya) | Part 1, Hardware |
| REQ-002 | Per-book fine-tuned models | User decision |
| REQ-003 | Model inheritance between books | Q&A Batch 1 |
| REQ-004 | Reference detection for diagram linking | Q&A Batch 1 |
| REQ-005 | Configurable N pages or all batches review | Q&A Batch 2 |
| REQ-006 | Manual training trigger with 25-correction reminder | Q&A Batch 2 |
| REQ-007 | Hybrid title detection (user L1, YOLO L2/L3) | Q&A Batch 3 |
| REQ-008 | Standard + custom reference patterns | Q&A Batch 3 |
| REQ-009 | Shared models folder + DB reference | Q&A Batch 4 |
| REQ-010 | Flag for manual review on failures | Q&A Batch 4 |
| REQ-011 | Book-specific class selection | Q&A Batch 5 |
| REQ-012 | Template learning from N-page corrections | Q&A Batch 5 |
| REQ-013 | Detailed training metrics (mAP, per-class) | Q&A Batch 6 |
| REQ-014 | Full list differentiation + items | Q&A Batch 7 |
| REQ-015 | Configurable header/footer processing | Q&A Batch 7 |
| REQ-016 | Equations as diagram + text extraction | Q&A Batch 8 |
| REQ-017 | Always separate steps workflow | Q&A Batch 8 |
| REQ-018 | Advanced canvas tools + keyboard shortcuts | Q&A Batch 9 |
| REQ-019 | Flag unlinked references | Q&A Batch 9 |
| REQ-020 | Adaptive confidence thresholds | Q&A Batch 10 |
| REQ-021 | Dual storage (config JSON + table) | Q&A Batch 10 |
| REQ-022 | User choice training mode + continue working | Q&A Batch 11 |
| REQ-023 | User specifies primary language | Q&A Batch 11 |
| REQ-024 | Detailed progress + visual preview | Q&A Batch 12 |
| REQ-025 | Full export portability | Q&A Batch 12 |
| REQ-026 | Configurable batch size for review all mode | Q&A Batch 13 |
| REQ-027 | Table full structure extraction (default) | Q&A Batch 13 |
| REQ-028 | Parent-child region overlap handling | Q&A Batch 13 |

---

**Document Version:** 1.0
**Last Updated:** January 2026
**Status:** APPROVED FOR IMPLEMENTATION
**Author:** Claude Code Analysis
