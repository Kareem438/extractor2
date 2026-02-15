# Requirements Document

## Introduction

This feature integrates Qwen VL vision models via Alibaba Cloud DashScope as a cloud-based alternative to the existing local OCR pipeline for Arabic PDF book processing. The user performs layout detection on a few pages (using existing DocLayout-YOLO), those annotated pages become few-shot prompts for Qwen, and Qwen processes remaining pages returning structured JSON. Results are stored as "knowledge_pages" (logical groupings between L3 titles), reviewed by the user in a layout-review-style UI, then converted to individual Knowledge Unit records. Phase 2 (not in scope) will add DeepSeek-R1 for reasoning, pipeline integration, and cost tracking.

## Glossary

- **Qwen_Service**: The service module that communicates with the DashScope API to invoke Qwen VL models for vision-based text extraction from page images.
- **Few_Shot_Prompt_Builder**: The component that constructs few-shot prompts from user-annotated pages (layout-detected via DocLayout-YOLO) to guide Qwen on the expected structured output format.
- **Cloud_OCR_Router**: The API route handler that exposes endpoints for cloud-based OCR operations (start, pause, resume, cancel, retry-failed, status).
- **Knowledge_Page**: A logical grouping of all elements between two consecutive L3 titles. One physical page can contain multiple knowledge_pages; one knowledge_page can span multiple physical pages. Stored as JSONB in the database.
- **Knowledge_Unit (KU)**: A structured data record representing an extracted piece of knowledge (paragraph, diagram, Q&A pair) stored in the database. Created by "exploding" knowledge_pages.
- **DashScope**: Alibaba Cloud's API platform providing access to Qwen VL models with implicit prompt caching (20% cost for cached tokens).
- **Annotated_Page**: A page marked "Ready for Extraction" that has been processed through DocLayout-YOLO layout detection, with bounding boxes and element classifications available. Used as few-shot examples for Qwen.

## Requirements

### Requirement 1: DashScope API Configuration

**User Story:** As a system administrator, I want to configure API keys and endpoints for DashScope, so that the system can authenticate with the Qwen VL cloud provider.

#### Acceptance Criteria

1. THE Settings class SHALL include configuration fields for `DASHSCOPE_API_KEY` and `DASHSCOPE_BASE_URL` with a default base URL of `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`.
2. WHEN the `.env` file contains DashScope credentials, THE Settings class SHALL load the credentials following the existing `ANTHROPIC_API_KEY` pattern.
3. IF the `DASHSCOPE_API_KEY` is missing or empty when a cloud OCR operation is requested, THEN THE Cloud_OCR_Router SHALL return an HTTP 400 error with a descriptive message identifying the missing credential.
4. THE `.env.example` file SHALL document `DASHSCOPE_API_KEY` and `DASHSCOPE_BASE_URL` with descriptions and placeholder values.

### Requirement 2: Qwen Vision-Based Text Extraction

**User Story:** As a user, I want to use Qwen VL to extract Arabic text from scanned PDF pages, so that I can replace the local OCR workflow with a more accurate cloud-based alternative.

#### Acceptance Criteria

1. WHEN a user initiates cloud OCR for a book, THE Qwen_Service SHALL send page images to the DashScope API using the user-selected Qwen VL model (e.g., `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash`).
2. WHEN processing a page image, THE Qwen_Service SHALL include the image as a base64-encoded payload in the vision message format expected by the DashScope OpenAI-compatible API.
3. THE Qwen_Service SHALL return extracted text as a JSON array per page, where each element contains: `text` (Arabic content), `type` (paragraph/heading/footnote/verse/diagram/question/answer/equation), `level_3_title` (sub-topic or null), `confidence` (0-1), `order` (reading order), `bbox` ([x, y, width, height]).
4. WHEN processing multiple pages, THE Qwen_Service SHALL process pages sequentially (default: 1 page at a time) to respect API rate limits.
5. IF the DashScope API returns a rate-limit error (HTTP 429), THEN THE Qwen_Service SHALL retry the request with exponential backoff up to 3 attempts.
6. IF the DashScope API returns a non-recoverable error (HTTP 4xx other than 429, or 5xx after retries), THEN THE Qwen_Service SHALL log the error, mark the page as `"failed"`, and continue processing remaining pages.
7. THE Qwen_Service SHALL place few-shot example images as a fixed prefix in the prompt (system message or first content block) to enable DashScope implicit prompt caching.

