# Task Tracking & Development Framework v2

**Version:** 2.0  
**Purpose:** A portable framework for AI-assisted development that enforces API-first design, structured tracking, and session continuity across any project.

---

## HOW TO IMPORT THIS FRAMEWORK

When a user says "implement the framework in this file", the AI assistant must:

1. Create the folder `000-tracking/` in the project root (if it doesn't exist)
2. Create `000-tracking/00-tracking-framework.md` with the content from **Section A** below
3. Create `000-tracking/00-main-steps.md` with the template from **Section B** below (adapt DB name/path to the user's project)
4. Create the steering file at `.kiro/steering/tracking-framework.md` with the content from **Section C** below
5. Create or update `NEXT-SESSION.md` with the template from **Section D** below
6. Confirm to the user that the framework is active and explain the key rules

**IMPORTANT:** The DB backup command in `00-main-steps.md` must be adapted to the user's actual database name, database user, and backup path. Ask the user for these values during setup if not obvious from the project.

---
---

## SECTION A: Framework Rules Document

> Create this file at: `000-tracking/00-tracking-framework.md`


### 1. Overview

This framework provides structured tracking for all code changes, feature implementations, and bug fixes. It ensures:
- Full context continuity across sessions (no context loss between conversations)
- API-first development (all data/logic functionality exposed as APIs before GUI)
- Strict design-to-implementation adherence
- Automated test cleanup tracking
- Regular database backup reminders

### 2. When to Track

Tracking is triggered ONLY for:
- Code changes
- Feature implementations
- Bug fixes
- Architectural changes

Tracking is NOT triggered for:
- Simple commands (push to git, start server, check health)
- Questions / information requests
- File reads without modifications

### 3. File Structure Per Task

Each tracked task creates **4 files** in `000-tracking/`:

| File | Naming Pattern | Purpose |
|------|---------------|---------|
| Requirement | `dd-mm-requirement-{name}.md` | Requirements Q&A log |
| Design | `dd-mm-design-{name}.md` | Full API contracts, sequences, error specs, code impact |
| Tracking | `dd-mm-tracking-{name}.md` | Live progress log |
| Testing | `dd-mm-testing-{name}.md` | Test cases + cleanup checklist |

Where `dd-mm` is the date (day-month) and `{name}` is a short kebab-case description.

Example for an API configuration task on Feb 9:
- `09-02-requirement-api-configuration.md`
- `09-02-design-api-configuration.md`
- `09-02-tracking-api-configuration.md`
- `09-02-testing-api-configuration.md`

### 4. Central Index: 00-main-steps.md

The file `000-tracking/00-main-steps.md` is the master index. For each active task it contains:
1. Task name and date
2. 5-line summary
3. Requirements gathering status
4. Execution status
5. References to all 4 files (requirement, design, tracking, testing)
6. Design deviations (if any bug-prevention deviations occurred)

**Task Lifecycle Statuses:**
```
Not Started → Requirements Gathering → Design Review → Ready for Execution → In Progress → Testing → Completed
```

### 5. API-First Development Rule

**CRITICAL:** All functionality that reads/writes data or triggers business logic MUST be implemented as an API endpoint first. The GUI calls the API — no direct DB access or business logic in frontend code.

**Exempt from API-first (no need to ask user):**
- Pure cosmetic/UI-only changes (CSS, layout, text changes)
- Pure rendering/display logic with no data interaction

**Borderline cases:**
- Flag during design verification round (Step 5 of workflow)
- Let the user decide if building an API is overkill

**Enforcement:**
- The design document must list ALL API endpoints before implementation begins
- Implementation must create API endpoints BEFORE any GUI code
- Testing must verify functionality through API calls (no GUI interaction required)

### 6. Full Workflow: 9-Step Sequence

```
1. User makes a request
2. If it's a code change/feature/bug:
   a. Ask: "Does this request require detailing?"
   b. If YES → Follow Steps 1-9 below
   c. If NO → Create tracking file only, proceed with execution, update 00-main-steps.md
```

**Step 1: REQUIREMENTS Q&A**
- Create all 4 files (requirement, design, tracking, testing) in `000-tracking/`
- Add task entry to `00-main-steps.md`
- Ask clarification questions one at a time, multiple choice format
- Record each Q&A pair in the requirement file immediately after the user answers
- Update the DESIGN document gradually after each answer (add relevant API contracts, data model changes, etc.)
- Update the TESTING document gradually after each answer (derive test cases from the answer)
- Continue asking questions until 95% confidence that requirements are fully understood

**Step 2: CODE IMPACT REVIEW**
- Review existing code that will be affected by the implementation
- Identify: files to modify, functions to extend, patterns to follow, potential conflicts
- Document all findings in the design document under a "Code Impact Analysis" section

**Step 3: FULL TEST-CASES REVIEW**
- Comprehensive review of all test cases accumulated in the testing document
- Ensure coverage: happy path, edge cases, error handling, integration points
- Add the "Cleanup" section listing ALL objects that tests will create (DB records with table names, files, config changes)
- Cleanup section uses checklist format (checkboxes)

**Step 4: FULL DESIGN REVIEW**
- Comprehensive review of the entire design document
- Ensure all API contracts are complete: HTTP method, path, request schema, response schema, status codes
- Ensure sequence diagrams exist for complex multi-step flows
- Ensure error handling specs and edge cases are documented
- Ensure data model changes (DB schema, migrations) are specified

**Step 5: DESIGN VERIFICATION QUESTIONS TO USER**
- Ask the user about APIs that may be overkill (present each borderline case)
- Ask about design decisions that could be optimized given the existing codebase
- Ask for confirmation of test cases
- Questions asked in batches of 1 (one at a time)

**Step 6: UPDATE DOCUMENTS**
- Update the design document based on user's verification answers
- Update the testing document based on user's verification answers
- Remove any APIs the user confirmed as overkill
- Adjust design decisions per user feedback

**Step 7: SUMMARY**
- Show a concise summary of the planned work to the user
- Include: number of APIs to create, files to modify, estimated scope

**Step 8: "SHALL I PROCEED?"**
- Ask the user for explicit confirmation before starting implementation

**Step 9: AUTONOMOUS EXECUTION**
- Implement everything without further interruptions
- Follow the design document strictly
- Update the tracking file every 2 minutes of execution OR every change bigger than 50 Lines of Code (whichever comes first)
- After completion: verify test cleanup checklist, report any design deviations, update `00-main-steps.md`

### 7. Design Document Rules

**Content Requirements — the design document must include:**
- **API Contracts:** HTTP method, path, request schema (with field types), response schema, status codes for EVERY endpoint
- **Sequence Diagrams:** Text-based diagrams for complex multi-step flows
- **Error Handling Specs:** Expected errors, error response format, edge cases
- **Data Model Changes:** DB schema changes, new columns/tables, migration scripts needed
- **Service Layer Design:** Which services are involved, function signatures, dependencies
- **Code Impact Analysis:** Existing files that will be modified, functions to extend, patterns to follow

**Build Process:**
- Built gradually during requirements Q&A (updated after each answer)
- Full review performed after requirements are complete (Step 4)
- Updated based on design verification answers from user (Step 6)

**Adherence Rules:**
- **STRICT:** Implementation MUST match the design document exactly
- **Any deviation requires:** Updating the design doc first + getting user approval with a justification for the deviation
- **Bug-prevention exception (ONLY exception):** If following the design would create a bug because it mismatches the current codebase implementation:
  - Deviation is allowed WITHOUT user approval
  - MUST be reported at the end of the task
  - MUST be captured in `00-main-steps.md` under the task's "Design Deviations" field
- **No silent deviations** — every difference between design and implementation must be documented

### 8. Requirement File Rules

- Questions are asked in batches of 1 (one at a time)
- Each question is multiple-choice format
- Questions continue until 95% confidence in understanding requirements
- Each Q&A pair is recorded in the requirement file immediately after the user answers
- The design and testing files are ALSO updated after each answer

### 9. Tracking File Rules

The tracking file is a live progress log updated:
- Every 2 minutes of execution, OR
- Every change bigger than 50 Lines of Code
- (whichever comes first)

Each tracking entry includes:
- Timestamp (or entry number)
- What was done
- Files created/modified with line counts
- Decisions made
- Current status

The tracking file also maintains a running "Files Created/Modified" section listing ALL files touched during the task, with action (Created/Modified) and line counts.

### 10. Testing File Rules

- Updated continuously after each requirement answer with derived test cases
- A final review pass is done after requirements gathering (Step 3)
- Test cases are linked to the requirement questions that generated them
- Test cases cover: happy path, edge cases, error handling, integration points
- **All tests must be executable through API calls** (no GUI interaction required for testing)

**Cleanup Section (REQUIRED in every testing file):**
- Lists ALL objects that tests will create: DB records (table name + expected IDs), files created, config changes made
- Uses checklist format with checkboxes: `- [ ] Delete record X from table Y`
- After test execution completes, every cleanup item must be verified (checked off)
- Cleanup is NOT considered complete until ALL items are checked
- The assistant must execute the cleanup (or guide the user through it) before marking the task as complete

### 11. Database Backup Reminder

- The header of `00-main-steps.md` tracks the last database backup date
- At session start, check if 2+ days have passed since the last backup
- If yes: remind the user to run the backup, show the ready-to-use backup command
- After the user confirms the backup was done, update the date in `00-main-steps.md`
- The backup command should be customized to the project's database during framework setup

### 12. Archiving Rules

- Tasks older than 21 days are moved from `00-main-steps.md` to a monthly archive file
- Archive file naming: `00-main-steps-ARCHIVE-mm-yyyy.md` (where mm = month, yyyy = year)
- A new archive file is created for each month
- Archiving check happens at session start (only if tasks older than 21 days exist)
- Archived tasks are removed from the active section of `00-main-steps.md`

### 13. Session Start Behavior

When a new session begins, the AI assistant must:

1. Read `000-tracking/00-main-steps.md` to understand current state
2. Check DB backup date — if 2+ days since last backup, remind the user with the backup command
3. For any in-progress tasks, read ALL 4 files (requirement, design, tracking, testing)
4. Check for tasks older than 21 days and archive if found
5. Continue from where the last session finished

### 14. "No Detailing" Path

When the user says a task does NOT require detailing:
- Create ONLY a tracking file (`dd-mm-tracking-{name}.md`) for progress logging
- Add a task entry to `00-main-steps.md` (with status, summary, reference to tracking file only)
- Proceed directly with execution
- Update the tracking file during execution (same 2 min / 50 LOC rule)
- Update `00-main-steps.md` when complete

### 15. After Task Completion

When a task is finished:
1. Final update to the tracking file (mark as complete, list all files modified)
2. Final review of the testing file (ensure all test cases passed)
3. Verify the test cleanup checklist (all items checked off)
4. Report any design deviations that occurred during implementation
5. Update the task status in `00-main-steps.md` to "✅ Completed"
6. If there were bug-prevention deviations, add them to the task entry in `00-main-steps.md`

---
---

## SECTION B: 00-main-steps.md Template

> Create this file at: `000-tracking/00-main-steps.md`
> Adapt the database name, user, and backup path to the user's project.

```markdown
# Main Steps - Active Tasks

**Last Updated:** [TODAY'S DATE]
**Framework:** See [00-tracking-framework.md](00-tracking-framework.md) for full rules (v2)

---

## Database Backup Tracking

| Field | Value |
|-------|-------|
| **Last Backup Date** | _(not yet recorded)_ |
| **Reminder Interval** | Every 2 days |
| **Database** | `[DATABASE_NAME]` |

**Backup Command (copy-paste ready):**
```
[INSERT PROJECT-SPECIFIC BACKUP COMMAND HERE]
```
Example for PostgreSQL:
```
pg_dump -U [DB_USER] -d [DATABASE_NAME] -F c -f "[BACKUP_PATH]/[DATABASE_NAME]_[DATE].backup"
```

⚠️ **REMINDER:** If 2+ days since last backup, remind user to run the backup command above.

---

## Active Tasks (Last 21 Days)

_(No active tasks yet. Tasks will appear here as they are created.)_

---

## Completed Tasks

_(Completed tasks remain here for 21 days before archiving.)_

---

## Archive Reference

_(No archives yet. Tasks older than 21 days will be moved to `00-main-steps-ARCHIVE-mm-yyyy.md`)_
```

---
---

## SECTION C: Steering File

> Create this file at: `.kiro/steering/tracking-framework.md`
> This file is auto-included in every AI session to enforce the framework rules.

```markdown
---
inclusion: auto
---

# Task Tracking & Development Framework (v2)

**CRITICAL: At the start of every session, read `000-tracking/00-main-steps.md` and resume any in-progress tasks.**

For full framework rules, read: `000-tracking/00-tracking-framework.md`

---

## Session Start Checklist
1. Read `000-tracking/00-main-steps.md`
2. Check DB backup date — if 2+ days since last backup, remind user with backup command
3. For in-progress tasks, read ALL 4 files (requirement, design, tracking, testing)
4. Archive tasks older than 21 days if found
5. Continue from where last session finished

---

## API-First Development (MANDATORY)
- ALL functionality that reads/writes data or triggers business logic MUST be an API endpoint first
- GUI code ONLY calls APIs — no direct DB access or business logic in frontend code
- Exempt: pure cosmetic/UI-only changes (CSS, layout, text)
- Borderline cases: flag during design verification, let user decide

---

## Task File Structure (4 files per task in 000-tracking/)
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

## Full Workflow Sequence (9 Steps)
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
- Include ready-to-use backup command

---

## Key Rules
- For code changes/features/bugs: Ask "Does this require detailing?" before starting
- If yes: Create 4 files in `000-tracking/`, follow full 9-step workflow
- If no: Create tracking file only, proceed with execution
- Archive tasks older than 21 days to monthly archive files
```

---
---

## SECTION D: NEXT-SESSION.md Template

> Create this file at: `NEXT-SESSION.md` in the project root.

```markdown
# Next Session Context

**Last Updated:** [TODAY'S DATE]
**Primary Reference:** `000-tracking/00-main-steps.md`

---

## TRACKING FRAMEWORK ACTIVE

All task tracking uses the structured framework in `000-tracking/`.

**At session start, read these files:**

| File | Purpose |
|------|---------|
| `000-tracking/00-main-steps.md` | Master task index — start here |
| `000-tracking/00-tracking-framework.md` | Framework rules and workflow |

For any in-progress tasks in `00-main-steps.md`, also read the requirement, design, tracking, and testing files listed there.
```

---
---

## SECTION E: File Templates

These templates show the initial content for each of the 4 task files when a new task is created.

### Requirement File Template
```markdown
# Requirements: [TASK NAME]

**Task:** [Brief description]
**Date:** [TODAY'S DATE]
**Status:** 🟡 Requirements Gathering

---

## Requirements Q&A Log

_(Questions and answers will be recorded here as they are discussed)_
```

### Design File Template
```markdown
# Design: [TASK NAME]

**Task:** [Brief description]
**Date:** [TODAY'S DATE]
**Status:** 🟡 In Progress (built gradually during requirements Q&A)

---

## API Contracts

_(API endpoints will be added here as requirements are clarified)_

## Data Model Changes

_(DB schema changes will be documented here)_

## Service Layer Design

_(Service functions and dependencies will be listed here)_

## Sequence Diagrams

_(Complex flows will be diagrammed here)_

## Error Handling Specs

_(Error cases and responses will be documented here)_

## Code Impact Analysis

_(Existing files to modify will be listed after code impact review)_
```

### Tracking File Template
```markdown
# Tracking: [TASK NAME]

**Task:** [Brief description]
**Date:** [TODAY'S DATE]
**Status:** 🟡 In Progress

---

## Progress Log

### Entry 1 — [TODAY'S DATE]
- Created requirement, design, tracking, and testing files
- Starting requirements gathering Q&A

---

## Files Created/Modified

| File | Action | Lines |
|------|--------|-------|
| _(will be updated during execution)_ | | |
```

### Testing File Template
```markdown
# Testing: [TASK NAME]

**Task:** [Brief description]
**Date:** [TODAY'S DATE]
**Status:** 🟡 In Progress (updated after each requirement answer)

---

## Test Cases

_(Test cases will be added here as requirements are clarified)_

---

## Cleanup Checklist

_(Objects created during testing will be listed here for cleanup verification)_

- [ ] _(example: Delete test record from [table_name] where id = [X])_
- [ ] _(example: Remove test file [path])_
```

---

_End of framework export. With this file and the prompt "implement the framework in export-tracking-framework.md", any AI assistant should be able to set up the complete framework in any project._
