# Knowledge Unit Creation from Layout Review - Requirements Specification

**Created**: 2026-01-22
**Status**: Requirements Complete - Ready for Spec Creation
**Related Session**: SESSION-SUMMARY-2026-01-22.md

---

## Overview

This document captures the requirements for extending the Layout Review/Extraction workflow to also create Knowledge Units. Currently, extraction only writes to `raw_paragraph_images` and `raw_diagram_images` tables. This enhancement adds a new step to create corresponding records in the `knowledge_units` table.

---

## Questions & Answers Summary (Q1-Q28)

### Q1: Knowledge Unit Creation Timing
**Question**: When should the `knowledge_units` records be created?
**Answer**: **D** - After Extraction completes (as a separate step)

### Q2: Class Type Storage for Layout Classes
**Question**: How should layout classes map to paragraph vs diagram types?
**Answer**: **A** (Updated by Q12)

**Final Mapping**:
- **Paragraphs** (`raw_paragraph_images`): paragraph only
- **Diagrams** (`raw_diagram_images`): diagram, table, equation, list_bulleted, list_numbered, list_lettered, question, answer

### Q3: Linking Between Tables
**Question**: How should knowledge_units link back to raw tables?
**Answer**: **C** - Bidirectional linking
- Raw tables → KU: `linked_knowledge_unit_id` column
- KU → Raw tables: `attr12_value` stores reference (see Q27 for format)

### Q4: OCR Text Storage for Questions/Answers
**Question**: Which attribute should store preliminary OCR text for questions/answers?
**Answer**: **A** - Use `attr2_value` (currently "easyocr_text" in sequential workflow)

### Q5: List-to-Paragraph Association
**Question**: How should lists be associated with paragraphs?
**Answer**: Same as diagrams:
- Use `linked_knowledge_unit_id` pointing to parent paragraph's knowledge_unit
- User manually links lists to paragraphs during Layout Review (like diagram-paragraph linking)
- Store parent paragraph text in `attr10_value`

### Q6: Knowledge Unit Creation Trigger
**Question**: What triggers the KU creation step?
**Answer**: **D** - Add a new button to Pipeline page

### Q7 & Q8: Attribute Assignments
**Answer**:
- `attr9_value` = "layout_class_type" (stores: paragraph, question, answer, diagram, table, equation, list_bulleted, etc.)
- `attr10_value` = "parent_paragraph_text" (stores OCR text of linked parent paragraph)

### Q9: Title Level Handling
**Question**: How should L1/L2/L3 titles be stored in knowledge_units?
**Answer**: Use existing columns in knowledge_units table:
- `chapter` VARCHAR(255) → Level 1 title
- `topic` VARCHAR(255) → Level 2 title
- `sub_topic` VARCHAR(255) → Level 3 title

L3 titles from layout detection are NOT stored as separate knowledge_units - they're only used to populate the `sub_topic` field in other KUs.

### Q10: Questions and Answers Relationship
**Question**: How should question-answer pairs be stored?
**Answer**: Store BOTH in the SAME knowledge_unit:
- `text_content` = Question text (from Claude)
- `attr11_value` = Answer text (from Claude)
- `attr2_value` = Preliminary OCR text (before Claude)

### Q11: Question-Answer Pairing in Layout Review
**Question**: How should question and answer be paired?
**Answer**: **A** - User manually links answer regions to question regions in Layout Review (like diagram-to-paragraph linking)

### Q12: Raw Table Storage for Question-Answer
**Question**: Where should question and answer regions be stored?
**Answer**: **B** - Both in `raw_diagram_images` (since they need Claude processing like diagrams)

### Q13: OCR for All Diagram Types
**Question**: Should OCR run on questions/answers and other diagram types?
**Answer**: **A** - OCR runs on ALL diagram types, stored in `attr2_value` as preliminary text

### Q14: Pipeline Button Scope
**Question**: What should the "Create Knowledge Units" button process?
**Answer**: **C** - All pages that have records in `raw_paragraph_images` or `raw_diagram_images` (ensures workflow order)

### Q15: Knowledge Unit Type Distinction
**Question**: How to distinguish paragraph-type vs diagram-type KUs?
**Answer**: **A** - Use `attr9_value` (layout_class_type) only - no other distinction needed

