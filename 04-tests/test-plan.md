# Test Plan - Knowledge Extraction System

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-09
**Tester:** Claude (Tester Agent)
**Approach:** Test-First Development (TFD)
**Status:** ✅ Test Plan Complete

---

## 📋 Executive Summary

This test plan defines the complete testing strategy for the Knowledge Extraction System. All tests are generated **BEFORE** development begins, following a strict test-first approach.

**Key Principle:** Developer **CANNOT** proceed to chunk N+1 until **ALL** tests for chunk N pass (100% pass requirement).

---

## 🎯 Testing Philosophy

### Test-First Development (TFD)

1. **Tests Written First:** All test cases generated before any production code
2. **Chunk-by-Chunk:** Each of 45 code chunks has dedicated unit tests
3. **100% Pass Required:** No partial success - all tests must pass before proceeding
4. **Dependency-Ordered:** Tests follow same dependency hierarchy as code chunks

### Quality Gates

| Gate | Requirement | Enforced By |
|------|-------------|-------------|
| **Unit Test Pass** | 100% of unit tests for current chunk | Developer agent |
| **Integration Test Pass** | 100% of integration tests for current level | Developer agent |
| **Code Coverage** | 80%+ line coverage | pytest-cov |
| **No Regressions** | All previous tests still pass | CI/CD pipeline |

---

## 📊 Test Coverage Overview

### Test Pyramid

```
                    /\
                   /  \
                  / E2E\          5 E2E tests
                 /______\
                /        \
               /Integration\      5 integration test suites
              /____________\
             /              \
            /   Unit Tests   \    45 unit test files
           /__________________\
```

### Test Statistics

| Test Level | Test Files | Test Cases (Est.) | Coverage Target |
|------------|------------|-------------------|-----------------|
| **Unit Tests** | 45 files | ~300-400 tests | 80%+ per chunk |
| **Integration Tests** | 5 files | ~50-75 tests | 80%+ per level |
| **End-to-End Tests** | 5 files | ~15-25 tests | Critical workflows |
| **TOTAL** | 55 files | ~400-500 tests | 80%+ overall |

---

## 📦 Test Structure

### Directory Layout

```
04-tests/
├── test-plan.md                    # This file
├── unit/                           # Unit tests (45 files)
│   ├── test_chunk_001.py          # CHUNK-001: Configuration Management
│   ├── test_chunk_002.py          # CHUNK-002: Database Connection
│   ├── test_chunk_003.py          # CHUNK-003: Book Model
│   └── ...                         # (45 total)
├── integration/                    # Integration tests (5 files)
│   ├── test_level0_foundation.py
│   ├── test_level1_core.py
│   ├── test_level2_services.py
│   ├── test_level3_presentation.py
│   └── test_level4_integration.py
├── e2e/                           # End-to-end tests
│   ├── test_workflow_upload.py
│   ├── test_workflow_ocr.py
│   ├── test_workflow_split.py
│   ├── test_workflow_verify.py
│   └── test_workflow_export.py
├── test-cases/                    # Manual test case documentation
├── test-results/                  # Test execution results
├── bug-reports/                   # Bug tracking
└── automated-tests/               # Additional automated test scripts
```

---

## 🧪 Unit Tests (45 Files)

### Purpose
Test each code chunk in isolation with mocked dependencies.

### Test File Naming
- **Pattern:** `test_chunk_{NNN}.py` (e.g., `test_chunk_001.py`)
- **Location:** `04-tests/unit/`
- **One file per chunk** (45 chunks = 45 test files)

### Test Structure per File

```python
"""
Unit tests for CHUNK-{NNN}: {Chunk Name}

Tests:
- Happy path scenarios
- Error handling and edge cases
- Input validation
- Mocked external dependencies
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Test fixtures
@pytest.fixture
def sample_data():
    """Fixture for test data"""
    pass

# Test cases
class TestChunk{NNN}:
    """Test suite for CHUNK-{NNN}"""

    def test_happy_path(self):
        """Test normal operation"""
        pass

    def test_error_handling(self):
        """Test error scenarios"""
        pass

    def test_edge_cases(self):
        """Test boundary conditions"""
        pass

    def test_input_validation(self):
        """Test input validation"""
        pass
```

### Coverage Requirements per Chunk

- ✅ **All functions** in the chunk must be tested
- ✅ **Happy path** - normal operation
- ✅ **Error cases** - exceptions, invalid inputs, failures
- ✅ **Edge cases** - boundary conditions, empty inputs, null values
- ✅ **Mocked dependencies** - database, file I/O, external APIs

---

## 🔗 Integration Tests (5 Files)

### Purpose
Test interaction between chunks within each dependency level.

### Test Files

