# Task Tracking Framework

**Version:** 2.0  
**Created:** 2026-02-09  
**Updated:** 2026-02-09  
**Purpose:** Ensure full context continuity across sessions, enforce API-first development, and maintain strict design-to-implementation adherence.

---

## Overview

This framework provides structured tracking for all code changes, feature implementations, and bug fixes. It ensures:
- Full context continuity across sessions
- API-first development (all data/logic functionality exposed as APIs before GUI)
- Strict design-to-implementation adherence
- Automated test cleanup
- Regular database backup reminders

---

## When to Track

Tracking is triggered ONLY for:
- Code changes
- Feature implementations
- Bug fixes
- Architectural changes

Tracking is NOT triggered for:
- Simple commands (push to github, start server, check health)
- Questions / information requests
- File reads without modifications

---

## File Structure

Each tracked task creates **4 files** in `000-tracking/`:

| File | Naming Pattern | Purpose |
|------|---------------|---------|
| Requirement | `dd-mm-requirement-{name}.md` | Requirements Q&A log |
| Design | `dd-mm-design-{name}.md` | Full API contracts, sequences, error specs |
| Tracking | `dd-mm-tracking-{name}.md` | Live progress log |
| Testing | `dd-mm-testing-{name}.md` | Test cases + cleanup checklist |

Example for an API configuration task on Feb 9:
- `09-02-requirement-api-configuration.md`
- `09-02-design-api-configuration.md`
- `09-02-tracking-api-configuration.md`
- `09-02-testing-api-configuration.md`

---

## Central Index: 00-main-steps.md

The file `000-tracking/00-main-steps.md` is the master index containing:

For each active task:
1. Task name and date
2. 5-line summary
3. Requirements gathering status
4. Execution status
5. References to all 4 files (requirement, design, tracking, testing)
6. Design deviations (if any bug-prevention deviations occurred)

### Task Lifecycle Statuses

```
Not Started → Requirements Gathering → Design Review → Ready for Execution → In Progress → Testing → Completed
```

### Database Backup Tracking

The header of `00-main-steps.md` tracks the last database backup date. At session start, if 2+ days have passed since the last backup, remind the user with the ready-to-use `pg_dump` command.

---

## API-First Development Rule

**CRITICAL:** All functionality that reads/writes data or triggers business logic MUST be implemented as an API endpoint first. The GUI calls the API — no direct DB access or business logic in frontend code.

### Exempt from API-first:
- Pure cosmetic/UI-only changes (CSS, layout, text)
- Pure rendering/display logic

### Borderline cases:
- Flag during design verification round
- Let the user decide if an API is overkill

### API-First Enforcement:
- The design document must list ALL API endpoints before implementation begins
- Implementation must create API endpoints BEFORE any GUI code
- Testing must verify functionality through API calls (no GUI interaction required)

---

## Workflow: Full Sequence (Requirements → Autonomous Execution)

```
1. User makes a request
2. If it's a code change/feature/bug:
   a. Ask: "Does this request require detailing?"
   b. If YES:
      Step 1: REQUIREMENTS Q&A
      - Create all 4 files (requirement, design, tracking, testing)
      - Ask clarification questions (1 at a time, multiple choice)
      - Record each Q&A in requirement file immediately
      - Update DESIGN document gradually after each answer
      - Update TESTING document gradually after each answer
      - Continue until 95% confidence

      Step 2: CODE IMPACT REVIEW
      - Review existing code that will be affected by the implementation
      - Identify files to modify, functions to extend, patterns to follow
      - Document findings in the design document

      Step 3: FULL TEST-CASES REVIEW
      - Comprehensive review of all test cases in the testing document
      - Ensure coverage: happy path, edge cases, error handling, integration
      - Add cleanup section with all objects tests will create

      Step 4: FULL DESIGN REVIEW
      - Comprehensive review of the design document
      - Ensure all API contracts are complete (method, path, request/response schemas, status codes)
      - Ensure sequence diagrams for complex flows
      - Ensure error handling specs and edge cases

      Step 5: DESIGN VERIFICATION QUESTIONS TO USER
      - Ask about APIs that may be overkill
      - Ask about design decisions (optimized for existing code)
      - Ask for test cases confirmation
      - All questions in batches of 1

      Step 6: UPDATE DOCUMENTS
      - Update design document based on user answers
      - Update testing document based on user answers

      Step 7: SUMMARY
      - Show summary of planned work to user

      Step 8: "SHALL I PROCEED?"
      - Ask user for confirmation

      Step 9: AUTONOMOUS EXECUTION
      - Implement, test, and complete without further interruptions
      - Follow design document strictly
      - Update tracking file every 2 min or 50+ LOC

   c. If NO (does not require detailing):
      - Create tracking file only (for progress logging)
      - Proceed with execution
      - Update 00-main-steps.md
3. During execution:
   - Update tracking file every 2 min or 50+ LOC
   - Log files modified, decisions, progress
4. After completion:
   - Final update to tracking file
   - Final review of testing file
   - Verify test cleanup checklist
   - Report any design deviations
   - Update status in 00-main-steps.md
```

