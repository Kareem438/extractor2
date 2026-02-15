# Main Steps - Active Tasks

**Last Updated:** 2026-02-09  
**Framework:** See [00-tracking-framework.md](00-tracking-framework.md) for full rules (v2)

---

## Database Backup Tracking

| Field | Value |
|-------|-------|
| **Last Backup Date** | 2026-02-12 |
| **Reminder Interval** | Every 2 days |
| **Database** | `knowledge_extraction_2` |

**Backup Command (copy-paste ready):**
```powershell
pg_dump -U postgres -d knowledge_extraction_2 -F c -f "H:\13-extractor2\backups\knowledge_extraction_2_$(Get-Date -Format 'yyyy-MM-dd').backup"
```

⚠️ **REMINDER:** If 2+ days since last backup, remind user to run the backup command above.

---

## Active Tasks (Last 21 Days)

### Task 1: Build Task Tracking Framework
- **Date:** 2026-02-09
- **Status:** ✅ Completed
- **Summary:**
  Build a comprehensive tracking framework to maintain full context across sessions.
  Creates requirement, tracking, and testing files per task.
  Central index (this file) tracks all active tasks with statuses.
  Integrates with steering files for automatic session loading.
  Replaces ad-hoc session summaries with structured tracking.
- **Requirements Gathering:** ✅ Complete (10 questions answered)
- **Execution Status:** ✅ Completed
- **Files:**
  - Requirement: [09-02-requirement-tracking-framework.md](09-02-requirement-tracking-framework.md)
  - Tracking: [09-02-tracking-tracking-framework.md](09-02-tracking-tracking-framework.md)
  - Testing: [09-02-testing-tracking-framework.md](09-02-testing-tracking-framework.md)

### Task 2: Tracking Framework v2 Upgrade
- **Date:** 2026-02-09
- **Status:** ✅ Completed
- **Summary:**
  Upgrade tracking framework to enforce API-first development approach.
  Add design document as a 4th file per task alongside requirement, tracking, testing.
  Ensure steering files enforce design-first implementation.
  Add test object cleanup tracking and DB backup reminders every 2 days.
  Enable autonomous execution after design verification round.
- **Requirements Gathering:** ✅ Complete (10 questions answered)
- **Execution Status:** ✅ Completed
- **Design Deviations:** None
- **Files:**
  - Requirement: [09-02-requirement-framework-v2-upgrade.md](09-02-requirement-framework-v2-upgrade.md)
  - Tracking: [09-02-tracking-framework-v2-upgrade.md](09-02-tracking-framework-v2-upgrade.md)
  - Testing: [09-02-testing-framework-v2-upgrade.md](09-02-testing-framework-v2-upgrade.md)

### Task 3: Cloud OCR Approach (Qwen 2.5-VL + DeepSeek-R1)
- **Date:** 2026-02-12
- **Status:** 🔄 Requirements Gathering
- **Summary:**
  Integrate cloud-based AI models as alternative OCR/analysis engines.
  Qwen 2.5-VL (72B) via OpenRouter for Arabic PDF vision/OCR extraction.
  DeepSeek-R1 via DeepSeek API for reasoning and deep text analysis.
  Plugs into existing OCR pipeline alongside EasyOCR/Surya/PaddleOCR.
  Follows existing claude_batch_service.py pattern for external API integration.
- **Requirements Gathering:** ✅ Complete (Q1-Q10 answered)
- **Execution Status:** Not Started — Design verification next
- **Design Deviations:** None (yet)
- **Files:**
  - Requirement: [12-02-requirement-cloud-ocr-approach.md](12-02-requirement-cloud-ocr-approach.md)
  - Design: [12-02-design-cloud-ocr-approach.md](12-02-design-cloud-ocr-approach.md)
  - Tracking: [12-02-tracking-cloud-ocr-approach.md](12-02-tracking-cloud-ocr-approach.md)
  - Testing: [12-02-testing-cloud-ocr-approach.md](12-02-testing-cloud-ocr-approach.md)

### Task 4: Export Pages to Folder
- **Date:** 2026-02-14
- **Status:** ⏸️ Paused (Requirements Gathering — Q1 pending)
- **Summary:**
  Export book page images to a local folder with user-defined naming convention.
  User provides a folder path and a filename template containing `ppp` as page number placeholder.
  Each page image from the database is saved to the folder following the naming convention.
  Page number increments automatically across all exported pages.
  Reads from `raw_{prefix}_pages` table (original_image_data, original_format).
- **Requirements Gathering:** ⏸️ Paused at Q1 (0 questions answered)
- **Execution Status:** Not Started
- **Design Deviations:** None (yet)
- **Files:**
  - Requirement: [14-02-requirement-export-pages-to-folder.md](14-02-requirement-export-pages-to-folder.md)
  - Design: [14-02-design-export-pages-to-folder.md](14-02-design-export-pages-to-folder.md)
  - Tracking: [14-02-tracking-export-pages-to-folder.md](14-02-tracking-export-pages-to-folder.md)
  - Testing: [14-02-testing-export-pages-to-folder.md](14-02-testing-export-pages-to-folder.md)

### Task 5: Rolling API XML Extraction
- **Date:** 2026-02-14
- **Status:** 🔄 Requirements Gathering
- **Summary:**
  Call external APIs with 3 pages of the book at a time in a rolling window fashion.
  Each API call sends 3 page images and receives XML output.
  Rolling means: pages 1-2-3, then 2-3-4, then 3-4-5, etc. (or similar sliding window).
  XML output is parsed and stored per page/section.
  Complex task requiring detailed requirements analysis.
- **Requirements Gathering:** 🔄 In Progress
- **Execution Status:** Not Started
- **Design Deviations:** None (yet)
- **Files:**
  - Requirement: [14-02-requirement-rolling-api-xml-extraction.md](14-02-requirement-rolling-api-xml-extraction.md)
  - Design: [14-02-design-rolling-api-xml-extraction.md](14-02-design-rolling-api-xml-extraction.md)
  - Tracking: [14-02-tracking-rolling-api-xml-extraction.md](14-02-tracking-rolling-api-xml-extraction.md)
  - Testing: [14-02-testing-rolling-api-xml-extraction.md](14-02-testing-rolling-api-xml-extraction.md)

---

## Completed Tasks

_(No completed tasks yet)_

---

## Archive Reference

_(No archives yet. Tasks older than 21 days will be moved to `00-main-steps-ARCHIVE-mm-yyyy.md`)_
