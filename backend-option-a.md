# Backend Worker System - Option A (PostgreSQL-Based)

**Document Version:** 1.0
**Created:** 2025-12-30
**Status:** Requirements Gathering Complete ✅
**Confidence Level:** 95% ✅

---

## 1. Executive Summary

This document outlines the requirements and design for a standalone backend worker system that:
- Runs independently of the FastAPI server
- Executes sequential processing tasks after OCR confirmation
- Interacts with Claude API for text enrichment
- Reads/writes to PostgreSQL and ChromaDB
- Uses PostgreSQL as the single source of truth for task queue and state

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL Database                          │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  task_queue     │  │  claude_prompts │  │  knowledge_units    │  │
│  │  (per book)     │  │  (per book)     │  │  (existing)         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
│                                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │  FastAPI    │  │   Worker    │  │  ChromaDB   │
     │  Server     │  │   Process   │  │             │
     │  (may be    │  │  (always    │  │             │
     │   down)     │  │   running)  │  │             │
     └─────────────┘  └─────────────┘  └─────────────┘
```

---

## 3. Frontend Requirements

### 3.1 New Page: Claude Prompt Configuration

A new frontend page for configuring Claude API prompts per book.

#### 3.1.1 Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Claude Prompt Configuration                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Selected Book: [Dropdown: Book 1 - Wessam Explanation 2026    ▼]   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │ Step 1: [Step Name Input]                                   [Delete] ││
│  ├─────────────────┬───────────────┬───────────────┬────────────────────┤│
│  │ Prompt          │ Output Field  │ Applies To    │                    ││
│  ├─────────────────┼───────────────┼───────────────┼────────────────────┤│
│  │ [Multi-line     │ [Dropdown:    │ [Dropdown:    │                    ││
│  │  textarea with  │  - attr10     │  - Paragraphs │                    ││
│  │  template vars  │  - attr11     │    (default)  │                    ││
│  │  like           │  - attr12     │  - Diagrams   │                    ││
│  │  {{text}} ]     │  - ...]       │  - Both   ]   │                    ││
│  └─────────────────┴───────────────┴───────────────┴────────────────────┘│
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │ Step 2: [Step Name Input]                                   [Delete] ││
│  ├─────────────────┬───────────────┬───────────────┬────────────────────┤│
│  │ ...             │ ...           │ ...           │                    ││
│  └─────────────────┴───────────────┴───────────────┴────────────────────┘│
│                                                                      │
│  [+ Add New Step]                                                    │
│                                                                      │
│  [Save Configuration]  [Run Pipeline]  [View Status]                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 Column Specifications (Updated - 6 Columns)

| Column | Type | Description |
|--------|------|-------------|
| Step Name | Text input | Descriptive name for this step (e.g., "Summarize Text") |
| Prompt | Multi-line textarea | Prompt template with variables like `{{text_content}}` |
| Input Source | Dropdown | "PostgreSQL" or "ChromaDB" - where to read data from |
| Output Destination | Dropdown | "PostgreSQL" or "ChromaDB" - where to write result |
| Claude Model | Dropdown | "Sonnet 4" (default), "Opus 4.5", or "Haiku" |
| Applies To | Dropdown | "Paragraphs" (default), "Diagrams", or "Both" |

#### 3.1.2.1 Updated Page Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Claude Pipeline Configuration                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Selected Book: [Dropdown: Book 1 - Wessam Explanation 2026    ▼]           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Available Template Variables: (see reference table below)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: [Summarize Paragraph________________________]            [Delete]  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┬────────────┐ │
│  │ Prompt       │ Input Source │ Output Dest  │ Model        │ Applies To │ │
│  ├──────────────┼──────────────┼──────────────┼──────────────┼────────────┤ │
│  │ [Summarize   │ [PostgreSQL▼]│ [PostgreSQL▼]│ [Sonnet 4 ▼] │[Paragraphs]│ │
│  │  the text:   │              │              │              │            │ │
│  │  {{text}}    │ Field:       │ Field:       │              │            │ │
│  │  in Arabic]  │ [text_content│ [attr10_value│              │            │ │
│  │              │           ▼] │           ▼] │              │            │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┴────────────┘ │
│                                                                              │
│  Step 2: [Semantic Embedding________________________]             [Delete]  │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┬────────────┐ │
│  │ Prompt       │ Input Source │ Output Dest  │ Model        │ Applies To │ │
│  ├──────────────┼──────────────┼──────────────┼──────────────┼────────────┤ │
│  │ [N/A - No    │ [PostgreSQL▼]│ [ChromaDB ▼] │ [N/A - No    │[Both     ▼]│ │
│  │  Claude call │              │              │  Claude]     │            │ │
│  │  for embed]  │ Field:       │ Operation:   │              │            │ │
│  │              │ [attr10_value│ [Upsert      │              │            │ │
│  │              │           ▼] │  Embedding ▼]│              │            │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┴────────────┘ │
│                                                                              │
│  [+ Add New Step]                                                           │
│                                                                              │
│  [Save Configuration]                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2.1 Processing Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MERGE/SPLIT PAGE                                │
│                                                                      │
│  User reviews paragraphs/diagrams                                   │
│            │                                                         │
│            ▼                                                         │
│  User merges/splits as needed                                       │
│            │                                                         │
│            ▼                                                         │
│  User clicks "Confirm" on each paragraph/diagram                    │
│            │                                                         │
│            ▼                                                         │
│  [Execute Pipeline] button → Processes only CONFIRMED records       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.1.3 Template Variable Reference (Displayed at Top of Page)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Available Template Variables for Book: "Wessam Explanation 2026"   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Original Name      │ User-Defined Name    │ Usage in Prompt         │
│  ─────────────────────────────────────────────────────────────────  │
│  text_content       │ paragraph_text       │ {{paragraph_text}}      │
│  attr2_value        │ easyocr_result       │ {{easyocr_result}}      │
│  attr3_value        │ surya_result         │ {{surya_result}}        │
│  attr10_value       │ enriched_summary     │ {{enriched_summary}}    │
│  ...                │ ...                  │ ...                     │
│                                                                      │
│  Note: Both {{attr2_value}} and {{easyocr_result}} are valid        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.1.4 Processing Entities

The pipeline processes TWO types of entities:
1. **Paragraphs** - From `raw_{prefix}_paragraph_images` table
2. **Diagrams** - From `raw_{prefix}_diagram_images` table

Pipeline runs AFTER merge/split operations are complete.

#### 3.1.5 Trigger Location

Two "Execute Pipeline" buttons on the **confirmation/merge-split page**:
- **"Execute Pipeline (Paragraphs)"** - Processes all confirmed paragraphs
- **"Execute Pipeline (Diagrams)"** - Processes all confirmed diagrams

---

## 3.2 ChromaDB Operations Reference

When a pipeline step uses ChromaDB as input or output, the following operations are available:

### 3.2.1 ChromaDB as INPUT Source

| Operation | Description | Returns |
|-----------|-------------|---------|
| **Get Embedding** | Retrieve the embedding vector for this record | 384-dim vector |
| **Semantic Search** | Find similar records to the current one | List of similar record IDs + scores |
| **Get Similar Text** | Get the text content of N most similar records | Concatenated text from similar records |
| **Get Metadata** | Retrieve stored metadata for this record | JSON metadata object |

**Use Case Example:**
```
Step: "Find Related Content"
- Input: ChromaDB → Semantic Search (top 5 similar)
- Prompt: "Given this paragraph: {{text_content}} and these related paragraphs: {{similar_texts}}, identify common themes."
- Output: PostgreSQL → attr12_value
```

### 3.2.2 ChromaDB as OUTPUT Destination

| Operation | Description | Input Required |
|-----------|-------------|----------------|
| **Upsert Embedding** | Generate and store embedding for text | Text from PostgreSQL field |
| **Update Metadata** | Update metadata fields in ChromaDB | Key-value pairs |
| **Delete Entry** | Remove this record from ChromaDB | Record ID |
| **Add with Custom Text** | Store Claude's response as embedded text | Claude's response |

**Use Case Example:**
```
Step: "Generate Searchable Summary"
- Input: PostgreSQL → text_content
- Prompt: "Summarize this text for semantic search: {{text_content}}"
- Output: ChromaDB → Add with Custom Text (Claude's summary gets embedded)
```

### 3.2.3 Combined PostgreSQL + ChromaDB Steps

Some steps may need to write to BOTH databases:

| Pattern | Description |
|---------|-------------|
| **Enrich + Embed** | Claude enriches text → Save to PostgreSQL AND embed in ChromaDB |
| **Search + Analyze** | Read from ChromaDB (similar) → Claude analyzes → Save to PostgreSQL |
| **Sync** | Read from PostgreSQL → Update ChromaDB embedding |

### 3.2.4 Steps That Don't Need Claude

Some pipeline steps don't require Claude API calls:

| Step Type | Description |
|-----------|-------------|
| **Embedding Sync** | Just generate embedding from PostgreSQL text → ChromaDB |
| **Metadata Sync** | Copy metadata fields from PostgreSQL → ChromaDB |
| **Search Index** | Trigger re-indexing in ChromaDB |

For these steps, the "Prompt" field can be left empty or marked as "N/A", and "Model" dropdown shows "None (No API Call)".

---

## 4. Database Design

### 4.1 Table Strategy Decision

**Decision: Per-Book Tables (User Preference)**

Rationale:
- Consistent with existing architecture (knowledge_units, pages, etc. are per-book)
- Complete isolation between books
- Can drop all book data cleanly
- No risk of cross-book data contamination

New tables to create per book:
- `{prefix}_claude_prompts` - Prompt configuration for this book
- `{prefix}_task_queue` - Task queue for this book

---

## 5. Questions and Answers Log

### Batch 1 (2025-12-30)

**Q1: At what granularity should Claude API be called for each step?**

Options:
- A) Once per Knowledge Unit
- B) Once per Page
- C) Once per Book
- D) User-configurable per Step

**A1:** The granularity is on every **paragraph** AND on every **diagram** (two separate entity types). The backend must be executed AFTER paragraphs are merged or split. A button labeled "Execute Pipeline" will trigger this.

**Q2: Can a single prompt step use multiple input DB fields, or only one?**

Options:
- A) Single input field only
- B) Multiple input fields
- C) Multiple inputs with template variables

**A2:** Option C - Multiple inputs with template variables. Requirements:
- Template names displayed at top of page
- Can use user-defined column names (from book settings) OR original column names (attr2_value)
- System must accept BOTH naming conventions
- System must correctly substitute values before sending to Claude

**Q3: How should the pipeline be triggered to start processing?**

Options:
- A) Manual button only
- B) Automatic after OCR
- C) Both options

**A3:** Manual button labeled "Execute Pipeline" on the page that allows merge/split paragraphs. Pipeline executes at paragraph or diagram level.

### Batch 2 (2025-12-30)

**Q4: Should paragraphs and diagrams share the same prompt configuration, or have separate configurations?**

Options:
- A) Same prompts for both
- B) Separate prompts
- C) Shared + Entity-specific

**A4:** Option C - Each prompt step has a **4th column** specifying the entity type:
- Paragraphs only (DEFAULT selection)
- Diagrams only
- Both paragraphs and diagrams

**Q5: When 'Execute Pipeline' is clicked, which records should be processed?**

Options:
- A) All paragraphs and diagrams
- B) Only unprocessed records
- C) User-selected records
- D) Configurable filter

**A5:** Only **CONFIRMED** paragraphs/diagrams are processed. The confirmation happens on the merge/split page. User confirms each paragraph/diagram, and once confirmed, the pipeline executes for that specific record.

**Q6: If pipeline processing fails mid-way, what should happen on retry?**

Options:
- A) Resume from failure point
- B) Restart from beginning
- C) User chooses on retry
- D) Retry only failed record

**A6:** Option A - **Resume from failure point**. Skip already-processed records and continue from where it failed.

### Batch 3 (2025-12-30)

**Q7: When a paragraph/diagram is confirmed, should the pipeline execute immediately or wait for explicit button?**

Options:
- A) Immediate on confirm
- B) Batch on button click
- C) Configurable per book

**A7:** Two separate "Execute Pipeline" buttons on the confirmation page:
- One button for paragraphs
- One button for diagrams

**NEW REQUIREMENT:** Each pipeline step row should have:
- **Input DB source**: Can be PostgreSQL OR ChromaDB
- **Output DB destination**: Can be PostgreSQL OR ChromaDB
- User needs help understanding what ChromaDB operations can be included

**Q8: Which Claude model should be used for the API calls?**

Options:
- A) Claude Sonnet 4 (balanced)
- B) Claude Opus 4.5 (highest quality)
- C) Claude Haiku (fastest/cheapest)
- D) User-configurable per step

**A8:** Option D - **User-configurable per step**. Add a column to select the Claude model for each step.

**Q9: Should the pipeline steps execute in strict sequential order, or can some steps run in parallel?**

Options:
- A) Strict sequential
- B) Parallel per record
- C) Fully parallel
- D) Sequential per record

**A9:** Option B - **Parallel per record**. For each record, steps run sequentially. But different records can be processed in parallel by the worker.

### Batch 4 (2025-12-30)

**Q10: For ChromaDB output, should a step be able to write to BOTH PostgreSQL AND ChromaDB simultaneously?**

Options:
- A) Single output only
- B) Allow dual output
- C) Configurable checkboxes

**A10:** Option A - **Single output only**. Each step writes to either PostgreSQL OR ChromaDB. Use two separate steps if both are needed.

**NEW REQUIREMENT:** Add a checkbox/option to execute ALL unprocessed records as a batch. This is useful for:
- Newly created steps that need to run on all existing records
- Re-processing after step configuration changes

**Q11: When using ChromaDB 'Semantic Search' as input, how should similar records be presented to Claude?**

Options:
- A) Concatenated text
- B) Structured JSON
- C) Numbered list
- D) User chooses format

**A11:** User requested recommendation.

**RECOMMENDATION:** Option D - User chooses format, with JSON as default (most flexible).

Implementation:
- When "Semantic Search" is selected as input, show a "Result Format" dropdown
- Options: "JSON Array" (default), "Numbered List", "Concatenated Text"
- Also show "Max Results" field (default: 5)
- Template variable: `{{similar_results}}`

This provides flexibility without over-complicating the initial implementation.

**Q12: How should the worker handle rate limits from Claude API?**

Options:
- A) Simple retry with delay
- B) Exponential backoff
- C) Queue and continue
- D) Pause all processing

**A12:** Option D with modification - **Pause all processing** when rate limited, but:
- Check every 60 seconds if API is accepting requests again
- Resume automatically when rate limit clears
- Log the pause/resume events for monitoring

### Batch 5 (2025-12-30)

**Q13: How should the worker process be started and stopped?**

Options:
- A) Manual start/stop (command line)
- B) Windows Service
- C) Started by FastAPI (subprocess)
- D) Button in UI

**A13:** Option D - **UI buttons** to control worker:
- "Start Worker" button
- "Stop Worker" button
- "Check Status" button to verify if worker is running

**CRITICAL REQUIREMENT:** Worker must continue running even if the GUI/FastAPI server is down. The UI buttons just send signals to the worker process; they don't host it.

**Q14: How should pipeline progress be displayed to the user?**

Options:
- A) Simple status text
- B) Progress bar + log
- C) Detailed dashboard
- D) Minimal (background)

**A14:** Option C - **Detailed dashboard** with:
- Per-step progress indicators
- Estimated time remaining
- Success/failure counts
- Current record details being processed
- Historical run statistics

**Q15: After pipeline completes for a confirmed paragraph/diagram, what should happen to its status?**

Options:
- A) Mark as 'processed'
- B) Keep as 'confirmed'
- C) Mark as 'enriched'
- D) Per-step tracking

**A15:** Option D - **Per-step tracking**. Track which steps have completed for each record:
- Each record shows progress like "Step 3/5 complete"
- Can see exactly which steps succeeded/failed per record
- Allows re-running individual failed steps

### Batch 6 (2025-12-30) - FINAL

**Q16: How should the worker process communicate its status to the UI (since worker runs independently)?**

Options:
- A) Database polling
- B) File-based status
- C) WebSocket from worker
- D) Named pipe / IPC

**A16:** Option A - **Database polling**. Worker writes status to a PostgreSQL table. UI polls this table every few seconds to get updates.

Implementation:
- Worker updates `worker_status` table with: current state, current record, progress counts, last heartbeat
- UI polls this table every 2-5 seconds
- If heartbeat is stale (>30 seconds), UI shows "Worker may be stopped"

**Q17: Should the pipeline configuration be copied when creating a new book, or start fresh?**

Options:
- A) Start fresh (empty)
- B) Copy from template book
- C) Global default template
- D) Choose at creation time

**A17:** Option D - **Choose at creation time**. When creating a new book, user selects:
- "Empty" - No pipeline steps
- "Copy from [Book X]" - Clone another book's pipeline config
- "Use Default Template" - Apply system default template

**Q18: If a step fails for a specific record (e.g., Claude returns error), what should happen to other steps for that record?**

Options:
- A) Skip remaining steps
- B) Continue remaining steps
- C) Configurable per step
- D) Retry then skip

**A18:** Option C - **Configurable per step**. Each step has an "On Failure" setting:
- "Skip Remaining Steps" - Critical step; if it fails, abort remaining steps for this record
- "Continue to Next Step" - Optional step; failure doesn't block other steps

This allows mixing critical and optional steps in the same pipeline.

---

## 6. Requirements Checklist (Complete)

### 6.1 Backend Worker Requirements
- [ ] Standalone Python process (independent of FastAPI)
- [ ] Continues running even if GUI/server is down
- [ ] Polls PostgreSQL for pending tasks
- [ ] Processes paragraphs and diagrams separately
- [ ] Parallel processing per record (different records in parallel)
- [ ] Sequential step execution within each record
- [ ] Calls Claude API with configured prompts and models
- [ ] Supports template variable substitution (both original and user-defined names)
- [ ] Stores Claude responses in specified DB fields
- [ ] Supports PostgreSQL and ChromaDB as input/output
- [ ] Caches Claude API responses (prevents duplicate calls on retry)
- [ ] Resume from failure point (skip already-processed records)
- [ ] Per-step failure handling (configurable: skip remaining or continue)
- [ ] Rate limit handling: pause all, check every 60s, auto-resume
- [ ] Writes status to PostgreSQL for UI polling
- [ ] Heartbeat mechanism for "worker alive" detection
- [ ] Logs progress per book

### 6.2 Frontend Requirements

#### 6.2.1 Pipeline Configuration Page
- [ ] Book selector dropdown
- [ ] Template variable reference table (original + user-defined names)
- [ ] Multiple prompt steps (add/remove/reorder)
- [ ] Per-step configuration:
  - [ ] Step name (text input)
  - [ ] Prompt textarea with template variables
  - [ ] Input source: PostgreSQL field OR ChromaDB operation
  - [ ] Output destination: PostgreSQL field OR ChromaDB operation
  - [ ] Claude model selector (Sonnet/Opus/Haiku/None)
  - [ ] Applies to: Paragraphs/Diagrams/Both
  - [ ] On Failure: Skip Remaining Steps / Continue
- [ ] Save configuration button
- [ ] Copy config from another book (at creation time)

#### 6.2.2 Confirmation/Merge-Split Page
- [ ] "Execute Pipeline (Paragraphs)" button
- [ ] "Execute Pipeline (Diagrams)" button
- [ ] Checkbox for "Execute all unprocessed records" (batch mode)
- [ ] Per-record step progress display (e.g., "Step 3/5 complete")

#### 6.2.3 Worker Control (in UI)
- [ ] "Start Worker" button
- [ ] "Stop Worker" button
- [ ] "Check Status" button
- [ ] Worker status indicator

#### 6.2.4 Pipeline Dashboard
- [ ] Per-step progress indicators
- [ ] Estimated time remaining
- [ ] Success/failure counts
- [ ] Current record details being processed
- [ ] Historical run statistics
- [ ] Real-time updates via database polling

### 6.3 Database Requirements

#### 6.3.1 New Tables (Per Book)
- [ ] `{prefix}_pipeline_config` - Pipeline step definitions
- [ ] `{prefix}_task_queue` - Pending/running/completed tasks
- [ ] `{prefix}_step_progress` - Per-record step completion tracking

#### 6.3.2 New Tables (Global)
- [ ] `worker_status` - Worker heartbeat and current state
- [ ] `pipeline_templates` - Default/template pipeline configurations

#### 6.3.3 Data Integrity
- [ ] Claude response caching in task_queue (api_response column)
- [ ] Transaction safety: response stored before marking complete
- [ ] Task status tracking (pending, running, completed, failed)
- [ ] Error message logging per task
- [ ] Retry count tracking

### 6.4 ChromaDB Integration
- [ ] Input operations: Get Embedding, Semantic Search, Get Similar Text, Get Metadata
- [ ] Output operations: Upsert Embedding, Update Metadata, Delete Entry, Add with Custom Text
- [ ] Semantic Search result format: configurable (JSON/List/Concatenated)
- [ ] Max results parameter for searches

---

## 7. Technical Specifications

### 7.1 Database Schema

#### 7.1.1 Global Tables

```sql
-- Worker status table (global, not per-book)
CREATE TABLE worker_status (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped',  -- stopped, running, paused, rate_limited
    current_book_id INTEGER,
    current_entity_type VARCHAR(20),       -- paragraph, diagram
    current_record_id INTEGER,
    current_step INTEGER,
    total_steps INTEGER,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    records_remaining INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    rate_limited_until TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pipeline templates (for copying to new books)
CREATE TABLE pipeline_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,  -- Array of step configurations
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 7.1.2 Per-Book Tables

```sql
-- Pipeline configuration (per book)
CREATE TABLE {prefix}_pipeline_config (
    id SERIAL PRIMARY KEY,
    step_order INTEGER NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    prompt_template TEXT,
    input_source VARCHAR(20) NOT NULL,      -- 'postgresql' or 'chromadb'
    input_field VARCHAR(100),               -- PostgreSQL column name or ChromaDB operation
    input_params JSONB,                     -- Additional params (e.g., max_results for search)
    output_destination VARCHAR(20) NOT NULL, -- 'postgresql' or 'chromadb'
    output_field VARCHAR(100),              -- PostgreSQL column name or ChromaDB operation
    claude_model VARCHAR(50),               -- 'sonnet-4', 'opus-4.5', 'haiku', NULL for no API call
    applies_to VARCHAR(20) DEFAULT 'paragraphs', -- 'paragraphs', 'diagrams', 'both'
    on_failure VARCHAR(30) DEFAULT 'skip_remaining', -- 'skip_remaining', 'continue'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(step_order)
);

-- Task queue (per book)
CREATE TABLE {prefix}_task_queue (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,       -- 'paragraph' or 'diagram'
    entity_id INTEGER NOT NULL,             -- ID in paragraph_images or diagram_images table
    current_step INTEGER DEFAULT 1,
    total_steps INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',   -- pending, running, completed, failed, paused
    priority INTEGER DEFAULT 0,

    -- Claude API caching (critical for cost control)
    api_response JSONB,                     -- Cached Claude response
    api_called_at TIMESTAMP,
    api_model_used VARCHAR(50),
    api_tokens_used INTEGER,

    -- Retry handling
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(entity_type, entity_id)
);

-- Step progress tracking (per book)
CREATE TABLE {prefix}_step_progress (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,       -- 'paragraph' or 'diagram'
    entity_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    step_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',   -- pending, running, completed, failed, skipped

    -- Results
    api_response JSONB,                     -- Claude response for this step
    output_value TEXT,                      -- What was written to output field
    error_message TEXT,

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(entity_type, entity_id, step_order)
);

-- Indexes for efficient querying
CREATE INDEX idx_{prefix}_task_queue_pending
ON {prefix}_task_queue (entity_type, status, priority)
WHERE status = 'pending';

CREATE INDEX idx_{prefix}_step_progress_entity
ON {prefix}_step_progress (entity_type, entity_id, step_order);
```

### 7.2 Worker Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WORKER PROCESS                                │
│                     (worker/main.py)                                 │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Main Loop                                 │    │
│  │                                                              │    │
│  │  while True:                                                 │    │
│  │    1. Update heartbeat in worker_status                      │    │
│  │    2. Check for stop signal                                  │    │
│  │    3. Poll for pending tasks across all books                │    │
│  │    4. For each task (in parallel up to N workers):           │    │
│  │       - Execute steps sequentially                           │    │
│  │       - Handle failures per step config                      │    │
│  │    5. Sleep if no work                                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   Claude    │  │  PostgreSQL │  │  ChromaDB   │                  │
│  │   Client    │  │   Client    │  │   Client    │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Template Variable Substitution

```python
# Example template processing
prompt_template = """
Summarize the following text in Arabic:

Text: {{text_content}}

Previous OCR result: {{easyocr_result}}
"""

# Variable mapping (from book's column_definitions)
variable_map = {
    'text_content': 'text_content',      # Original name
    'paragraph_text': 'text_content',    # User-defined alias
    'easyocr_result': 'attr2_value',     # User-defined alias
    'attr2_value': 'attr2_value',        # Original name also works
}

# Substitution logic
def substitute_variables(template, record, variable_map):
    result = template
    for var_name, column_name in variable_map.items():
        placeholder = '{{' + var_name + '}}'
        value = record.get(column_name, '')
        result = result.replace(placeholder, str(value))
    return result
```

### 7.4 Worker Control via UI

```
UI Button Click                    Worker Process
     │                                   │
     │  "Start Worker"                   │
     ▼                                   │
┌─────────────┐                          │
│ FastAPI     │  subprocess.Popen()      │
│ Endpoint    │─────────────────────────►│ Worker starts
│             │                          │ (independent process)
└─────────────┘                          │
                                         │
     │  "Stop Worker"                    │
     ▼                                   │
┌─────────────┐                          │
│ FastAPI     │  INSERT INTO             │
│ Endpoint    │  worker_commands         │
│             │  (command='stop')        │
└─────────────┘        │                 │
                       │  Worker polls   │
                       └────────────────►│ Worker sees stop
                                         │ command, exits
                                         │ gracefully
```

### 7.5 Rate Limit Handling

```python
def handle_rate_limit(error, worker_status_id):
    # 1. Update worker status
    db.execute("""
        UPDATE worker_status
        SET status = 'rate_limited',
            rate_limited_until = NOW() + INTERVAL '60 seconds',
            last_error = :error
        WHERE id = :id
    """, {'error': str(error), 'id': worker_status_id})

    # 2. Wait and retry loop
    while True:
        time.sleep(60)  # Check every minute

        # 3. Try a simple API call to check if rate limit cleared
        try:
            test_response = claude.messages.create(
                model="claude-haiku",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            # Success! Rate limit cleared
            db.execute("""
                UPDATE worker_status
                SET status = 'running',
                    rate_limited_until = NULL
                WHERE id = :id
            """, {'id': worker_status_id})
            return
        except RateLimitError:
            # Still rate limited, continue waiting
            continue
```

---

## 8. Implementation Plan

### Phase 1: Database Schema (1-2 days)
1. Create migration scripts for new tables
2. Add global tables (worker_status, pipeline_templates)
3. Add per-book table creation to existing book creation flow
4. Test table creation and relationships

### Phase 2: Backend Worker Core (3-4 days)
1. Create worker module structure
2. Implement main polling loop
3. Implement task execution engine
4. Implement template variable substitution
5. Implement Claude API integration with caching
6. Implement rate limit handling
7. Implement PostgreSQL input/output handlers
8. Implement ChromaDB input/output handlers
9. Test with sample pipeline

### Phase 3: Frontend - Configuration Page (2-3 days)
1. Create pipeline configuration page HTML/CSS
2. Implement step add/remove/reorder functionality
3. Implement template variable reference display
4. Implement input/output source selection
5. Implement save/load configuration
6. Connect to API endpoints

### Phase 4: Frontend - Dashboard & Controls (2-3 days)
1. Add worker control buttons to existing page
2. Create pipeline dashboard with progress tracking
3. Implement real-time status polling
4. Add "Execute Pipeline" buttons to merge/split page
5. Display per-record step progress

### Phase 5: Integration & Testing (2-3 days)
1. End-to-end testing with real book data
2. Test failure scenarios and recovery
3. Test rate limiting behavior
4. Performance testing with parallel processing
5. Documentation and cleanup

**Total Estimated Effort: 10-15 days**

---

## 9. File Structure

```
03-code/
├── src/
│   ├── worker/                          # NEW: Worker module
│   │   ├── __init__.py
│   │   ├── main.py                      # Entry point
│   │   ├── config.py                    # Worker configuration
│   │   ├── loop.py                      # Main polling loop
│   │   ├── executor.py                  # Task execution engine
│   │   ├── template_engine.py           # Variable substitution
│   │   ├── rate_limiter.py              # Rate limit handling
│   │   │
│   │   ├── handlers/                    # Input/Output handlers
│   │   │   ├── __init__.py
│   │   │   ├── postgresql_handler.py
│   │   │   ├── chromadb_handler.py
│   │   │   └── claude_handler.py
│   │   │
│   │   └── models/                      # Data models
│   │       ├── __init__.py
│   │       ├── task.py
│   │       └── step.py
│   │
│   ├── api/routes/
│   │   ├── pipeline.py                  # NEW: Pipeline config API
│   │   └── worker_control.py            # NEW: Worker control API
│   │
│   └── frontend/
│       ├── templates/
│       │   ├── pipeline-config.html     # NEW: Configuration page
│       │   └── pipeline-dashboard.html  # NEW: Dashboard page
│       │
│       └── static/js/
│           ├── pipeline-config.js       # NEW
│           └── pipeline-dashboard.js    # NEW
```

---

## 10. Summary of Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Task Queue Location | PostgreSQL | Single source of truth, ACID transactions |
| Worker Independence | Separate process | Runs even when GUI is down |
| Processing Granularity | Per paragraph/diagram | User-defined entities |
| Step Execution | Parallel per record | Different records in parallel |
| Claude Model | Configurable per step | Flexibility for different tasks |
| Input/Output | Single source per step | Simplicity; use two steps for dual output |
| Rate Limit Handling | Pause all, check every 60s | Cost control |
| Failure Handling | Configurable per step | Critical vs optional steps |
| Worker-UI Communication | Database polling | Works when processes are separate |
| Template Config | Choose at book creation | Empty/Copy/Template options |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-30 | Initial document creation |
| 1.1 | 2025-12-30 | Added all Q&A from 6 batches |
| 1.2 | 2025-12-30 | Added complete requirements checklist |
| 1.3 | 2025-12-30 | Added technical specifications and implementation plan |
