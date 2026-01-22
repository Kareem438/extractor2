# Knowledge Unit Creation - Technical Design

## Architecture Overview

### Data Flow
```
Layout Review → Extraction → Create KUs → Claude Analysis
     ↓              ↓            ↓             ↓
  Validation    raw_*_images  knowledge_units  text_content
```

### New Service: Knowledge Unit Creation Service
**File:** `03-code/src/services/ku_creation_service.py`

```python
# Core functions:
- create_knowledge_units_for_pages(book_id, page_numbers) -> Dict
- create_paragraph_ku(db, prefix, paragraph_record) -> int
- create_diagram_ku(db, prefix, diagram_record, parent_text) -> int
- create_qa_ku(db, prefix, question_record, answer_record) -> int
- get_parent_paragraph_text(db, prefix, linked_ku_id) -> str
```

## Database Changes

### Attribute Key Updates
Update `{prefix}_attribute_keys` table with new attribute names:
- attr9: "layout_class_type"
- attr10: "parent_paragraph_text"
- attr11: "answer_text"
- attr12: "raw_entity_reference"

### No Schema Changes Required
All columns already exist in knowledge_units table.

## API Endpoints

### New Endpoints
```
POST /api/pipeline/{book_id}/create-knowledge-units
  Body: { page_numbers: [1, 2, 3] }
  Response: { success, created_count, errors }

GET /api/pipeline/{book_id}/page-status
  Response: { pages: [{ page_number, layout_status, extraction_status, ku_status, claude_status }] }
```

### Modified Endpoints
```
PUT /api/extraction/{book_id}/ready-for-extraction
  - Add validation for orphan regions
  - Return validation errors with region IDs
```

## Frontend Changes

### Layout Review Validation
**File:** `03-code/src/frontend/static/js/layout-review.js`

Add validation functions:
- `validateOrphanDiagrams()` - check diagrams/tables/equations/lists have parent
- `validateOrphanQA()` - check questions have answers and vice versa
- `showOrphanAnimation(regionId)` - red rectangle animation
- `canMarkReady()` - returns true only if all validations pass

### Pipeline Page Enhancement
**File:** `03-code/src/frontend/templates/pipeline.html`
**File:** `03-code/src/frontend/static/js/pipeline.js`

Add:
- Page status table with columns
- Checkbox selection with "Select All"
- "Create Knowledge Units" button
- Status indicators (pending/completed)
- Thumbnail rendering with layout overlay

### Header Navigation
**Files:** All template files with top-nav

Update order:
1. Upload
2. Auto-Slicer
3. Extraction
4. Pipeline
5. Library
6. (rest)

### Page Descriptions
Add description div below header in each template.

## Implementation Order

### Phase 1: Backend Service (Tasks 1-3)
1. Create KU creation service
2. Add API endpoints
3. Update attribute keys

### Phase 2: Layout Review Validation (Tasks 4-5)
4. Add orphan validation logic
5. Add red rectangle animation

### Phase 3: Pipeline Page UI (Tasks 6-8)
6. Add page status table
7. Add "Create Knowledge Units" button
8. Connect to backend

### Phase 4: Header & Descriptions (Tasks 9-10)
9. Reorder header navigation
10. Add page descriptions

### Phase 5: Claude Integration (Tasks 11-12)
11. Expand Claude processing scope
12. Handle Q&A image retrieval

## Testing Strategy

### Unit Tests
- KU creation service functions
- Validation logic
- API endpoints

### Integration Tests
- Full workflow: extraction → KU creation → Claude analysis
- Bidirectional linking verification
- Q&A merging logic

## References
- Requirements: `.kiro/specs/knowledge-unit-creation/requirements.md`
- Full Requirements: `02-architecture/KNOWLEDGE-UNIT-CREATION-REQUIREMENTS.md`
- Progress: `02-architecture/KU-CREATION-PROGRESS.md`