| File | Dependency Level | Chunks Tested | Purpose |
|------|-----------------|---------------|---------|
| `test_level0_foundation.py` | Level 0 | CHUNK-001 to CHUNK-008 | Config, DB, Models, Utils |
| `test_level1_core.py` | Level 1 | CHUNK-009 to CHUNK-018 | OCR, Splitting, Processing |
| `test_level2_services.py` | Level 2 | CHUNK-019 to CHUNK-030 | API, Background Tasks, WebSocket |
| `test_level3_presentation.py` | Level 3 | CHUNK-031 to CHUNK-040 | UI, Routes, Frontend |
| `test_level4_integration.py` | Level 4 | CHUNK-041 to CHUNK-045 | Full system integration |

### Test Scenarios per Level

**Level 0 (Foundation):**
- Config loads and DB connects successfully
- Models can be created and persisted
- Utility functions work with real dependencies

**Level 1 (Core):**
- OCR engine processes real PDF pages
- Text splitting produces correct knowledge units
- Background tasks execute and update state

**Level 2 (Services):**
- API endpoints return correct responses
- WebSocket broadcasts updates
- Service layer orchestrates operations

**Level 3 (Presentation):**
- UI pages render correctly
- Routes handle requests and responses
- Frontend components interact with backend

**Level 4 (Integration):**
- Complete workflows execute end-to-end
- All system components work together
- Real database operations succeed

---

## 🌐 End-to-End Tests (5 Files)

### Purpose
Test complete user workflows from start to finish with real system.

### Test Files

| File | Workflow | Coverage |
|------|----------|----------|
| `test_workflow_upload.py` | Book Upload | Upload PDF → Extract metadata → Create tables |
| `test_workflow_ocr.py` | OCR Processing | Start OCR → Run 3 engines → Store results |
| `test_workflow_split.py` | Text Splitting | Evaluate → Split → Generate knowledge units |
| `test_workflow_verify.py` | Verification | Load records → User verifies → Update database |
| `test_workflow_export.py` | Export | Generate CSV/JSON → Download → Validate format |

### E2E Test Characteristics

- ✅ **Real database** (test database, not mocked)
- ✅ **Real file I/O** (actual PDF processing)
- ✅ **Real OCR engines** (Tesseract, PaddleOCR, Surya)
- ✅ **Complete workflows** (start to finish)
- ✅ **UI interactions** (Playwright/Selenium for frontend tests)

---

## 🔧 Testing Tools & Frameworks

### Core Testing Stack

| Tool | Purpose | Version |
|------|---------|---------|
| **pytest** | Test framework | 7.4+ |
| **pytest-asyncio** | Async test support | 0.21+ |
| **pytest-cov** | Code coverage | 4.1+ |
| **pytest-mock** | Mocking utilities | 3.11+ |
| **unittest.mock** | Python mocking | Built-in |
| **Playwright** | E2E browser testing | 1.40+ |
| **httpx** | HTTP client testing | 0.25+ |
| **faker** | Test data generation | 20.0+ |

### Database Testing

- **Test Database:** Separate PostgreSQL database for tests
- **Fixtures:** pytest fixtures for database setup/teardown
- **Migrations:** Apply migrations before each test run
- **Cleanup:** Rollback after each test to maintain isolation

### Test Configuration

**pytest.ini:**
```ini
[pytest]
testpaths = 04-tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    --verbose
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

**conftest.py:**
```python
# Global test fixtures
import pytest
from sqlalchemy import create_engine
from src.database.connection import get_session

@pytest.fixture(scope="session")
def test_db():
    """Test database setup"""
    engine = create_engine("postgresql://test:test@localhost/test_db")
    # Apply migrations
    # Yield engine
    # Cleanup
    pass

@pytest.fixture
def db_session(test_db):
    """Database session for tests"""
    session = get_session()
    yield session
    session.rollback()
    session.close()
```

---

## 🎯 Critical Test Areas

### High Priority (Must Test Thoroughly)

1. **OCR Retry Logic**
   - 3-attempt strategy with different engines
   - Failure handling and fallback
   - Confidence score evaluation

2. **Semantic Text Splitting**
   - SBERT-based chunking
   - 3-5 line target with flexibility
   - Coherence score validation

3. **Database Operations**
   - Connection pooling (10 connections)
   - Batch inserts (50 records)
   - Transaction management
   - Foreign key constraints
   - 30-attribute column architecture

4. **Background Task Processing**
   - Celery task execution
   - Checkpoint save/restore
   - Pause/resume functionality
   - Progress tracking

5. **WebSocket Real-Time Updates**
   - Connection management
   - Broadcast to all clients
   - Progress updates
   - Error notifications

6. **Image Processing**
   - Compression (LZ4)
   - Decompression
   - Format conversion
   - Size validation

7. **Record Merge/Split**
   - Merge multiple records into one
   - Split one record into multiple
   - Update record_status correctly
   - Maintain referential integrity

8. **Chroma DB Sync**
   - Async queue sync
   - Merge/split synchronization
   - Metadata-only updates
   - Fresh embedding generation

---

## 📈 Test Execution Strategy

### Execution Order

```
1. Unit Tests (Level 0 - Foundation)
   ↓
