# Quick Reference - Integration and E2E Tests

## Summary at a Glance

**Total Files:** 10
**Total Lines:** 4,231
**Total Tests:** 177

---

## Integration Tests (5 files, 123 tests)

| File | Lines | Tests | Coverage |
|------|-------|-------|----------|
| test_level0_foundation.py | 426 | 18 | CHUNK-001 to 008 (Config, DB, Models) |
| test_level1_core.py | 490 | 24 | CHUNK-009 to 018 (OCR, PDF, Split) |
| test_level2_services.py | 539 | 26 | CHUNK-019 to 030 (APIs, Tasks, WebSocket) |
| test_level3_presentation.py | 472 | 33 | CHUNK-031 to 040 (UI, Routes, Templates) |
| test_level4_integration.py | 582 | 22 | CHUNK-041 to 045 (Merge, Split, Export) |

---

## E2E Tests (5 files, 54 tests)

| File | Lines | Tests | Workflow |
|------|-------|-------|----------|
| test_workflow_upload.py | 310 | 9 | Upload PDF → Create tables |
| test_workflow_ocr.py | 327 | 9 | Start OCR → 3 engines → Store results |
| test_workflow_split.py | 328 | 10 | Evaluate → Split → Knowledge units |
| test_workflow_verify.py | 339 | 12 | Load → Verify → Update DB |
| test_workflow_export.py | 418 | 14 | Generate → Download → Validate |

---

## Run Tests

```bash
# All integration tests
pytest 04-tests/integration/ -v

# All E2E tests
pytest 04-tests/e2e/ -v

# Everything
pytest 04-tests/ -v --cov=src

# Specific file
pytest 04-tests/integration/test_level0_foundation.py -v
```

---

## Key Features Tested

✅ Config loading & database connection
✅ Dynamic table creation (7 tables/book)
✅ OCR with 3-attempt retry (Tesseract, PaddleOCR, Surya)
✅ PDF text extraction & image conversion
✅ Semantic text splitting with SBERT
✅ Background task processing with Celery
✅ WebSocket real-time updates
✅ Record merge & split operations
✅ Chroma DB vector synchronization
✅ CSV/JSON export with validation
✅ Complete user workflows (upload → export)

---

For detailed information, see: `INTEGRATION_E2E_TEST_SUMMARY.md`
