# Task Tracking Framework

**Version:** 1.0  
**Created:** 2026-02-09  
**Purpose:** Ensure full context continuity across sessions by tracking requirements, progress, and testing for every significant task.

---

## Overview

This framework provides structured tracking for all code changes, feature implementations, and bug fixes. It ensures that when a new session starts, the AI assistant can fully resume context from where the last session ended.

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

Each tracked task creates 3 files in `000-tracking/`:

| File | Naming Pattern | Purpose |
|------|---------------|---------|
| Requirement | `dd-mm-requirement-{name}.md` | Requirements Q&A log |
| Tracking | `dd-mm-tracking-{name}.md` | Live progress log |
| Testing | `dd-mm-testing-{name}.md` | Test cases from requirements |

Example for an API configuration task on Feb 9:
- `09-02-requirement-api-configuration.md`
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
5. References to requirement, tracking, and testing files

### Task Lifecycle Statuses

```
Not Started → Requirements Gathering → Ready for Execution → In Progress → Testing → Completed
```

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
2. For any in-progress tasks, read ALL three files (requirement, tracking, testing)
3. Check for tasks older than 21 days and archive if found
4. Continue from where the last session finished

---

## Requirement File Rules

- Questions are asked in batches of 1 (one at a time)
- Each question is multiple-choice
- Questions continue until 95% confidence in understanding requirements
- Each Q&A pair is recorded in the requirement file immediately after the user answers
- The testing file is also updated after each answer with derived test cases

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
- A final review pass is done at the end of requirements gathering
- Test cases are linked to the requirement questions that generated them
- Test cases cover: happy path, edge cases, error handling, integration points

---

## Integration with Existing System

- `NEXT-SESSION.md` serves as a quick-reference pointer to `00-main-steps.md`
- The steering file (`.kiro/steering/`) references this framework document
- This framework replaces the need for `SESSION-SUMMARY-*.md` files for new tasks

---

## Workflow Summary

```
1. User makes a request
2. If it's a code change/feature/bug:
   a. Ask: "Does this request require detailing?"
   b. If YES:
      - Create requirement, tracking, and testing files
      - Ask clarification questions (1 at a time, multiple choice)
      - Record each Q&A in requirement file
      - Update testing file after each answer
      - Continue until 95% confidence
      - Update 00-main-steps.md
   c. If NO:
      - Create tracking file only (for progress logging)
      - Proceed with execution
      - Update 00-main-steps.md
3. During execution:
   - Update tracking file every 2 min or 50+ LOC
   - Log files modified, decisions, progress
4. After completion:
   - Final update to tracking file
   - Final review of testing file
   - Update status in 00-main-steps.md
```