2. Unit Tests (Level 1 - Core)
   ↓
3. Unit Tests (Level 2 - Services)
   ↓
4. Unit Tests (Level 3 - Presentation)
   ↓
5. Unit Tests (Level 4 - Integration)
   ↓
6. Integration Tests (All Levels)
   ↓
7. End-to-End Tests (Complete Workflows)
```

### Per-Chunk Workflow

For each chunk (1-45):

```
Step 1: Read chunk specification (breakdown.md)
Step 2: Read corresponding test file (04-tests/unit/test_chunk_{NNN}.py)
Step 3: Implement code for chunk
Step 4: Run unit tests: pytest 04-tests/unit/test_chunk_{NNN}.py
Step 5: Fix code until ALL tests pass
Step 6: Verify 100% test pass
Step 7: Run integration tests for current level
Step 8: If all pass, proceed to next chunk; otherwise, DO NOT PROCEED
```

### Continuous Integration

**On Each Commit:**
- Run all unit tests
- Run integration tests for affected levels
- Generate coverage report
- Fail build if coverage < 80%
- Fail build if any test fails

**On Pull Request:**
- Run full test suite (unit + integration + E2E)
- Require 100% pass before merge
- Require code review approval

---

## 🐛 Bug Tracking & Reporting

### Bug Report Template

```markdown
# Bug Report: {Short Description}

**Discovered During:** {Test Phase}
**Test File:** {test_chunk_XXX.py}
**Severity:** {Critical | High | Medium | Low}
**Status:** {Open | In Progress | Fixed | Closed}

## Description
{Detailed description of the bug}

## Steps to Reproduce
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Expected Behavior
{What should happen}

## Actual Behavior
{What actually happens}

## Test Case
\`\`\`python
{Failing test code}
\`\`\`

## Stack Trace
\`\`\`
{Error stack trace}
\`\`\`

## Fix
{Description of fix, if known}
```

---

## 📊 Test Metrics & Reporting

### Metrics to Track

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test Pass Rate** | 100% | pytest results |
| **Code Coverage** | 80%+ | pytest-cov |
| **Test Execution Time** | < 5 minutes | pytest --durations |
| **Bugs Found** | Track all | Bug reports |
| **Bugs Fixed** | 100% | Bug status |

### Daily Test Report

```
=== Test Execution Report ===
Date: 2025-11-09
Chunks Implemented: 10/45
Tests Run: 100
Tests Passed: 98
Tests Failed: 2
Code Coverage: 82%
Execution Time: 3m 45s

Failed Tests:
- test_chunk_005::test_ocr_retry_logic
- test_chunk_008::test_checkpoint_restore

Action Required:
- Fix failing tests before proceeding to chunk 11
```

---

## ✅ Definition of Done

### For Each Chunk

- ✅ Unit test file created with minimum 4 test cases
- ✅ All unit tests pass (100%)
- ✅ Code coverage ≥ 80% for the chunk
- ✅ Integration tests for the level pass
- ✅ No regressions in previous tests
- ✅ Code reviewed and approved

### For Each Dependency Level

- ✅ All unit tests for level pass
- ✅ Integration test for level passes
- ✅ Code coverage ≥ 80% for level
- ✅ All bugs for level fixed
- ✅ Documentation updated

### For Complete System

- ✅ All 45 unit test files created
- ✅ All unit tests pass (100%)
- ✅ All 5 integration tests pass
- ✅ All 5 E2E tests pass
- ✅ Overall code coverage ≥ 80%
- ✅ Zero critical/high bugs
- ✅ Performance benchmarks met
- ✅ System ready for production

---

## 🚀 Next Steps

1. ✅ **Test Plan Complete** (this document)
2. ⬅️ **Generate Unit Tests** (45 files in 04-tests/unit/)
3. **Generate Integration Tests** (5 files in 04-tests/integration/)
4. **Generate E2E Tests** (5 files in 04-tests/e2e/)
5. **Begin Development** (implement chunks with test-first approach)

---

**Test Plan Status:** ✅ Complete
**Total Test Files to Generate:** 55 (45 unit + 5 integration + 5 E2E)
**Estimated Test Generation Time:** 8-12 hours
**Ready for Test Generation:** Yes
