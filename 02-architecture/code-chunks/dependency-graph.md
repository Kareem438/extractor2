# Dependency Graph - Code Chunk Execution Order

**Project:** Knowledge Extraction System (12-extractor)
**Created:** 2025-11-03
**Total Chunks:** 45
**Status:** ✅ Dependency Graph Complete

---

## 📊 Execution Order Summary

```
LEVEL 0 (Foundation)     → No dependencies
    ↓
LEVEL 1 (Core Logic)     → Depends on Level 0
    ↓
LEVEL 2 (Services)       → Depends on Levels 0-1
    ↓
LEVEL 3 (Presentation)   → Depends on Levels 0-2
    ↓
LEVEL 4 (Integration)    → Depends on all previous levels
```

---

## 🎯 LEVEL 0: FOUNDATION (8 chunks)

**Can be developed in parallel** (no inter-dependencies)

```
CHUNK-001: Configuration Management
CHUNK-002: Database Connection Setup         ← depends on CHUNK-001
CHUNK-003: Books Metadata Model              ← depends on CHUNK-002
CHUNK-004: Sanitization Utilities
CHUNK-005: File Type Detection
CHUNK-006: Pydantic Schemas
CHUNK-007: Logging Setup                     ← depends on CHUNK-001
CHUNK-008: Error Classes
```

### Parallel Development Possible:
- **Group A:** CHUNK-001 → CHUNK-002 → CHUNK-003
- **Group B:** CHUNK-004, CHUNK-005, CHUNK-006, CHUNK-008 (all independent)
- **Group C:** CHUNK-007 (after CHUNK-001)

---

## 🎯 LEVEL 1: CORE LOGIC (10 chunks)

```
CHUNK-009: Dynamic Table Creation            ← CHUNK-002, CHUNK-003
CHUNK-010: OCR Utility (Tesseract)           ← CHUNK-001, CHUNK-008
CHUNK-011: OCR Retry Logic                   ← CHUNK-010
CHUNK-012: PDF Text Extraction               ← CHUNK-008
CHUNK-013: PDF to Image Conversion           ← (no Level 0 dependencies)
CHUNK-014: Language Detection                ← (no Level 0 dependencies)
CHUNK-015: Image Compression (LZ4)           ← (no Level 0 dependencies)
CHUNK-016: Sentence Transformer Loader       ← CHUNK-001
CHUNK-017: Text Chunking Algorithm           ← CHUNK-016
CHUNK-018: BLIP Image Captioning             ← CHUNK-001
```

### Dependencies:
- CHUNK-009: Requires CHUNK-002, CHUNK-003
- CHUNK-010: Requires CHUNK-001, CHUNK-008
- CHUNK-011: Requires CHUNK-010
- CHUNK-016: Requires CHUNK-001
- CHUNK-017: Requires CHUNK-016
- CHUNK-018: Requires CHUNK-001

### Parallel Development Possible:
- **Group A:** CHUNK-009 (after Level 0 Group A)
- **Group B:** CHUNK-010 → CHUNK-011
- **Group C:** CHUNK-012, CHUNK-013, CHUNK-014, CHUNK-015 (independent)
- **Group D:** CHUNK-016 → CHUNK-017
- **Group E:** CHUNK-018

---

## 🎯 LEVEL 2: SERVICES (12 chunks)

```
CHUNK-019: Reader Agent                      ← CHUNK-010, CHUNK-011, CHUNK-012, CHUNK-013, CHUNK-014
CHUNK-020: Splitter Agent                    ← CHUNK-017
CHUNK-021: Marker Agent                      ← CHUNK-013
CHUNK-022: Image-Reader Agent                ← CHUNK-018
CHUNK-023: Agent Orchestrator                ← CHUNK-019, CHUNK-020, CHUNK-021, CHUNK-022
CHUNK-024: DB Service - Knowledge Units      ← CHUNK-002, CHUNK-009
CHUNK-025: DB Service - Images               ← CHUNK-002, CHUNK-009, CHUNK-015
CHUNK-026: DB Service - Pages                ← CHUNK-002, CHUNK-009, CHUNK-015
CHUNK-027: DB Service - Processing State     ← CHUNK-002, CHUNK-009
CHUNK-028: DB Service - Book Settings        ← CHUNK-002, CHUNK-009
CHUNK-029: DB Service - Attribute Keys       ← CHUNK-002, CHUNK-009
CHUNK-030: Background Processing Task        ← CHUNK-023, CHUNK-024-029
```