### Requirement 3: Few-Shot Prompt Construction

**User Story:** As a user, I want to use my DocLayout-YOLO annotated pages as few-shot examples for Qwen, so that the model understands the expected output structure for my specific book's layout.

#### Acceptance Criteria

1. WHEN cloud OCR is started, THE Few_Shot_Prompt_Builder SHALL use all pages marked "Ready for Extraction" as few-shot examples, retrieving their page images and corresponding layout detection results from the database.
2. THE Few_Shot_Prompt_Builder SHALL construct a prompt prefix that includes the annotated page images paired with their expected structured JSON output as demonstration examples.
3. WHEN constructing few-shot prompts, THE Few_Shot_Prompt_Builder SHALL support between 1 and 10 example pages (inclusive).
4. IF a selected example page has no layout detection results, THEN THE Few_Shot_Prompt_Builder SHALL skip that page and log a warning.
5. THE Few_Shot_Prompt_Builder SHALL format each example to show the input (page image) and the expected output (JSON array with element classifications, text, bbox, type, and reading order).
6. THE few-shot prefix SHALL be identical across all page requests for a given extraction run, enabling DashScope implicit caching (cached tokens billed at 20% of standard price).

### Requirement 4: Cloud OCR API Endpoints and Execution Control

**User Story:** As a user, I want API endpoints to trigger, pause, resume, cancel, and monitor cloud OCR processing, so that I can control the cloud workflow through the same interface patterns as local OCR.

#### Acceptance Criteria

1. THE Cloud_OCR_Router SHALL expose a `POST /api/cloud-ocr/start/{book_id}` endpoint that accepts the selected Qwen model name and optional page range parameters. Pages marked "Ready for Extraction" are automatically used as few-shot samples.
2. THE Cloud_OCR_Router SHALL expose a `GET /api/cloud-ocr/status/{book_id}` endpoint that returns the current processing status including pages completed, pages failed, pages pending, and current page being processed.
3. THE Cloud_OCR_Router SHALL expose `POST /api/cloud-ocr/pause/{book_id}`, `POST /api/cloud-ocr/resume/{book_id}`, and `POST /api/cloud-ocr/cancel/{book_id}` endpoints following the existing auto-slicer pause/resume pattern (cooperative pause after current page completes).
4. THE Cloud_OCR_Router SHALL expose a `POST /api/cloud-ocr/retry-failed/{book_id}` endpoint that retries only pages with status `"failed"`.
5. WHEN cloud OCR is started, THE Cloud_OCR_Router SHALL run processing as a background task and return immediately with a status of `"processing"`.
6. EACH page SHALL be tracked independently with its own status (`pending`, `processing`, `completed`, `failed`) persisted in the database so progress survives server restarts.

### Requirement 5: Knowledge Pages Table and Translation Layer

**User Story:** As a user, I want Qwen's structured output stored as knowledge_pages grouped by L3 title sections, so that I can review logical content groupings before converting them to individual KU records.

#### Acceptance Criteria

1. THE system SHALL create a `{prefix}_knowledge_pages` table with columns: `id`, `l3_title`, `start_page`, `end_page`, `l1_title_id`, `l2_title_id`, `l1_title_text`, `l2_title_text`, `content` (JSONB), `ocr_engine`, `model_name`, `cached_tokens`, `total_input_tokens`, `total_output_tokens`, `status`, `created_at`, `updated_at`.
2. WHEN Qwen returns JSON for a page, THE translation layer SHALL group elements by `level_3_title` across pages — elements sharing the same L3 title (even across physical pages) form one knowledge_page.
3. FOR each knowledge_page, THE translation layer SHALL resolve L1 and L2 titles by looking up the page number against the existing `level1_titles` and `level2_titles` tables (page range matching).
4. THE `content` JSONB column SHALL store the full element array with structure: `{"elements": [{"type": "...", "text": "...", "page_number": N, "bbox": [x,y,w,h], "confidence": 0.95, "order": 1, "metadata": {}}]}`.
5. THE `status` column SHALL support values: `extracted`, `reviewed`, `ready_to_convert`, `converted`.
6. A database migration script SHALL be created to add the `{prefix}_knowledge_pages` table for existing books.

