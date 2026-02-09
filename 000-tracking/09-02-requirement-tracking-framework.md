# Requirements: Task Tracking Framework

**Task:** Build a tracking framework for session continuity  
**Date:** 2026-02-09  
**Status:** ✅ Complete (95% confidence reached)

---

## Requirements Q&A Log

### Q1: When does tracking trigger?
**Question:** When you say "ask me if this request requires detailing" — does this apply to ALL requests, or only requests that involve code changes / feature implementation?  
**Options:**
- A) Only for code changes / feature implementation / bug fixes
- B) For ALL requests without exception
- C) For any request that takes more than 5 minutes
- D) I'll tell you when to track

**Answer:** A — Only for code changes, feature implementation, and bug fixes. Simple operational commands are excluded.

---

### Q2: What goes in the tracking file?
**Question:** For the tracking file, should it be a live progress log that I update as I work through the task?  
**Options:**
- A) Yes — log every significant step, code change, and decision
- B) No — just a summary at the end
- C) Only milestones, not every line change
- D) Real-time log with timestamps

**Answer:** A — The tracking file should log every significant step, code change, and decision as work progresses. Additionally, a testing file should be created alongside the requirement and tracking files, updated after each requirement answer with derived test cases.

---

### Q3: Should the framework itself be tracked?
**Question:** Should the creation of this tracking framework itself be tracked as the first entry in 00-main-steps.md?  
**Options:**
- A) Yes — it's the first task to track
- B) No — it's a meta-task
- C) Yes, but mark as 'framework' type

**Answer:** A — The tracking framework itself is the first task to track in 00-main-steps.md.

---

### Q4: How should the testing file be updated?
**Question:** Should each test case be directly linked to the specific requirement question that generated it?  
**Options:**
- A) Yes — update after each answer with linked test cases
- B) No — only after ALL questions are complete
- C) After each batch of questions
- D) Update continuously + final review pass at the end

**Answer:** D — Update the testing file continuously after each answer, and also do a final review pass at the end.

---

### Q5: Session start behavior?
**Question:** At the start of a new session, what's the expected behavior?  
**Options:**
- A) Read 00-main-steps.md, then tracking files for in-progress tasks
- B) Only read 00-main-steps.md
- C) Read 00-main-steps.md AND all three files for in-progress tasks
- D) No special behavior

**Answer:** C — Read 00-main-steps.md AND all three files (requirement, tracking, testing) for any in-progress task, and continue from where the last session finished.

---

### Q6: Task lifecycle statuses?
**Question:** What task statuses should be tracked in 00-main-steps.md?  
**Options:**
- A) Not Started → Requirements Gathering → Ready for Execution → In Progress → Testing → Completed
- B) Not Started → Requirements Gathering → In Progress → Completed
- C) Not Started → Requirements Gathering → Ready for Execution → In Progress → Completed
- D) Custom statuses

**Answer:** A — Full lifecycle: Not Started → Requirements Gathering → Ready for Execution → In Progress → Testing → Completed.

---

### Q7: Replace existing session summaries?
**Question:** Should this tracking framework replace the existing session summary files?  
**Options:**
- A) Yes — replace entirely
- B) No — keep both in parallel
- C) Gradually migrate
- D) Replace session summaries, but keep NEXT-SESSION.md as pointer to 00-main-steps.md

**Answer:** D — The tracking framework replaces session summaries, but NEXT-SESSION.md is kept as a quick-reference pointer to 00-main-steps.md.

---

### Q8: When does archiving happen?
**Question:** Should the 21-day archiving check happen automatically at session start?  
**Options:**
- A) Yes — every session start
- B) Only when explicitly asked
- C) Check at session start, but only archive if tasks older than 21 days exist
- D) Automatically at end of each session

**Answer:** C — Check at session start, but only archive if there are actually tasks older than 21 days.

---

### Q9: Track modified files?
**Question:** Should the tracking file include a list of all files modified during task execution?  
**Options:**
- A) Yes — include a section listing all files with line counts
- B) No — just mention in progress log entries
- C) Yes — running list at top, updated with each entry
- D) Track in testing file instead

**Answer:** A — Include a dedicated section in the tracking file listing all files created/modified with line counts.

---

### Q10: Steering file integration?
**Question:** Should the full framework rules be embedded in the steering file?  
**Options:**
- A) Yes — complete rules in steering file
- B) Reference only — keep steering file lightweight
- C) Both — concise summary in steering + detailed doc in 000-tracking/
- D) Only steering file, no separate doc

**Answer:** B — The steering file should just reference the framework documentation file. Keep the steering file lightweight.