### Dependencies:
- CHUNK-019: Requires all OCR and PDF chunks
- CHUNK-020: Requires text chunking
- CHUNK-021: Requires PDF to image
- CHUNK-022: Requires BLIP captioning
- CHUNK-023: Requires all 4 agents (CHUNK-019 to CHUNK-022)
- CHUNK-024-029: Require database setup
- CHUNK-030: Requires orchestrator + all DB services

### Parallel Development Possible:
- **Group A:** CHUNK-019, CHUNK-020, CHUNK-021, CHUNK-022 (4 agents in parallel)
- **Group B:** CHUNK-024, CHUNK-025, CHUNK-026, CHUNK-027, CHUNK-028, CHUNK-029 (6 DB services in parallel)
- **Sequential:** CHUNK-023 (after Group A), then CHUNK-030 (after Group B + CHUNK-023)

---

## 🎯 LEVEL 3: PRESENTATION (10 chunks)

```
CHUNK-031: FastAPI Application Setup         ← CHUNK-001, CHUNK-007
CHUNK-032: API Routes - Upload               ← CHUNK-003, CHUNK-004, CHUNK-005, CHUNK-006, CHUNK-009
CHUNK-033: API Routes - Processing Control   ← CHUNK-030
CHUNK-034: API Routes - Books Management     ← CHUNK-003, CHUNK-006
CHUNK-035: API Routes - Knowledge Units      ← CHUNK-024, CHUNK-006
CHUNK-036: API Routes - Images               ← CHUNK-025
CHUNK-037: API Routes - Pages                ← CHUNK-026
CHUNK-038: WebSocket Handler                 ← CHUNK-027
CHUNK-039: HTML Template - Upload Page       ← CHUNK-031
CHUNK-040: JavaScript - Upload Handler       ← CHUNK-032, CHUNK-039
```

### Dependencies:
- CHUNK-031: Foundation only
- CHUNK-032-038: Require corresponding backend services
- CHUNK-039: Requires FastAPI app
- CHUNK-040: Requires upload API + HTML

### Parallel Development Possible:
- **Group A:** CHUNK-031 first
- **Group B:** CHUNK-032, CHUNK-033, CHUNK-034, CHUNK-035, CHUNK-036, CHUNK-037, CHUNK-038 (7 API routes in parallel)
- **Group C:** CHUNK-039, CHUNK-040 (frontend, after CHUNK-031 and CHUNK-032)

---

## 🎯 LEVEL 4: INTEGRATION (5 chunks)

```
CHUNK-041: Database Initialization Script    ← CHUNK-002, CHUNK-003
CHUNK-042: Complete Frontend CSS             ← (no dependencies)
CHUNK-043: Requirements.txt & Setup Script   ← (no dependencies)
CHUNK-044: Configuration Files               ← (no dependencies)
CHUNK-045: Main Entry Point & Documentation  ← ALL PREVIOUS CHUNKS
```

### Dependencies:
- CHUNK-041-044: Can be developed in parallel
- CHUNK-045: Must be last (verifies entire system)

---

## 📈 Visual Dependency Graph (Text-Based)