### Q16: Bidirectional Linking Implementation
**Question**: Which columns for bidirectional linking?
**Answer**: Use `attr12_value` for KU → Raw reference (not repurposing attr1)
- Raw tables → KU: `linked_knowledge_unit_id` column (already exists)
- KU → Raw tables: `attr12_value` = "raw_entity_reference"

### Q17: Existing Extraction Service Behavior
**Question**: Should extraction service be modified?
**Answer**: **A** - Keep extraction service unchanged, add a NEW separate service for "Create Knowledge Units"

### Q18: Claude Processing Scope
**Question**: What should "Execute Diagram Analysis" process?
**Answer**: **B** - Expand to process ALL types in `raw_diagram_images` (diagram, table, equation, question, answer, lists)

### Q19: Workflow Order Enforcement
**Question**: Should system enforce workflow order?
**Answer**: **A** - Yes, button disabled/hidden until extraction completes for at least some pages

**Additional UI Requirement**: Pipeline page should show a table with:
- Checkbox (for selection)
- Page Number
- Thumbnails with layout overlay
- Status of execution of the pipeline
- Select all functionality

### Q20: Knowledge Unit for Paragraphs - Text Source
**Question**: Where does `text_content` come from for regular paragraphs?
**Answer**: **A** - Directly from Surya OCR during extraction (already in `raw_paragraph_images.extracted_text`)
- Surya OCR extracts text at 600 DPI

### Q21: Question-Answer Merging Logic
**Question**: How should Q&A be merged into one KU?
**Answer**: **B** - Wait until both question AND answer are processed, then create single KU
- Store question image reference in attr12_value (JSON)
- Store answer image reference in attr12_value (JSON)
- Pipeline sends both images to Claude separately
- Claude responses stored: question → `text_content`, answer → `attr11_value`

**Additional Requirement**: Pipeline must be able to follow image references and retrieve actual image data from raw tables for Claude processing.

### Q22: Handling Unlinked Answers
**Question**: What should happen if an answer region has no linked question?
**Answer**: **D** - Show error/warning, require user to fix linking first
- Add validation in Layout Review: page can't be "Ready for Extraction" if answer has no linked question
- Same pattern as diagram-to-paragraph validation
- Same red rectangle animation as orphan diagrams

### Q23: Standalone Questions (No Answer)
**Question**: What should happen if a question has no linked answer?
**Answer**: **C** - Show error/warning in Layout Review, require user to either link an answer or delete the question
- Same red rectangle animation as orphan diagrams

### Q24: List and Equation Validation
**Question**: Should lists require a linked parent paragraph?
**Answer**: **A** - Yes, same validation as diagrams
- Lists must have parent paragraph
- Equations must have parent paragraph
- Same red rectangle animation for orphans

### Q25 & Q26: Prompt Types
**Question**: What prompts are available for different diagram types?
**Answer**: All 8 prompt types already exist and are customizable in Book Settings:
- ✅ diagram
- ✅ table
- ✅ equation
- ✅ list_bulleted
- ✅ list_numbered
- ✅ list_lettered
- ✅ question
- ✅ answer

Prompts are stored in `auto_slicer_config.extraction_prompts` JSON field.

### Q27: Image Reference Storage for Q&A
**Question**: How to store references to both question and answer images?
**Answer**: **C** - Store both in `attr12_value` as JSON:
```json
{"question": "diagram:123", "answer": "diagram:456"}
```
Pipeline page will parse this JSON, extract the IDs, and retrieve actual images from `raw_diagram_images` table for Claude analysis.

### Q28: Pipeline Page Location
**Question**: Where should "Create Knowledge Units" functionality be added?
**Answer**: **A** - Add to existing Pipeline page

**Additional Requirements**:
1. **Header reorder** (left to right): Upload → Auto-Slicer → Extraction → Pipeline → Library → (rest of existing links)
2. **Page descriptions**: Add a one-line description at the top of each page explaining its purpose

---

## Attribute Mapping Summary

| Attribute | Name | Purpose |
|-----------|------|---------|
| `attr1_value` | related_image | (Keep original purpose) |
| `attr2_value` | preliminary_ocr_text | Preliminary OCR text for all types (before Claude) |
| `attr3_value` | surya_ocr_text | (Keep original purpose) |
| `attr4_value` | tesseract_text | (Keep original purpose) |
| `attr5_value` | easyocr_confidence | (Keep original purpose) |
| `attr6_value` | surya_ocr_confidence | (Keep original purpose) |
| `attr7_value` | tesseract_confidence | (Keep original purpose) |
| `attr8_value` | record_status | (Keep original purpose) |
| `attr9_value` | layout_class_type | Original layout class (paragraph, diagram, table, equation, list_*, question, answer) |
| `attr10_value` | parent_paragraph_text | OCR text of linked parent paragraph (for non-paragraph types) |
| `attr11_value` | answer_text | Answer text for Q&A pairs (question in text_content) |
| `attr12_value` | raw_entity_reference | JSON reference to raw table(s): `{"question": "diagram:123", "answer": "diagram:456"}` or `"paragraph:123"` or `"diagram:456"` |

