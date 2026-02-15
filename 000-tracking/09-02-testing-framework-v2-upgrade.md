# Testing: Framework v2 Upgrade

**Task:** Upgrade tracking framework with API-first approach, design documents, test cleanup, and DB backup reminders  
**Date:** 2026-02-09  
**Status:** ✅ Complete (Final Review Done)

---

## Test Cases

### TC-001: Design Document Creation (from Q1)
- **Verify:** A design document (`dd-mm-design-{name}.md`) is created alongside requirement, tracking, and testing files
- **Verify:** Design document includes full API contracts (method, path, request/response schemas, status codes)
- **Verify:** Design document includes sequence diagrams for complex flows
- **Verify:** Design document includes error handling specs and edge cases
- **Verify:** Design document is built gradually — updated after each requirement Q&A answer
- **Verify:** After requirements are complete, a full design review is performed
- **Verify:** Design review includes review of existing code that will be impacted
- **Verify:** Design review asks user about design decisions (optimized for existing code)
- **Verify:** Design review asks user about APIs that may be overkill

### TC-002: Design Document as 4th File (from Q2)
- **Verify:** Each tracked task now creates 4 files: requirement, design, tracking, testing
- **Verify:** Design file follows naming: `dd-mm-design-{name}.md`
- **Verify:** Design file is referenced in `00-main-steps.md` alongside the other 3 files
- **Verify:** Steering file enforces that implementation must reference the design doc before writing code
- **Verify:** Implementation cannot proceed without a completed design document

### TC-003: Test Object Cleanup Tracking (from Q3)
- **Verify:** Testing file has a "Cleanup" section listing all objects tests will create
- **Verify:** Cleanup section includes: DB records (table + IDs), files created, config changes
- **Verify:** Cleanup section has a checklist format (checkboxes) for verification
- **Verify:** After test execution, cleanup checklist must be verified (all items checked off)
- **Verify:** Cleanup is not considered complete until all items are checked

### TC-004: DB Backup Reminder (from Q4)
- **Verify:** `00-main-steps.md` has a "Database Backup" section in the header
- **Verify:** Section tracks last backup date
- **Verify:** Section includes ready-to-use `pg_dump` command for copy-paste
- **Verify:** At session start, if 2+ days since last backup, a reminder is shown to the user
- **Verify:** After user confirms backup, the date is updated in `00-main-steps.md`

### TC-005: Autonomous Execution After Design Verification (from Q5)
- **Verify:** After all design verification questions are answered, a summary of planned work is shown
- **Verify:** User is asked "Shall I proceed?" before autonomous execution begins
- **Verify:** Once user confirms, execution proceeds without further interruptions
- **Verify:** Implementation, testing, and completion all happen autonomously after confirmation

### TC-006: API-First Threshold Rules (from Q6)
- **Verify:** Pure cosmetic/UI-only changes (CSS, layout, text) are automatically exempt from API-first rule
- **Verify:** Any functionality that reads/writes data MUST have an API endpoint
- **Verify:** Any functionality that triggers business logic MUST have an API endpoint
- **Verify:** Borderline cases are flagged during design verification for user decision
- **Verify:** GUI code only calls APIs — no direct DB access or business logic in frontend JS

### TC-007: Design-to-Implementation Adherence (from Q7)
- **Verify:** Implementation matches design document exactly (API contracts, schemas, endpoints)
- **Verify:** Any deviation requires updating the design doc first + user approval with justification
- **Verify:** Bug-prevention deviations (design would cause bug due to existing code mismatch) are allowed without approval
- **Verify:** Bug-prevention deviations are reported at end of task
- **Verify:** Bug-prevention deviations are captured in `00-main-steps.md`
- **Verify:** No silent deviations — all differences between design and implementation are documented

### TC-008: Steering File Organization (from Q8)
- **Verify:** Single steering file `.kiro/steering/tracking-framework.md` covers all rules
- **Verify:** Steering file includes: tracking rules, API-first rules, design enforcement, cleanup tracking, backup reminders
- **Verify:** No duplicate steering files for overlapping concerns
- **Verify:** Steering file references `000-tracking/00-tracking-framework.md` for full details

### TC-009: Full Workflow Sequence (from Q9)
- **Verify:** Requirements Q&A builds design doc AND test cases gradually (after each answer)
- **Verify:** After requirements complete, code impact review happens first
- **Verify:** After code impact review, full test-cases review is performed
- **Verify:** After test-cases review, full design review is performed
- **Verify:** Design verification questions include: overkill APIs, design decisions, test cases confirmation
- **Verify:** Design doc and test-cases doc are updated based on verification answers
- **Verify:** Summary of planned work is shown to user
- **Verify:** User is asked "Shall I proceed?" before autonomous execution
- **Verify:** Autonomous execution only starts after user confirms

### TC-010: Retroactive Application (from Q10)
- **Verify:** v2 framework rules apply to all NEW tasks created after the upgrade
- **Verify:** Existing completed tasks (Task 1) are NOT modified
- **Verify:** Existing in-progress tasks are NOT retrofitted with design docs
- **Verify:** The framework version is clearly marked as v2 in the framework doc