```
Level 0: Foundation
═══════════════════
[001] Config ──┬──> [002] DB Connection ──> [003] Books Model
               │
               ├──> [007] Logging
               │
               └──> [010] OCR ──> [011] OCR Retry

[004] Sanitization    [005] File Detection    [006] Pydantic    [008] Errors

                        ↓ ↓ ↓
Level 1: Core Logic
═══════════════════
[009] Table Creation  (002, 003)
[010] OCR             (001, 008)
[011] OCR Retry       (010)
[012] PDF Text        (008)
[013] PDF→Image       (-)
[014] Lang Detect     (-)
[015] Compression     (-)
[016] SBERT           (001)
[017] Text Chunk      (016)
[018] BLIP            (001)

                        ↓ ↓ ↓
Level 2: Services
═══════════════════
[019] Reader Agent ────┐
[020] Splitter Agent ──┼──> [023] Orchestrator ──┐
[021] Marker Agent ────┤                          │
[022] Image-Reader ────┘                          │
                                                  │
[024] KU Service ───────┐                         │
[025] Image Service ────┤                         │
[026] Page Service ─────┼──> [030] Background ←──┘
[027] State Service ────┤         Processing
[028] Settings Service ─┤
[029] Attr Key Service ─┘

                        ↓ ↓ ↓
Level 3: Presentation
═══════════════════
[031] FastAPI App ──┬──> [039] HTML Upload ──> [040] JS Upload
                     │
                     ├──> [032] API: Upload
                     ├──> [033] API: Processing
                     ├──> [034] API: Books
                     ├──> [035] API: KU
                     ├──> [036] API: Images
                     ├──> [037] API: Pages
                     └──> [038] WebSocket

                        ↓ ↓ ↓
Level 4: Integration
═══════════════════
[041] DB Init
[042] CSS
[043] Requirements
[044] Config Files
[045] README & Entry ← ALL CHUNKS
```

---

## 🔢 Chunk Dependencies Table

| Chunk | Name | Depends On | Can Start After |
|-------|------|------------|-----------------|
| 001 | Config | - | Immediately |
| 002 | DB Connection | 001 | CHUNK-001 complete |
| 003 | Books Model | 002 | CHUNK-002 complete |
| 004 | Sanitization | - | Immediately |
| 005 | File Detection | - | Immediately |
| 006 | Pydantic Schemas | - | Immediately |
| 007 | Logging | 001 | CHUNK-001 complete |
| 008 | Errors | - | Immediately |
| 009 | Table Creation | 002, 003 | CHUNK-003 complete |
| 010 | OCR | 001, 008 | CHUNK-001, 008 complete |
| 011 | OCR Retry | 010 | CHUNK-010 complete |
| 012 | PDF Text | 008 | CHUNK-008 complete |
| 013 | PDF→Image | - | Immediately |
| 014 | Lang Detect | - | Immediately |
| 015 | Compression | - | Immediately |
| 016 | SBERT | 001 | CHUNK-001 complete |
| 017 | Text Chunk | 016 | CHUNK-016 complete |
| 018 | BLIP | 001 | CHUNK-001 complete |
| 019 | Reader Agent | 010, 011, 012, 013, 014 | CHUNK-014 complete |
| 020 | Splitter Agent | 017 | CHUNK-017 complete |
| 021 | Marker Agent | 013 | CHUNK-013 complete |
| 022 | Image-Reader | 018 | CHUNK-018 complete |
| 023 | Orchestrator | 019, 020, 021, 022 | CHUNK-022 complete |
| 024 | KU Service | 002, 009 | CHUNK-009 complete |
| 025 | Image Service | 002, 009, 015 | CHUNK-015 complete |
| 026 | Page Service | 002, 009, 015 | CHUNK-015 complete |
| 027 | State Service | 002, 009 | CHUNK-009 complete |
| 028 | Settings Service | 002, 009 | CHUNK-009 complete |
| 029 | Attr Service | 002, 009 | CHUNK-009 complete |
| 030 | Background Task | 023, 024-029 | CHUNK-029 complete |
| 031 | FastAPI App | 001, 007 | CHUNK-007 complete |
| 032 | API Upload | 003, 004, 005, 006, 009 | CHUNK-009 complete |
| 033 | API Processing | 030 | CHUNK-030 complete |
| 034 | API Books | 003, 006 | CHUNK-006 complete |
| 035 | API KU | 024, 006 | CHUNK-024 complete |
| 036 | API Images | 025 | CHUNK-025 complete |
| 037 | API Pages | 026 | CHUNK-026 complete |
| 038 | WebSocket | 027 | CHUNK-027 complete |
| 039 | HTML Upload | 031 | CHUNK-031 complete |
| 040 | JS Upload | 032, 039 | CHUNK-039 complete |
| 041 | DB Init | 002, 003 | CHUNK-003 complete |
| 042 | CSS | - | Immediately |
| 043 | Requirements | - | Immediately |
| 044 | Config Files | - | Immediately |
| 045 | README | ALL | CHUNK-044 complete |