---

## Layout Class to Storage Mapping

| Layout Class | Raw Table | KU Type | Parent Required | Notes |
|--------------|-----------|---------|-----------------|-------|
| paragraph | raw_paragraph_images | paragraph | No | Text from Surya OCR at 600 DPI |
| title_level_3 | N/A | N/A | N/A | Only used to populate sub_topic field |
| diagram | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| table | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| equation | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| list_bulleted | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| list_numbered | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| list_lettered | raw_diagram_images | diagram | Yes (paragraph) | Text from Claude |
| question | raw_diagram_images | diagram | Yes (answer) | Paired with answer, text from Claude |
| answer | raw_diagram_images | diagram | Yes (question) | Linked to question, text from Claude |

---

## Validation Rules for "Ready for Extraction"

| Region Type | Validation Required | Animation on Failure |
|-------------|---------------------|---------------------|
| paragraph | None | N/A |
| diagram | Must have parent paragraph | Red rectangle |
| table | Must have parent paragraph | Red rectangle |
| equation | Must have parent paragraph | Red rectangle |
| list_* | Must have parent paragraph | Red rectangle |
| question | Must have linked answer | Red rectangle |
| answer | Must have linked question | Red rectangle |

---

## Workflow Summary

1. **Layout Detection** - YOLO detects regions on pages
2. **Layout Review** - User corrects regions, links:
   - Diagrams/tables/equations/lists → parent paragraphs
   - Answers → questions
   - Questions → answers
3. **Mark Ready** - User marks pages as "Ready for Extraction" (validation enforced)
4. **Extraction** - Runs Surya OCR at 600 DPI, stores in raw_paragraph_images and raw_diagram_images
5. **Create Knowledge Units** (NEW) - Creates KU records from raw tables:
   - Paragraphs: direct copy of OCR text to text_content
   - Q&A pairs: merged into single KU with image references
   - Other diagrams: skeleton KU with image reference
6. **Execute Diagram Analysis** - Sends all raw_diagram_images types to Claude for text extraction

---

## Pipeline Page UI Requirements

### Page Table Columns:
1. Checkbox (for selection, with "Select All" header)
2. Page Number
3. Thumbnail (with layout overlay)
4. Layout Status (detected/reviewed/ready)
5. Extraction Status (pending/completed)
6. KU Creation Status (pending/completed)
7. Claude Analysis Status (pending/completed)

### Action Buttons:
1. **"Create Knowledge Units"** - processes selected pages
   - Disabled until extraction completes for selected pages
2. **"Execute Diagram Analysis"** - sends diagrams to Claude
   - Processes ALL types in raw_diagram_images (expanded scope)

### Workflow Enforcement:
- Buttons disabled based on prerequisite completion
- Visual indicators for each status

---

## Header Navigation Order

**New Order (left to right):**
1. 📤 Upload
2. 🔪 Auto-Slicer
3. 📦 Extraction
4. ⚙️ Pipeline
5. 📚 Library
6. (rest of existing links)

---

## Page Descriptions

Each page should have a one-line description at the top:

| Page | Description |
|------|-------------|
| Upload | Upload PDF documents to create new books for processing |
| Auto-Slicer | Detect and configure layout regions on book pages using YOLO |
| Layout Review | Review and correct detected regions, link diagrams to paragraphs |
| Extraction | Extract text and images from reviewed pages using Surya OCR |
| Pipeline | Create knowledge units and run Claude analysis on extracted content |
| Library | Browse and manage all uploaded books |
| Verify Pages | Manually verify and edit extracted knowledge units |
| Book Settings | Configure book-specific settings, prompts, and attributes |

---

## Next Steps

1. ✅ Requirements gathering complete (Q1-Q28)
2. ⏳ Create detailed design document
3. ⏳ Create implementation tasks
4. ⏳ Implement changes

---

## Open Questions

*None - Requirements gathering complete*