### Requirement 6: Knowledge Page Review UI

**User Story:** As a user, I want to review and edit knowledge_pages in a layout-review-style interface before converting them to KU records, so that I can correct extraction errors and verify the structured output.

#### Acceptance Criteria

1. THE knowledge_page review UI SHALL reuse the existing layout-review page patterns: page navigation (prev/next), canvas-based page image rendering with element overlays, collapsible sidebar, Arabic mode, and zoom controls.
2. THE review UI SHALL display knowledge_page JSON elements as visual overlays on the page image, showing bounding boxes color-coded by element type.
3. THE sidebar SHALL show editable fields for each element: Arabic text content, element type, L3 title assignment, and reading order.
4. THE user SHALL be able to add, remove, and reorder elements within a knowledge_page.
5. THE review UI SHALL provide a per-page "Ready to Convert to KU" toggle button, following the same pattern as the existing "Ready for Extraction" toggle in layout-review.
6. WHEN a user marks a knowledge_page as "Ready to Convert to KU", THE system SHALL update the knowledge_page status to `ready_to_convert`.

### Requirement 7: Knowledge Page to KU Conversion

**User Story:** As a user, I want to convert reviewed knowledge_pages into individual Knowledge Unit records, so that the existing pipeline (extraction dashboard, cross-book audit, etc.) can work with the cloud-extracted data.

#### Acceptance Criteria

1. THE Cloud_OCR_Router SHALL expose a `POST /api/cloud-ocr/convert-to-ku/{book_id}` endpoint that converts all knowledge_pages with status `ready_to_convert` into individual KU records.
2. FOR each element in a knowledge_page, THE conversion process SHALL create a `raw_paragraph_images` row with: `page_number`, `selection_x/y/width/height` (from bbox), `extracted_text` (from text), `level_1_title`, `level_2_title`, `level_3_title`, `display_order` (from order), `ocr_confidence` (from confidence).
3. THE conversion process SHALL crop the page image using the element's bbox to generate `image_data` (BYTEA) for each `raw_paragraph_images` row.
4. AFTER creating `raw_paragraph_images` rows, THE conversion process SHALL invoke the existing `create_knowledge_units_for_pages()` function to create final KU records.
5. WHEN conversion completes for a knowledge_page, THE system SHALL update its status from `ready_to_convert` to `converted`.
6. THE conversion SHALL be idempotent — re-converting an already-converted knowledge_page SHALL delete the previously created KU records and recreate them.

### Requirement 8: Cloud Extraction UI on Auto-Slicer Page

**User Story:** As a user, I want cloud extraction controls on the auto-slicer page, so that I can trigger and monitor cloud OCR alongside the existing local OCR controls.

#### Acceptance Criteria

1. THE auto-slicer page SHALL include a new "Cloud Extraction" section visually distinct from the existing local OCR section.
2. THE "Cloud Extraction" section SHALL include: a model selection dropdown (listing available Qwen VL models), a "Start Cloud Extraction" button, and Pause/Resume/Cancel buttons following the existing auto-slicer button pattern.
3. THE section SHALL display a progress indicator showing: pages completed, pages failed, pages remaining, and current page being processed.
4. WHEN cloud extraction completes, THE section SHALL display a link to the knowledge_page review UI.
5. THE model selection dropdown SHALL include at minimum: `qwen-vl-max`, `qwen3-vl-plus`, `qwen3-vl-flash`.

### Requirement 9: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging for cloud API interactions, so that I can diagnose issues and monitor system health.

#### Acceptance Criteria

1. WHEN a cloud API call is made, THE Qwen_Service SHALL log the request metadata (model, page number, token estimate) at INFO level.
2. WHEN a cloud API call fails, THE Qwen_Service SHALL log the full error response at ERROR level including HTTP status code and response body.
3. WHEN a cloud API call succeeds, THE Qwen_Service SHALL log the response metadata (tokens used, processing time, cache hit status) at INFO level.
4. IF an unexpected exception occurs during cloud processing, THEN THE Cloud_OCR_Router SHALL catch the exception, log it at ERROR level, and return an HTTP 500 response with a generic error message.
