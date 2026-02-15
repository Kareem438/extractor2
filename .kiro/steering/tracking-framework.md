---
inclusion: auto
---

# Task Tracking & Development Framework (v2)

**CRITICAL: At the start of every session, read `000-tracking/00-main-steps.md` and resume any in-progress tasks.**

For full framework rules, read: `000-tracking/00-tracking-framework.md`

---

## Session Start Checklist
1. Read `000-tracking/00-main-steps.md`
2. Check DB backup date — if 2+ days since last backup, remind user with pg_dump command
3. For in-progress tasks, read ALL 4 files (requirement, design, tracking, testing)
4. Archive tasks older than 21 days if found
5. Continue from where last session finished

---

## API-First Development (MANDATORY)
- ALL functionality that reads/writes data or triggers business logic MUST be an API endpoint first
- GUI code ONLY calls APIs — no direct DB access or business logic in frontend JS
- Exempt: pure cosmetic/UI-only changes (CSS, layout, text)
- Borderline cases: flag during design verification, let user decide

---

## Task File Structure (4 files per task)
- `dd-mm-requirement-{name}.md` — Requirements Q&A log
- `dd-mm-design-{name}.md` — Full API contracts, sequences, error specs, code impact
- `dd-mm-tracking-{name}.md` — Live progress log (update every 2 min or 50+ LOC)
- `dd-mm-testing-{name}.md` — Test cases + cleanup checklist

---

## Design Document Enforcement
- Design doc is built gradually during requirements Q&A
- Implementation MUST match design document exactly
- Deviation requires: update design doc + user approval with justification
- ONLY exception: bug-prevention (design would cause bug due to existing code mismatch)
  - Allowed without approval, but MUST be reported at end of task + captured in 00-main-steps.md

---

## Full Workflow Sequence
1. Requirements Q&A (build design + test cases gradually)
2. Code impact review (review existing code affected)
3. Full test-cases review
4. Full design review
5. Design verification questions to user (overkill APIs + design decisions + test confirmation)
6. Update design doc + testing doc based on answers
7. Summary of planned work
8. "Shall I proceed?" — user confirmation
9. Autonomous execution

---

## Test Cleanup Tracking
- Testing file MUST have a "Cleanup" section listing all objects tests will create
- Checklist format — must be verified (checked off) after test execution
- Track: DB records (table + IDs), files created, config changes

---

## DB Backup Reminder
- Tracked in `00-main-steps.md` header (last backup date)
- Remind at session start if 2+ days since last backup
- Include ready-to-use pg_dump command

---

## Key Rules
- For code changes/features/bugs: Ask "Does this require detailing?" before starting
- If yes: Create 4 files in `000-tracking/`, follow full workflow
- If no: Create tracking file only, proceed with execution
- Archive tasks older than 21 days to monthly archive files
- v2 rules apply to new tasks only — don't retrofit existing tasks
