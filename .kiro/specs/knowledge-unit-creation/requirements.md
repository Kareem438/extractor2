# Knowledge Unit Creation from Layout Review - Requirements

## Overview
Extend the Layout Review/Extraction workflow to create Knowledge Units from extracted content, enabling Claude analysis for diagrams, tables, equations, lists, and Q&A pairs.

## User Stories

### US-1: Create Knowledge Units from Extracted Content
As a user, I want to create knowledge units from extracted paragraphs and diagrams so that I can process them through the Claude analysis pipeline.

**Acceptance Criteria:**
- 1.1 A "Create Knowledge Units" button exists on the Pipeline page
- 1.2 Button is disabled until extraction completes for selected pages
- 1.3 Clicking the button creates KU records from raw_paragraph_images and raw_diagram_images
- 1.4 Paragraphs get text_content from Surya OCR (extracted_text field)
- 1.5 Diagrams get skeleton KU with image reference in attr12_value
- 1.6 Q&A pairs are merged into single KU with both image references

### US-2: Bidirectional Linking
As a user, I want knowledge units linked to their source raw records so that I can trace data lineage.

**Acceptance Criteria:**
- 2.1 Raw tables have linked_knowledge_unit_id pointing to created KU
- 2.2 KU has attr12_value with reference format "paragraph:123" or "diagram:456"
- 2.3 Q&A KUs have JSON format: {"question": "diagram:123", "answer": "diagram:456"}

### US-3: Attribute Population
As a user, I want knowledge units populated with correct attributes so that I can identify their type and context.

**Acceptance Criteria:**
- 3.1 attr9_value contains layout_class_type (paragraph, diagram, table, etc.)
- 3.2 attr10_value contains parent_paragraph_text for non-paragraph types
- 3.3 attr11_value contains answer_text for Q&A pairs
- 3.4 attr2_value contains preliminary OCR text for all types
- 3.5 chapter/topic/sub_topic contain L1/L2/L3 titles

### US-4: Layout Review Validation
As a user, I want validation in Layout Review so that I cannot mark pages ready with orphan regions.

**Acceptance Criteria:**
- 4.1 Diagrams without parent paragraph show red rectangle animation
- 4.2 Tables without parent paragraph show red rectangle animation
- 4.3 Equations without parent paragraph show red rectangle animation
- 4.4 Lists without parent paragraph show red rectangle animation
- 4.5 Questions without linked answer show red rectangle animation
- 4.6 Answers without linked question show red rectangle animation
- 4.7 Page cannot be marked "Ready for Extraction" with orphan regions

### US-5: Pipeline Page UI
As a user, I want a table view on Pipeline page to see page status and select pages for processing.

**Acceptance Criteria:**
- 5.1 Table shows: checkbox, page number, thumbnail, layout status, extraction status, KU status, Claude status
- 5.2 "Select All" checkbox in header
- 5.3 Thumbnails show layout overlay
- 5.4 Status columns show pending/completed indicators
- 5.5 "Create Knowledge Units" button processes selected pages
- 5.6 "Execute Diagram Analysis" processes all raw_diagram_images types

### US-6: Header Navigation Reorder
As a user, I want navigation links ordered by workflow so that I can follow the process flow.

**Acceptance Criteria:**
- 6.1 Header order: Upload → Auto-Slicer → Extraction → Pipeline → Library → rest
- 6.2 All pages have consistent header

### US-7: Page Descriptions
As a user, I want a description on each page so that I understand its purpose.

**Acceptance Criteria:**
- 7.1 Each page has one-line description below header
- 7.2 Descriptions explain page purpose in workflow context

### US-8: Claude Analysis Expansion
As a user, I want Claude analysis to process all diagram types so that questions, answers, and lists are decoded.

**Acceptance Criteria:**
- 8.1 "Execute Diagram Analysis" processes: diagram, table, equation, list_*, question, answer
- 8.2 Pipeline retrieves images from raw tables using attr12_value references
- 8.3 Q&A pairs send both images to Claude (separate requests)
- 8.4 Question response stored in text_content
- 8.5 Answer response stored in attr11_value

## Dependencies
- Existing extraction service (unchanged)
- Existing Claude batch service (expanded)
- Existing Layout Review page (validation added)
- Existing Pipeline page (UI enhanced)

## References
- Requirements Document: `02-architecture/KNOWLEDGE-UNIT-CREATION-REQUIREMENTS.md`
- Progress Tracking: `02-architecture/KU-CREATION-PROGRESS.md`