---

## 🚀 Optimal Development Strategy

### Phase 1: Foundation (Week 1)
**Sequential:**
1. CHUNK-001 (config)
2. CHUNK-002 (DB connection)
3. CHUNK-003 (Books model)

**Parallel:**
- CHUNK-004, 005, 006, 008 (utilities)
- CHUNK-007 (logging, after CHUNK-001)

**Outcome:** Database connectivity + basic utilities ready

---

### Phase 2: Core Logic (Week 2-3)
**Parallel Track A (OCR):**
1. CHUNK-010 (OCR)
2. CHUNK-011 (OCR retry)

**Parallel Track B (PDF):**
- CHUNK-012 (PDF text)
- CHUNK-013 (PDF→Image)

**Parallel Track C (AI Models):**
- CHUNK-016 → CHUNK-017 (SBERT + text chunking)
- CHUNK-018 (BLIP)

**Parallel Track D (Utilities):**
- CHUNK-014 (language detection)
- CHUNK-015 (compression)

**Sequential:**
- CHUNK-009 (table creation, after CHUNK-003)

**Outcome:** All core extraction capabilities ready

---

### Phase 3: Agents & Services (Week 4-5)
**Parallel Track A (Agents):**
1. CHUNK-019 (Reader)
2. CHUNK-020 (Splitter)
3. CHUNK-021 (Marker)
4. CHUNK-022 (Image-Reader)

**Sequential:** CHUNK-023 (Orchestrator, after all agents)

**Parallel Track B (DB Services):**
1. CHUNK-024 (KU service)
2. CHUNK-025 (Image service)
3. CHUNK-026 (Page service)
4. CHUNK-027 (State service)
5. CHUNK-028 (Settings service)
6. CHUNK-029 (Attr service)

**Sequential:** CHUNK-030 (Background task, after orchestrator + services)

**Outcome:** Complete processing pipeline + database layer

---

### Phase 4: API & Frontend (Week 6-7)
**Sequential:** CHUNK-031 (FastAPI app first)

**Parallel Track A (API Routes):**
1. CHUNK-032 (Upload)
2. CHUNK-033 (Processing)
3. CHUNK-034 (Books)
4. CHUNK-035 (KU)
5. CHUNK-036 (Images)
6. CHUNK-037 (Pages)
7. CHUNK-038 (WebSocket)

**Parallel Track B (Frontend):**
- CHUNK-039 (HTML)
- CHUNK-040 (JavaScript, after CHUNK-032)
- CHUNK-042 (CSS)

**Outcome:** Complete web interface

---

### Phase 5: Integration (Week 8)
**Parallel:**
- CHUNK-041 (DB init)
- CHUNK-043 (requirements)
- CHUNK-044 (config files)

**Sequential:** CHUNK-045 (README, final integration test)

**Outcome:** Production-ready system

---

## ✅ Validation Checklist

Before moving to next level:
- [ ] All chunks in current level implemented
- [ ] All unit tests passing
- [ ] Integration tests passing for level
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] No known bugs

---

## 📊 Critical Path

**The critical path** (longest dependency chain):

```
CHUNK-001 → CHUNK-002 → CHUNK-003 → CHUNK-009 →
CHUNK-024 → CHUNK-030 → CHUNK-033 → CHUNK-045

Total: 8 chunks on critical path
```

**Estimated Critical Path Time:** ~25-30 hours

**Total Parallel Time:** ~120-150 hours (with 3-4 developers working in parallel)

---

**Dependency Graph Complete:** ✅
**Ready for:** Developer Agent parallel execution planning

