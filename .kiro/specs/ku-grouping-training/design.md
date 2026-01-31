# Requirement 7: Design Document

## KU Grouping, Multi-Tag Extraction & YOLO Fine-Tuning

**Created:** January 29, 2026
**Status:** Design Phase

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [7A: Multi-Tag XML Extraction Design](#7a-multi-tag-xml-extraction-design)
3. [7B: Knowledge Unit Grouping Design](#7b-knowledge-unit-grouping-design)
4. [7C: YOLO Fine-Tuning Design](#7c-yolo-fine-tuning-design)
5. [Database Schema Changes](#database-schema-changes)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Configuration UI                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Tag Mapping    │  │  KU Grouping    │  │  Execution      │  │
│  │  Table (7A)     │  │  Config (7B)    │  │  Mode Selector  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Execution Service                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Multi-Tag      │  │  KU Grouper     │  │  Response       │  │
│  │  Parser         │  │  Service        │  │  Distributor    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Batch Service                          │
│                 (Existing: claude_batch_service.py)               │
└─────────────────────────────────────────────────────────────────┘
```

### YOLO Training Component

```
┌─────────────────────────────────────────────────────────────────┐
│                     Layout Review UI                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Region Editor  │  │  Correction     │  │  Training       │  │
│  │  Canvas         │  │  Tracker        │  │  Dashboard      │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     YOLO Training Service                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Correction     │  │  Training Data  │  │  Model          │  │
│  │  Storage        │  │  Exporter       │  │  Trainer        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7A: Multi-Tag XML Extraction Design

### Data Model

```python
# New fields in pipeline_config table
class PipelineStepTagMapping:
    """Tag-to-attribute mapping for a pipeline step"""
    step_id: int
    tag_name: str           # e.g., "summary", "keywords"
    target_attribute: str   # e.g., "attr_15", "attr_16"
    is_required: bool       # If true, mark KU incomplete if missing
    order: int              # Display order in UI
```

### Tag Mapping Table Schema

```sql
-- Add to {prefix}_pipeline_config table
ALTER TABLE {prefix}_pipeline_config ADD COLUMN tag_mappings JSONB DEFAULT '[]';
ALTER TABLE {prefix}_pipeline_config ADD COLUMN fallback_attribute VARCHAR(20);

-- tag_mappings JSON structure:
-- [
--   {"tag_name": "summary", "target_attribute": "attr_15", "is_required": true, "order": 1},
--   {"tag_name": "keywords", "target_attribute": "attr_16", "is_required": false, "order": 2}
-- ]
```

### Response Parser Logic

```python
def parse_multi_tag_response(response: str, tag_mappings: List[dict], fallback_attr: str) -> dict:
    """
    Parse Claude response for multiple XML tags.
    
    Returns:
        {
            "extracted": {"attr_15": "summary content", "attr_16": "keywords"},
            "unmapped": {"unknown_tag": "content"},
            "missing_required": ["tag_name"],
            "is_complete": True/False
        }
    """
    import re
    
    extracted = {}
    unmapped = {}
    missing_required = []
    
    # Map tag names to attributes
    tag_to_attr = {m["tag_name"]: m["target_attribute"] for m in tag_mappings}
    required_tags = {m["tag_name"] for m in tag_mappings if m.get("is_required")}
    
    # Find all XML tags in response
    pattern = r'<(\w+)>(.*?)</\1>'
    matches = re.findall(pattern, response, re.DOTALL)
    
    found_tags = set()
    for tag_name, content in matches:
        found_tags.add(tag_name)
        if tag_name in tag_to_attr:
            extracted[tag_to_attr[tag_name]] = content.strip()
        else:
            unmapped[tag_name] = content.strip()
    
    # Check for missing required tags
    missing_required = list(required_tags - found_tags)
    
    # Store unmapped in fallback attribute if configured
    if unmapped and fallback_attr:
        extracted[fallback_attr] = json.dumps(unmapped)
    
    return {
        "extracted": extracted,
        "unmapped": unmapped,
        "missing_required": missing_required,
        "is_complete": len(missing_required) == 0
    }
```

---

## 7B: Knowledge Unit Grouping Design

### Grouping Configuration Schema

```sql
-- New table for grouping configuration (per book)
CREATE TABLE {prefix}_ku_grouping_config (
    id SERIAL PRIMARY KEY,
    is_enabled BOOLEAN DEFAULT FALSE,
    grouping_mode VARCHAR(20) DEFAULT 'ku_count',  -- 'ku_count' or 'token_limit'
    max_kus_per_group INT DEFAULT 5,
    max_tokens_per_group INT DEFAULT 4000,
    fallback_attribute VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 80 custom attributes for grouped KU results
-- These are added to {prefix}_knowledge_units table
-- attr_81_name through attr_160_name
-- attr_81_value through attr_160_value
```

### KU Grouper Service

```python
class KUGrouperService:
    """Service for grouping Knowledge Units for batch Claude processing"""
    
    def get_grouping_preview(self, book_id: int) -> List[dict]:
        """
        Get preview table of L1 → L2 → KU count → word count.
        
        Returns:
            [
                {
                    "l1_title": "Chapter 1",
                    "l2_title": "Section 1.1",
                    "ku_count": 15,
                    "word_count": 3200,
                    "estimated_tokens": 4100
                },
                ...
            ]
        """
        pass
    
    def create_groups(self, book_id: int, config: dict) -> List[dict]:
        """
        Create KU groups based on configuration.
        
        Args:
            config: {
                "mode": "ku_count" | "token_limit",
                "max_kus": 5,
                "max_tokens": 4000
            }
        
        Returns:
            [
                {
                    "group_id": 1,
                    "l1_title": "Chapter 1",
                    "l2_title": "Section 1.1",
                    "ku_ids": [123, 124, 125],
                    "total_tokens": 3500
                },
                ...
            ]
        """
        pass
    
    def build_grouped_prompt(self, ku_ids: List[int], prompt_template: str) -> str:
        """
        Build prompt with multiple KUs wrapped in ID tags.
        
        Format:
            <ku_123>
                <description>KU text...</description>
                <attr_12>existing value...</attr_12>
            </ku_123>
            <ku_124>
                ...
            </ku_124>
        """
        pass
    
    def distribute_response(self, response: str, ku_ids: List[int], tag_mappings: List[dict]) -> dict:
        """
        Parse grouped response and distribute to individual KUs.
        
        Response format:
            <ku_123>
                <summary>Generated summary...</summary>
            </ku_123>
            <ku_124>
                <summary>Another summary...</summary>
            </ku_124>
        
        Returns:
            {
                123: {"attr_15": "Generated summary...", "is_complete": True},
                124: {"attr_15": "Another summary...", "is_complete": True},
                125: {"is_complete": False, "error": "Missing from response"}
            }
        """
        pass
```

### Token Estimation

```python
def estimate_tokens(text: str) -> int:
    """
    Estimate Claude tokens for text.
    Uses tiktoken cl100k_base encoding (close to Claude's tokenizer).
    """
    import tiktoken
    
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except:
        # Fallback: ~4 chars per token
        return len(text) // 4
```

### Execution Modes

```python
class ExecutionMode(Enum):
    INDIVIDUAL = "individual"      # Process each KU separately (default)
    GROUPED = "grouped"            # Process KUs in groups
    INCOMPLETE_ONLY = "incomplete" # Retry only incomplete KUs
```

---

## 7C: YOLO Fine-Tuning Design

### Correction Storage Schema

```sql
-- New table for storing layout corrections
CREATE TABLE {prefix}_layout_corrections (
    id SERIAL PRIMARY KEY,
    page_number INT NOT NULL,
    
    -- Original YOLO detection
    original_x INT,
    original_y INT,
    original_width INT,
    original_height INT,
    original_class VARCHAR(50),
    original_confidence FLOAT,
    
    -- User correction
    corrected_x INT,
    corrected_y INT,
    corrected_width INT,
    corrected_height INT,
    corrected_class VARCHAR(50),
    
    -- Correction type
    correction_type VARCHAR(20),  -- 'adjusted', 'deleted', 'added'
    
    -- Metadata
    model_version INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_page FOREIGN KEY (page_number) 
        REFERENCES {prefix}_pages(page_number)
);

-- Index for efficient queries
CREATE INDEX idx_corrections_page ON {prefix}_layout_corrections(page_number);
CREATE INDEX idx_corrections_type ON {prefix}_layout_corrections(correction_type);
```

### Training Data Exporter

```python
class YOLOTrainingExporter:
    """Export corrections to YOLO training format"""
    
    def export_training_data(self, book_id: int, output_dir: Path) -> dict:
        """
        Export to YOLO format:
        
        output_dir/
        ├── images/
        │   ├── page_001.png
        │   ├── page_002.png
        │   └── ...
        └── labels/
            ├── page_001.txt
            ├── page_002.txt
            └── ...
        
        Label format (YOLO):
        class_id center_x center_y width height
        (all values normalized 0-1)
        
        Returns:
            {
                "pages_exported": 25,
                "corrections_exported": 150,
                "class_distribution": {"paragraph": 80, "diagram": 30, ...}
            }
        """
        pass
    
    def get_training_statistics(self, book_id: int) -> dict:
        """
        Get statistics for training readiness.
        
        Returns:
            {
                "total_corrections": 150,
                "pages_with_corrections": 25,
                "corrections_per_page": 6.0,
                "class_distribution": {"paragraph": 80, "diagram": 30, ...},
                "ready_for_training": True,
                "warnings": ["Less than 20 pages - results may vary"]
            }
        """
        pass
```

### Model Trainer Service

```python
class YOLOModelTrainer:
    """Service for fine-tuning DocLayout-YOLO"""
    
    def __init__(self, book_id: int):
        self.book_id = book_id
        self.backup_dir = Path("models/backups")
        self.output_dir = Path(f"models/layout_detection/fine_tuned")
    
    def backup_current_model(self) -> Path:
        """
        Backup current model before training.
        
        Returns path to backup file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"book_{self.book_id}_{timestamp}.pt"
        # Copy current model to backup
        return backup_path
    
    def start_training(self, config: dict, background: bool = True) -> dict:
        """
        Start YOLO fine-tuning.
        
        Args:
            config: {
                "epochs": 50,
                "batch_size": 4,
                "learning_rate": 0.001,
                "use_amp": True  # Mixed precision for 8GB VRAM
            }
            background: Run in background process
        
        Returns:
            {"job_id": "...", "status": "started"}
        """
        pass
    
    def get_training_progress(self, job_id: str) -> dict:
        """
        Get training progress.
        
        Returns:
            {
                "status": "running",
                "current_epoch": 25,
                "total_epochs": 50,
                "metrics": {
                    "loss": 0.05,
                    "mAP": 0.85,
                    "precision": 0.88,
                    "recall": 0.82
                }
            }
        """
        pass
```

---

## Database Schema Changes

### Migration Script

```python
# migrate_add_ku_grouping_training.py

def upgrade():
    """Add tables and columns for KU grouping and YOLO training"""
    
    # 1. Add tag_mappings to pipeline_config
    # ALTER TABLE {prefix}_pipeline_config ADD COLUMN tag_mappings JSONB DEFAULT '[]';
    # ALTER TABLE {prefix}_pipeline_config ADD COLUMN fallback_attribute VARCHAR(20);
    
    # 2. Create KU grouping config table
    # CREATE TABLE {prefix}_ku_grouping_config (...)
    
    # 3. Add 80 more custom attributes (attr_81 through attr_160)
    # for grouped KU results
    
    # 4. Create layout corrections table
    # CREATE TABLE {prefix}_layout_corrections (...)
    
    # 5. Add incomplete status tracking
    # ALTER TABLE {prefix}_knowledge_units ADD COLUMN is_complete BOOLEAN DEFAULT TRUE;
    # ALTER TABLE {prefix}_knowledge_units ADD COLUMN incomplete_reason TEXT;
```

---

## API Endpoints

### 7A: Multi-Tag Extraction

```
PUT /api/books/{book_id}/pipeline/steps/{step_id}/tag-mappings
    Body: {"tag_mappings": [...], "fallback_attribute": "attr_20"}

GET /api/books/{book_id}/pipeline/steps/{step_id}/tag-mappings
    Returns: {"tag_mappings": [...], "fallback_attribute": "attr_20"}
```

### 7B: KU Grouping

```
GET /api/books/{book_id}/pipeline/grouping/preview
    Returns: [{"l1_title": "...", "l2_title": "...", "ku_count": 15, ...}]

POST /api/books/{book_id}/pipeline/grouping/estimate-tokens
    Body: {"ku_ids": [1,2,3], "prompt_template": "..."}
    Returns: {"input_tokens": 3500, "estimated_output_tokens": 1500}

PUT /api/books/{book_id}/pipeline/grouping/config
    Body: {"mode": "ku_count", "max_kus": 5, "fallback_attribute": "attr_20"}

POST /api/books/{book_id}/pipeline/execute
    Body: {"mode": "grouped", "dry_run": false, "save_preview_to": "attr_25"}
```

### 7C: YOLO Training

```
GET /api/books/{book_id}/layout/corrections/statistics
    Returns: {"total_corrections": 150, "pages_with_corrections": 25, ...}

POST /api/books/{book_id}/layout/corrections
    Body: {"page_number": 5, "original": {...}, "corrected": {...}, "type": "adjusted"}

POST /api/books/{book_id}/layout/training/export
    Returns: {"export_path": "...", "pages_exported": 25}

POST /api/books/{book_id}/layout/training/start
    Body: {"epochs": 50, "background": true}
    Returns: {"job_id": "...", "status": "started"}

GET /api/books/{book_id}/layout/training/progress/{job_id}
    Returns: {"status": "running", "current_epoch": 25, "metrics": {...}}
```

---

## Frontend Components

### 7A: Tag Mapping Table

```html
<!-- In pipeline-config.html -->
<div class="tag-mapping-section">
    <h4>Tag-to-Attribute Mapping</h4>
    <table class="tag-mapping-table">
        <thead>
            <tr>
                <th>XML Tag Name</th>
                <th>Target Attribute</th>
                <th>Required</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="tag-mappings-body">
            <!-- Dynamic rows -->
        </tbody>
    </table>
    <button onclick="addTagMapping()">+ Add Mapping</button>
    
    <div class="fallback-config">
        <label>Fallback Attribute for Unmapped Tags:</label>
        <select id="fallback-attribute">
            <option value="">-- None --</option>
            <!-- attr_1 through attr_80 -->
        </select>
    </div>
</div>
```

### 7B: Grouping Preview Table

```html
<!-- In pipeline-dashboard.html -->
<div class="grouping-preview-section">
    <h4>KU Grouping Preview</h4>
    <table class="grouping-preview-table">
        <thead>
            <tr>
                <th>L1 Title</th>
                <th>L2 Title</th>
                <th>KU Count</th>
                <th>Word Count</th>
                <th>Est. Tokens</th>
            </tr>
        </thead>
        <tbody id="grouping-preview-body">
            <!-- Dynamic rows -->
        </tbody>
    </table>
    
    <div class="grouping-config">
        <label>Group By:</label>
        <select id="grouping-mode">
            <option value="ku_count">Max KUs per Group</option>
            <option value="token_limit">Max Tokens per Group</option>
        </select>
        <input type="number" id="grouping-limit" value="5">
        <button onclick="previewTokens()">Preview Tokens</button>
    </div>
    
    <div class="execution-mode">
        <label>Execution Mode:</label>
        <select id="execution-mode">
            <option value="individual">Individual KUs (default)</option>
            <option value="grouped">Grouped KUs</option>
            <option value="incomplete">Incomplete KUs Only</option>
        </select>
        <label><input type="checkbox" id="dry-run"> Dry Run</label>
    </div>
</div>
```

### 7C: Training Dashboard

```html
<!-- In layout-training.html (new page) -->
<div class="training-dashboard">
    <h3>YOLO Fine-Tuning</h3>
    
    <div class="training-statistics">
        <div class="stat-card">
            <span class="stat-value" id="total-corrections">0</span>
            <span class="stat-label">Total Corrections</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" id="pages-corrected">0</span>
            <span class="stat-label">Pages Corrected</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" id="corrections-per-page">0</span>
            <span class="stat-label">Avg Corrections/Page</span>
        </div>
    </div>
    
    <div class="class-distribution">
        <h4>Class Distribution</h4>
        <canvas id="class-chart"></canvas>
    </div>
    
    <div class="training-controls">
        <div class="warning" id="training-warning" style="display:none;">
            ⚠️ Less than 20 pages corrected - results may vary
        </div>
        
        <label>Run Mode:</label>
        <select id="training-mode">
            <option value="background">Background (recommended)</option>
            <option value="foreground">Foreground (blocking)</option>
        </select>
        
        <button onclick="startTraining()" class="btn-primary">
            Start Training
        </button>
    </div>
    
    <div class="training-progress" id="training-progress" style="display:none;">
        <h4>Training Progress</h4>
        <div class="progress-bar">
            <div class="progress-fill" id="progress-fill"></div>
        </div>
        <div class="metrics">
            <span>Epoch: <span id="current-epoch">0</span>/<span id="total-epochs">50</span></span>
            <span>Loss: <span id="current-loss">-</span></span>
            <span>mAP: <span id="current-map">-</span></span>
        </div>
    </div>
</div>
```

---

## Files to Modify

### Backend

| File | Changes |
|------|---------|
| `03-code/src/api/routes/pipeline.py` | Add tag mapping and grouping endpoints |
| `03-code/src/services/claude_batch_service.py` | Add multi-tag parsing, grouped execution |
| `03-code/src/services/ku_grouper_service.py` | NEW: KU grouping logic |
| `03-code/src/services/yolo_training_service.py` | NEW: Training data export, model training |
| `03-code/src/api/routes/layout_detection.py` | Add correction storage, training endpoints |
| `03-code/src/database/table_creator.py` | Add new tables and columns |

### Frontend

| File | Changes |
|------|---------|
| `03-code/src/frontend/templates/pipeline-config.html` | Add tag mapping UI |
| `03-code/src/frontend/templates/pipeline-dashboard.html` | Add grouping preview, execution modes |
| `03-code/src/frontend/templates/layout-training.html` | NEW: Training dashboard |
| `03-code/src/frontend/static/js/pipeline-config.js` | Tag mapping logic |
| `03-code/src/frontend/static/js/layout-review.js` | Correction tracking |

---

## Implementation Priority

| Phase | Feature | Complexity | Dependencies |
|-------|---------|------------|--------------|
| 1 | 7A Multi-Tag Extraction | Medium | Pipeline config |
| 2 | 7B KU Grouping | High | 7A, Title hierarchy |
| 3 | 7C YOLO Fine-Tuning | High | Layout review |
