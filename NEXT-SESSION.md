# Next Session Context

**Last Updated:** 2026-01-29
**Session:** Session 23 - Requirement 7 Requirements Gathering

---

## STATUS: REQUIREMENT 7 REQUIREMENTS GATHERING 🟡

### Requirement 6 - Delete Book: ✅ COMPLETE
- Two-step confirmation working
- Orphaned tables cleaned up
- All tasks complete

### Requirement 7 - KU Grouping, Multi-Tag Extraction & YOLO Training: 🟡 IN PROGRESS

**Three Features:**
1. **7A: Multi-Tag XML Extraction** - Extract multiple XML tags to different attributes
2. **7B: Knowledge Unit Grouping** - Combine KUs into single Claude prompts
3. **7C: YOLO Fine-Tuning** - Train DocLayout-YOLO with user corrections

**Requirements Gathering: 60% Complete**
- 4 of 12 clarification questions answered
- Need to complete Q5-Q12

---

## NEXT STEPS (Continue Requirement 7)

1. **Read requirements:** `01-requirements/requirement7-grouping-training.md`
2. **Read progress:** `01-requirements/requirement7-progress.md`
3. **Ask remaining questions (Q5-Q12)**
4. **Review existing code:**
   - `03-code/src/api/routes/pipeline.py`
   - `03-code/src/services/claude_batch_service.py`
5. **Create design document**
6. **Create tasks.md**

---

## Remaining Questions to Ask User

**7A (Multi-Tag Extraction):**
- Q5: Should unmapped tags in response be ignored or stored?
- Q6: Error handling if expected tag is missing?

**7B (KU Grouping):**
- Q7: Grouping scope - per pipeline step or global?
- Q8: What if KU ID missing from Claude response?
- Q9: Dry run mode to preview without executing?

**7C (YOLO Fine-Tuning):**
- Q10: Minimum pages before training enabled?
- Q11: Training in background or blocking?
- Q12: Auto-backup model before training?

---

## Decisions Already Made

| Feature | Decision |
|---------|----------|
| Tag mapping UI | Table/grid with Tag → Attribute dropdown |
| Grouping method | Group by L2 title with max N rule |
| Response ID | KU ID as XML tags (`<ku_123>...</ku_123>`) |
| Grouping criteria | KU count OR token limit, with preview button |
| Preview table | L1 → L2 → KU count → word count |

---

## Files to Read on Session Start

| File | Purpose |
|------|---------|
| `NEXT-SESSION.md` | This file - session context |
| `01-requirements/requirement7-grouping-training.md` | Full requirements |
| `01-requirements/requirement7-progress.md` | Progress tracker |
| `02-architecture/automatic-boundaries-local-llm-part2.md` | YOLO training reference |
| `.kiro/steering/code-review-first.md` | CRITICAL: Check existing code first |

---

## Quick Commands

```powershell
# Start server
cd H:\13-extractor2
Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Restart server
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2; Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn src.main:app --host 0.0.0.0 --port 8888" -WorkingDirectory "03-code" -WindowStyle Hidden

# Check server health
Invoke-WebRequest -Uri "http://localhost:8888/health" -UseBasicParsing | Select-Object -ExpandProperty Content

# PostgreSQL access
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d knowledge_extraction_2
# Password: postgres
```

---

## Project Configuration

- **Location:** `H:\13-extractor2`
- **Database:** `knowledge_extraction_2`
- **Port:** `8888`
- **Virtual Environment:** `H:\13-extractor2\venv`

---

## Previous Requirements Status

| Requirement | Status |
|-------------|--------|
| Req 4 - Title Hierarchy | ✅ Complete |
| Req 5 - Multi-PDF & Cross-Book | ✅ Complete |
| Req 6 - Delete Book | ✅ Complete |
| Req 7 - KU Grouping & Training | 🟡 Requirements 60% |
