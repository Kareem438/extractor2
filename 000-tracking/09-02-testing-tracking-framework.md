# Testing: Task Tracking Framework

**Task:** Build a tracking framework for session continuity  
**Date:** 2026-02-09  
**Status:** ✅ Complete (Final Review Done)

---

## Test Cases

### TC-001: Tracking Trigger Conditions (from Q1)
- **Verify:** Code change requests prompt "Does this require detailing?"
- **Verify:** Feature implementation requests prompt "Does this require detailing?"
- **Verify:** Bug fix requests prompt "Does this require detailing?"
- **Verify:** Simple commands (push, start server, health check) do NOT trigger tracking prompt
- **Verify:** Information questions do NOT trigger tracking prompt

### TC-002: File Creation (from Q1, Q2, Q3)
- **Verify:** When user answers "yes" to detailing, 3 files are created in `000-tracking/`
- **Verify:** Requirement file follows naming: `dd-mm-requirement-{name}.md`
- **Verify:** Tracking file follows naming: `dd-mm-tracking-{name}.md`
- **Verify:** Testing file follows naming: `dd-mm-testing-{name}.md`
- **Verify:** `000-tracking/` directory is created if it doesn't exist
- **Verify:** `00-main-steps.md` is updated with new task entry

### TC-003: Tracking File Live Updates (from Q2)
- **Verify:** Tracking file is updated every 2 minutes during execution
- **Verify:** Tracking file is updated when code change exceeds 50 LOC
- **Verify:** Each entry includes: timestamp, action, files modified, decisions
- **Verify:** Tracking file maintains a "Files Created/Modified" section with line counts

### TC-004: Testing File Updates (from Q4)
- **Verify:** Testing file is updated after EACH requirement answer (not batched)
- **Verify:** Test cases are derived from the specific answer given
- **Verify:** A final review pass is done after all requirements are gathered
- **Verify:** Test cases cover: happy path, edge cases, error handling

### TC-005: Session Start Behavior (from Q5)
- **Verify:** New session reads `00-main-steps.md` first
- **Verify:** For in-progress tasks, ALL three files are read (requirement, tracking, testing)
- **Verify:** Execution continues from where the last session finished
- **Verify:** No context is lost between sessions

### TC-006: Task Lifecycle (from Q6)
- **Verify:** Tasks start at "Not Started"
- **Verify:** Status progresses: Not Started → Requirements Gathering → Ready for Execution → In Progress → Testing → Completed
- **Verify:** Status is accurately reflected in `00-main-steps.md`
- **Verify:** Status emoji matches: 🔴 Not Started, 🟡 In Progress, 🟢 Completed

### TC-007: NEXT-SESSION.md Integration (from Q7)
- **Verify:** `NEXT-SESSION.md` points to `00-main-steps.md` as primary reference
- **Verify:** Old session summary workflow is replaced for new tasks
- **Verify:** `NEXT-SESSION.md` still contains quick-reference info (server commands, etc.)

### TC-008: 21-Day Archiving (from Q8)
- **Verify:** At session start, tasks older than 21 days are detected
- **Verify:** Archiving only happens if old tasks actually exist
- **Verify:** Archived tasks move to `00-main-steps-ARCHIVE-mm-yyyy.md`
- **Verify:** Archive file is named with the month/year of archiving
- **Verify:** A new archive file is created each month
- **Verify:** Archived tasks are removed from `00-main-steps.md`

### TC-009: Files Modified Section (from Q9)
- **Verify:** Tracking file has a dedicated "Files Created/Modified" section
- **Verify:** Each file entry includes: filename, action (Created/Modified), line count
- **Verify:** Section is updated as new files are touched during execution

### TC-010: Steering File Integration (from Q10)
- **Verify:** `.kiro/steering/tracking-framework.md` exists
- **Verify:** Steering file is lightweight — references `000-tracking/00-tracking-framework.md`
- **Verify:** Steering file does NOT contain the full framework rules
- **Verify:** Framework doc is loaded when steering file is read

### TC-011: Requirements Gathering Process
- **Verify:** Questions are asked one at a time (batches of 1)
- **Verify:** Questions are multiple-choice format
- **Verify:** Questions continue until 95% confidence
- **Verify:** Each Q&A is recorded in requirement file immediately after answer

### TC-012: 00-main-steps.md Structure
- **Verify:** Each task entry has: name, date, status, 5-line summary
- **Verify:** Each task entry has: requirements gathering status, execution status
- **Verify:** Each task entry has: references to all 3 files (requirement, tracking, testing)
- **Verify:** Completed tasks section exists
- **Verify:** Archive reference section exists

### TC-013: Edge Cases
- **Verify:** Multiple tasks can be tracked simultaneously
- **Verify:** Framework handles tasks that span multiple sessions
- **Verify:** Framework handles tasks where user says "no" to detailing (tracking file only)
- **Verify:** Date format is consistent (dd-mm) across all file names
