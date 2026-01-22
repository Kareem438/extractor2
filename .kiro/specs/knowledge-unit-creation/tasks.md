# Knowledge Unit Creation - Implementation Tasks

## Task Status Legend
- [ ] Not started
- [-] In progress
- [x] Completed

---

## Phase 1: Backend Service

### Task 1: Create KU Creation Service
- [x] 1.1 Create `03-code/src/services/ku_creation_service.py`
- [x] 1.2 Implement `create_paragraph_ku()` function
- [x] 1.3 Implement `create_diagram_ku()` function
- [x] 1.4 Implement `create_qa_ku()` function (merge Q&A into single KU)
- [x] 1.5 Implement `create_knowledge_units_for_pages()` main function
- [x] 1.6 Implement `get_parent_paragraph_text()` helper

### Task 2: Add API Endpoints
- [x] 2.1 Create `/api/pipeline/{book_id}/create-knowledge-units` POST endpoint
- [x] 2.2 Create `/api/pipeline/{book_id}/page-status` GET endpoint
- [x] 2.3 Add routes to main.py (already included via pipeline router)

### Task 3: Update Attribute Keys
- [x] 3.1 Create migration script for attribute key names
- [x] 3.2 Update attr9 = "layout_class_type"
- [x] 3.3 Update attr10 = "parent_paragraph_text"
- [x] 3.4 Update attr11 = "answer_text"
- [x] 3.5 Update attr12 = "raw_entity_reference"

---

## Phase 2: Layout Review Validation

### Task 4: Add Orphan Validation Logic
- [x] 4.1 Add `validateOrphanDiagrams()` function
- [x] 4.2 Add `validateOrphanLists()` function
- [x] 4.3 Add `validateOrphanEquations()` function
- [x] 4.4 Add `validateOrphanQuestions()` function
- [x] 4.5 Add `validateOrphanAnswers()` function
- [x] 4.6 Update `canMarkReady()` to check all validations

### Task 5: Add Red Rectangle Animation
- [x] 5.1 Add `showOrphanAnimation(regionId)` function
- [x] 5.2 Add CSS for red rectangle pulse animation
- [x] 5.3 Show animation when validation fails on "Ready for Extraction" click

---

## Phase 3: Pipeline Page UI

### Task 6: Add Page Status Table
- [x] 6.1 Add table HTML structure to pipeline.html
- [x] 6.2 Add checkbox column with "Select All" header
- [x] 6.3 Add page number column
- [x] 6.4 Add thumbnail column (with layout overlay)
- [x] 6.5 Add status columns (layout, extraction, KU, Claude)
- [x] 6.6 Add CSS styling for table

### Task 7: Add Create Knowledge Units Button
- [x] 7.1 Add button to pipeline.html
- [x] 7.2 Add click handler in pipeline.js
- [x] 7.3 Implement disabled state based on extraction status
- [x] 7.4 Add progress indicator during processing

### Task 8: Connect Pipeline UI to Backend
- [x] 8.1 Implement `loadPageStatus()` function
- [x] 8.2 Implement `createKnowledgeUnits()` function
- [x] 8.3 Implement thumbnail rendering with layout overlay
- [x] 8.4 Add status refresh after operations

---

## Phase 4: Header & Descriptions

### Task 9: Reorder Header Navigation
- [x] 9.1 Update upload.html header
- [x] 9.2 Update auto-slicer.html header
- [x] 9.3 Update extraction-dashboard.html header
- [x] 9.4 Update pipeline.html header
- [x] 9.5 Update library.html header
- [x] 9.6 Update layout-review.html header
- [x] 9.7 Update verify-pages.html header
- [x] 9.8 Update book-settings.html header

### Task 10: Add Page Descriptions
- [x] 10.1 Add description to upload.html
- [x] 10.2 Add description to auto-slicer.html
- [x] 10.3 Add description to extraction-dashboard.html
- [x] 10.4 Add description to pipeline.html
- [x] 10.5 Add description to library.html
- [x] 10.6 Add description to layout-review.html
- [x] 10.7 Add description to verify-pages.html
- [x] 10.8 Add description to book-settings.html

---

## Phase 5: Claude Integration

### Task 11: Expand Claude Processing Scope
- [x] 11.1 Update claude_batch_service.py to process all diagram types
- [x] 11.2 Add question/answer to processing query
- [x] 11.3 Add list types to processing query

### Task 12: Handle Q&A Image Retrieval
- [x] 12.1 Parse attr12_value JSON for Q&A references
- [x] 12.2 Retrieve question image from raw_diagram_images
- [x] 12.3 Retrieve answer image from raw_diagram_images
- [x] 12.4 Send both to Claude (separate requests)
- [x] 12.5 Store question response in text_content
- [x] 12.6 Store answer response in attr11_value

---

## Progress Summary
- Total Tasks: 12
- Total Subtasks: 52
- Completed: 52
- In Progress: 0
- Remaining: 0

---

## References
- Requirements: `.kiro/specs/knowledge-unit-creation/requirements.md`
- Design: `.kiro/specs/knowledge-unit-creation/design.md`
- Full Requirements: `02-architecture/KNOWLEDGE-UNIT-CREATION-REQUIREMENTS.md`
- Progress Tracking: `02-architecture/KU-CREATION-PROGRESS.md`
