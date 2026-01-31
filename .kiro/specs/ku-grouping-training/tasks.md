# Requirement 7: Implementation Tasks

## KU Grouping, Multi-Tag Extraction & YOLO Fine-Tuning

**Created:** January 29, 2026
**Status:** ✅ COMPLETE - All Phases Verified

---

## Phase 0: Expandable Help System

- [x] 0.1 Create expandable help component
  - [x] 0.1.1 Add CSS for expandable help section
  - [x] 0.1.2 Add JavaScript for toggle functionality
  - [x] 0.1.3 Add help content for pipeline-config page
  - [x] 0.1.4 Add help content for pipeline-dashboard page

---

## Phase 1: Multi-Tag XML Extraction (7A)

- [x] 1.1 Database Migration - Add tag_mappings columns
  - [x] 1.1.1 Create migration script for tag_mappings JSONB column in pipeline_config
  - [x] 1.1.2 Add fallback_attribute column to pipeline_config
  - [x] 1.1.3 Run migration on existing books

- [x] 1.2 Backend API - Tag mapping endpoints
  - [x] 1.2.1 Add PUT endpoint for tag mappings in pipeline.py
  - [x] 1.2.2 Add GET endpoint for tag mappings in pipeline.py
  - [x] 1.2.3 Add tag validation logic

- [x] 1.3 Response Parser - Multi-tag extraction
  - [x] 1.3.1 Create parse_multi_tag_response function in claude_batch_service.py
  - [x] 1.3.2 Add fallback attribute handling for unmapped tags
  - [x] 1.3.3 Add incomplete status tracking for missing required tags

- [x] 1.4 Frontend UI - Tag mapping table
  - [x] 1.4.1 Add tag mapping section to pipeline-config.html
  - [x] 1.4.2 Add JavaScript for dynamic tag mapping rows
  - [x] 1.4.3 Add fallback attribute dropdown

---

## Phase 2: Knowledge Unit Grouping (7B)

- [x] 2.1 Database Migration - Grouping config and attributes
  - [x] 2.1.1 Create ku_grouping_config table
  - [x] 2.1.2 Add 80 additional custom attributes (attr_81 through attr_160)
  - [x] 2.1.3 Add is_complete and incomplete_reason columns to knowledge_units

- [x] 2.2 Backend Service - KU Grouper
  - [x] 2.2.1 Create ku_grouper_service.py with grouping logic
  - [x] 2.2.2 Implement get_grouping_preview function
  - [x] 2.2.3 Implement create_groups function
  - [x] 2.2.4 Implement build_grouped_prompt function
  - [x] 2.2.5 Implement distribute_response function (parse_grouped_response)

- [x] 2.3 Token Estimation
  - [x] 2.3.1 Add tiktoken dependency for token estimation
  - [x] 2.3.2 Implement estimate_tokens function

- [x] 2.4 Backend API - Grouping endpoints
  - [x] 2.4.1 Add grouping preview endpoint
  - [x] 2.4.2 Add token estimation endpoint
  - [x] 2.4.3 Add grouping config endpoint
  - [x] 2.4.4 Add execution mode endpoint (individual/grouped/incomplete)

- [x] 2.5 Frontend UI - Grouping configuration
  - [x] 2.5.1 Add grouping preview table to pipeline-dashboard.html
  - [x] 2.5.2 Add execution mode selector
  - [x] 2.5.3 Add dry run checkbox
  - [x] 2.5.4 Add token preview button

---

## Phase 3: YOLO Fine-Tuning (7C)

- [x] 3.1 Database Migration - Correction storage
  - [x] 3.1.1 Create layout_corrections table
  - [x] 3.1.2 Add indexes for efficient queries
  - [x] 3.1.3 Add correction columns to layout_detections table

- [x] 3.2 Backend Service - Correction tracking
  - [x] 3.2.1 Backend already stores original regions on first correction (update_region endpoint)
  - [x] 3.2.2 Correction statistics endpoint added
  - [x] 3.2.3 Training data export endpoint added

- [x] 3.3 Backend Service - Training data export
  - [x] 3.3.1 Create yolo_training_service.py
  - [x] 3.3.2 Implement export_training_data function (YOLO format)
  - [x] 3.3.3 Implement get_training_statistics function

- [x] 3.4 Backend Service - Model training
  - [x] 3.4.1 Implement backup_current_model function
  - [x] 3.4.2 Implement start_training function
  - [x] 3.4.3 Implement get_training_progress function

- [x] 3.5 Frontend UI - Training dashboard
  - [x] 3.5.1 Create layout-training.html page
  - [x] 3.5.2 Add training statistics display
  - [x] 3.5.3 Add class distribution chart
  - [x] 3.5.4 Add training progress display

---

## Phase 4: Integration & Testing

- [x] 4.1 Integration testing
  - [x] 4.1.1 Test multi-tag extraction with sample prompts
  - [x] 4.1.2 Test KU grouping with different configurations
  - [x] 4.1.3 Test correction storage and retrieval

- [x] 4.2 End-to-end testing
  - [x] 4.2.1 Test full pipeline with grouped execution
  - [x] 4.2.2 Test dry run mode
  - [x] 4.2.3 Test incomplete KU retry mode

---

## Execution Order

1. Phase 1 (7A) - Foundation for tag extraction
2. Phase 2 (7B) - Builds on 7A for grouped processing
3. Phase 3 (7C) - Independent, can be done in parallel
4. Phase 4 - Integration testing after all phases
