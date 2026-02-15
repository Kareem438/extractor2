# Requirements: Tracking Framework v2 Upgrade

**Task:** Upgrade tracking framework with API-first approach, design documents, test cleanup, and DB backup reminders  
**Date:** 2026-02-09  
**Status:** ✅ Complete (95% confidence reached — 10 questions answered)

---

## Requirements Q&A Log

### Q1: Design document detail level?
**Question:** When you say "design document" — what level of detail do you expect in it?
**Options:**
- A) High-level: API list + brief descriptions
- B) Medium: APIs + data flow + service design + DB changes
- C) Detailed: Full contracts, sequence diagrams, error specs
- D) Adaptive: API list + schemas, more detail for complex ones

**Answer:** C — Detailed. Full API contracts (OpenAPI-style), sequence diagrams, error handling specs, edge cases. Must serve as a reference for investigating efficient implementation of new features. Built gradually with each requirement answer, then a full review once requirements are complete. The review includes: reviewing existing code that will be impacted, then asking the user design decisions (optimized in light of existing code) along with questions about APIs that may be overkill.

---

### Q2: How should the design document relate to the other tracking files?
**Question:** Currently each task creates 3 files. You want to add a design document. Should it be separate or embedded?
**Options:**
- A) 4 files: requirement, design, tracking, testing (all separate)
- B) 3 files: requirement (includes design section), tracking, testing
- C) 4 files + design is also referenced in the steering file for enforcement
- D) 3 files + design is embedded in the requirement file but with its own clear section

**Answer:** C — A 4th separate file (`dd-mm-design-{name}.md`), AND the steering file must enforce that implementation references and follows the design doc before writing any code.

---

### Q3: How should test object cleanup tracking work?
**Question:** You mentioned tracking objects created during testing so they can be cleaned up afterward. How should this be structured?
**Options:**
- A) Dedicated cleanup section in the testing file listing all objects to delete after tests
- B) Cleanup script auto-generated alongside test cases
- C) Cleanup section in testing file + a cleanup checklist that must be verified after test execution
- D) Track in the tracking file as a post-test step

**Answer:** C — A "Cleanup" section in the testing file listing all objects that tests will create (DB records, files, etc.), plus a cleanup checklist that must be verified (checked off) after test execution completes.

---

### Q4: How should the DB backup reminder work?
**Question:** You want a reminder every 2 days to export the database. How should this be tracked?
**Options:**
- A) Track last backup date in 00-main-steps.md header, remind at session start if 2+ days passed
- B) Separate backup tracking file in 000-tracking/
- C) Track in 00-main-steps.md header + include the pg_dump command so user can just copy-paste
- D) Only remind when I explicitly ask about backups

**Answer:** C — Track last backup date in `00-main-steps.md` header section, include the ready-to-use `pg_dump` command, and remind at session start if 2+ days have passed since last backup.

---

### Q5: What does "work autonomously after design verification" mean exactly?
**Question:** After the user answers all design verification questions, how autonomous should execution be?
**Options:**
- A) Fully autonomous — proceed immediately without further confirmation
- B) Semi-autonomous — show summary of planned work, ask "Shall I proceed?", then go fully autonomous
- C) Fully autonomous + progress updates at every major milestone
- D) One final gate "Ready to execute?" then fully autonomous with zero interruptions

**Answer:** B — After design questions are answered, show a summary of the planned work and ask "Shall I proceed?" — then go fully autonomous for implementation, testing, and completion.

---

### Q6: What's the threshold for "API is overkill"?
**Question:** What's the general expectation for when an API is overkill?
**Options:**
- A) ALL functionality must be API-first, no exceptions
- B) API-first by default, but pure cosmetic/UI-only changes are exempt
- C) API-first by default, user decides case-by-case during design verification
- D) API-first for data read/write or business logic — pure rendering exempt

**Answer:** B + C + D combined — Pure cosmetic/UI-only changes (CSS, layout, text) are automatically exempt. Any functionality that reads/writes data or triggers business logic must be API-first. For anything in between, flag it during the design verification round and let the user decide.

---

### Q7: How strictly should implementation follow the design document?
**Question:** How strict should the design-to-implementation adherence be?
**Options:**
- A) Strict: Must match exactly, any deviation requires updating design doc first + user approval
- B) Flexible: Design doc is a guide, minor deviations OK
- C) Strict with escape hatch: Must match, but deviations documented in tracking file
- D) Strict for APIs, flexible for internals

**Answer:** A (strict) — Implementation MUST match design doc exactly. Any deviation requires:
1. Updating the design doc first
2. Getting user approval with a justification for the deviation

**Exception:** The ONLY case where deviation is allowed without user approval is when following the design would create a bug due to mismatching the current implementation. In this case:
- Deviation is allowed without user approval
- Must be reported at the end of the task
- Must be captured in `00-main-steps.md`

---

### Q8: How should the steering files be organized for these new rules?
**Question:** With the new API-first, design enforcement, cleanup tracking, and backup reminder rules, how should steering files be organized?
**Options:**
- A) Update existing steering file only
- B) Create a new separate steering file for API-first/design rules + update existing one
- C) Update existing + create a new api-first-design.md steering file
- D) Single updated steering file that covers everything

**Answer:** D — Single updated steering file that covers everything: tracking + API-first + design enforcement + cleanup + backup reminders. Keep it all in one place.

---

### Q9: What's the exact workflow sequence from requirements to autonomous execution?
**Question:** Confirm the full workflow order from requirements gathering to autonomous execution.
**Options:**
- A) Req Q&A (build design gradually) → Full design review → Code impact review → Design verification → Summary → Proceed → Autonomous
- B) Req Q&A → Design verification → Full design + code review → Summary → Proceed → Autonomous
- C) Req Q&A (build design gradually) → Code impact review → Full design review → Design verification → Autonomous (no summary)
- D) Req Q&A → All reviews in one batch → Summary → Proceed → Autonomous

**Answer:** None of the above — the correct sequence is:

1. **Requirements Q&A** (build design doc gradually + build test cases gradually after each answer)
2. **Code impact review** (review existing code that will be affected)
3. **Full test-cases review** (comprehensive review of all test cases)
4. **Full design review** (comprehensive review of the design document)
5. **Design verification questions to user** (overkill APIs + design decisions + test cases confirmation)
6. **Update design document and test-cases document** (based on user answers)
7. **Summary** of planned work
8. **"Shall I proceed?"** — user confirmation
9. **Autonomous execution**

---

### Q10: Should the upgraded framework apply retroactively to existing in-progress tasks?
**Question:** Should the v2 rules apply to existing in-progress tasks or only future tasks?
**Options:**
- A) ALL future tasks + retrofit existing in-progress tasks
- B) All future tasks only — don't retrofit existing tasks
- C) Future tasks + retrofit only the design doc for in-progress tasks
- D) Future tasks only, and for in-progress tasks only if user explicitly asks

**Answer:** B — Apply to all future tasks only. Don't retrofit existing completed or in-progress tasks.