---

## Design Document Rules

### Content Requirements
The design document must include:
- **API Contracts:** Method, path, request schema, response schema, status codes for every endpoint
- **Sequence Diagrams:** For complex multi-step flows (text-based)
- **Error Handling Specs:** Expected errors, error responses, edge cases
- **Data Model Changes:** DB schema changes, new columns, migrations needed
- **Service Layer Design:** Which services are involved, function signatures
- **Code Impact Analysis:** Existing files that will be modified, functions to extend

### Build Process
- Built gradually during requirements Q&A (updated after each answer)
- Full review performed after requirements are complete
- Updated based on design verification answers from user

### Adherence Rules
- **STRICT:** Implementation MUST match design document exactly
- **Deviation requires:** Updating the design doc first + getting user approval with justification
- **Bug-prevention exception:** If following the design would create a bug due to mismatching existing code:
  - Deviation is allowed without user approval
  - MUST be reported at end of task
  - MUST be captured in `00-main-steps.md`
- **No silent deviations** — all differences must be documented

---

## Requirement File Rules

- Questions are asked in batches of 1 (one at a time)
- Each question is multiple-choice
- Questions continue until 95% confidence in understanding requirements
- Each Q&A pair is recorded in the requirement file immediately after the user answers
- The design and testing files are also updated after each answer

---

## Tracking File Rules

The tracking file is a live progress log updated:
- Every 2 minutes of execution, OR
- Every change bigger than 50 Lines of Code (whichever comes first)

Each tracking entry includes:
- Timestamp
- What was done
- Files created/modified with line counts
- Decisions made
- Current status

The tracking file also maintains a running section listing ALL files created/modified during the task.

---

## Testing File Rules

- Updated continuously after each requirement answer with derived test cases
- A final review pass is done after requirements gathering (Step 3)
- Test cases are linked to the requirement questions that generated them
- Test cases cover: happy path, edge cases, error handling, integration points
- **All tests must be executable through API calls** (no GUI interaction required)

### Cleanup Section (REQUIRED)
The testing file MUST include a "Cleanup" section that:
- Lists ALL objects that tests will create (DB records with table + expected IDs, files, config changes)
- Uses checklist format (checkboxes) for verification
- Must be verified (all items checked off) after test execution completes
- Cleanup is not considered complete until all items are checked

---

## Database Backup Reminder

- Track last backup date in `00-main-steps.md` header
- At session start, check if 2+ days have passed since last backup
- If yes, remind user with ready-to-use `pg_dump` command
- After user confirms backup, update the date in `00-main-steps.md`

---

## Archiving Rules

- Tasks older than 21 days are moved from `00-main-steps.md` to a monthly archive
- Archive file naming: `00-main-steps-ARCHIVE-mm-yyyy.md`
- A new archive file is created for each month
- Archiving check happens at session start (only if tasks older than 21 days exist)

---

## Session Start Behavior

When a new session begins:

1. Read `000-tracking/00-main-steps.md` to understand current state
2. Check DB backup date — remind if 2+ days since last backup
3. For any in-progress tasks, read ALL four files (requirement, design, tracking, testing)
4. Check for tasks older than 21 days and archive if found
5. Continue from where the last session finished

---

## Retroactive Application

- v2 rules apply to ALL new tasks created after the upgrade
- Existing completed tasks are NOT modified
- Existing in-progress tasks are NOT retrofitted

---

## Integration with Existing System

- `NEXT-SESSION.md` serves as a quick-reference pointer to `00-main-steps.md`
- The steering file (`.kiro/steering/tracking-framework.md`) references this framework document
- This framework replaces the need for `SESSION-SUMMARY-*.md` files for new tasks
