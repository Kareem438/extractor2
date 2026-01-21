# Quick Start Guide - Checkpoint & Handoff System

## What This System Does

🔄 **Progress Persistence**: Saves agent state every 5 minutes
💾 **Crash Recovery**: Resume from any checkpoint after interruption
📦 **Inter-Agent Handoffs**: Structured JSON manifests pass context between agents
📊 **Session Management**: Track entire project lifecycle
📝 **Execution Tracing**: Complete audit log of all agent activities

---

## 🔧 Configuration System

**NEW:** All system behavior is controlled by a central configuration file!

### Main Configuration File

**Location:** `agent-config.json` (project root)

This file is the **single source of truth** that controls:
- 📁 Where checkpoint files are saved
- 📁 Where deliverables are created
- 📁 Virtual environment location
- 🎯 Quality gate thresholds
- 🐛 Defect tracking file location
- ⚙️ Agent behavior settings

**Quick View:**
```bash
cat agent-config.json
```

**Key Configuration Sections:**

| Section | What It Controls | Default Value |
|---------|------------------|---------------|
| `project_metadata` | Project name, git settings | Auto-detected |
| `folder_structure` | Deliverable folder names | 01-requirements, 02-architecture, etc. |
| `environment` | Virtual env path, Python/Node versions | `venv/`, auto-detect |
| `progress_tracking` | ⭐ Checkpoint file locations | `.agent-status/*.json` |
| `deliverables_tracking` | Expected files per phase | Auto-tracked |
| `quality_gates` | Pass thresholds | BA: 95%, Tests: 100% per chunk |
| `defect_tracking` | Bug log location | `04-tests/bug-reports/defects.json` |
| `agent_behavior` | How each agent behaves | See defaults |

**Example Configuration:**
```json
{
  "environment": {
    "venv_path": "venv",
    "python_version": "auto"
  },
  "progress_tracking": {
    "checkpoint_files": {
      "ba_checkpoint": ".agent-status/ba-checkpoint.json",
      "developer_checkpoint": ".agent-status/developer-checkpoint.json"
    },
    "progress_dashboard": {
      "dashboard_file": ".agent-status/progress-dashboard.json"
    }
  },
  "quality_gates": {
    "ba_confidence_threshold": 95,
    "test_pass_rate_per_chunk": 100
  },
  "defect_tracking": {
    "defect_file": "04-tests/bug-reports/defects.json"
  }
}
```

**Want to customize?** Edit `agent-config.json` before running the orchestrator!

---

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│  • Manages session-metadata.json                                 │
│  • Tracks orchestrator-progress.json                             │
│  • Logs to execution-trace.log                                   │
│  • Offers crash recovery on start                                │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├─────> PHASE 1: BUSINESS ANALYST
         │       • Checkpoint: ba-checkpoint.json
         │       • Interactive questioning (→95% confidence)
         │       • Creates UI mockups
         │       • Handoff: ba-to-architect.json
         │
         ├─────> PHASE 2: ARCHITECT
         │       • Checkpoint: architect-checkpoint.json
         │       • Designs code chunks (30-50 LOC each)
         │       • Creates dependency graph
         │       • Handoff: architect-to-tester.json (test gen)
         │       • Handoff: architect-to-developer-chunks.json
         │
         ├─────> PHASE 3: TESTER (Test Generation)
         │       • Checkpoint: tester-checkpoint.json
         │       • Generates all test cases
         │       • No handoff created
         │
         ├─────> PHASE 4: CHUNK DEVELOPMENT (Per Chunk)
         │       │
         │       ├─> DEVELOPER
         │       │   • Checkpoint: developer-checkpoint.json
         │       │   • Implements chunk
         │       │   • Writes unit tests
         │       │   • Handoff: dev-chunk-{N}-to-tester.json
         │       │
         │       └─> TESTER (Chunk Verification)
         │           • Checkpoint: tester-checkpoint.json
         │           • Executes test cases for chunk
         │           • Handoff: tester-chunk-{N}-results.json
         │           • If 100% pass → Next chunk
         │           • If any fail → Back to Developer
         │
         └─────> PHASE 5: FINAL VALIDATION
                 • Checkpoint: tester-checkpoint.json
                 • Integration testing
                 • E2E testing
                 • Performance/Security testing
                 • Handoff: tester-final-validation.json
```

---

## File Structure

```
project-root/
├── .agent-status/                    # ⚠️  Git-ignored (runtime only)
│   ├── session-metadata.json              Project session state
│   ├── orchestrator-progress.json         Phase & chunk tracking
│   ├── ba-checkpoint.json                 Business Analyst progress
│   ├── architect-checkpoint.json          Architect progress
│   ├── developer-checkpoint.json          Developer progress
│   ├── tester-checkpoint.json             Tester progress
│   └── execution-trace.log                Event log
│
├── 01-requirements/
│   └── .handoff/                     # ✅ Committed to git
│       └── ba-to-architect.json
│
├── 02-architecture/
│   └── .handoff/                     # ✅ Committed to git
│       ├── architect-to-tester.json
│       └── architect-to-developer-chunks.json
│
├── 03-code/
│   └── .handoff/                     # ✅ Committed to git
│       ├── dev-chunk-1-to-tester.json
│       ├── dev-chunk-2-to-tester.json
│       └── ... (one per chunk)
│
└── 04-tests/
    └── .handoff/                     # ✅ Committed to git
        ├── tester-chunk-1-results.json
        ├── tester-chunk-2-results.json
        ├── ... (one per chunk)
        └── tester-final-validation.json
```

---

## 📂 Configuration-Controlled File Locations

All file paths shown above are **configurable** via `agent-config.json`.

### How Configuration Maps to File Locations

```json
// In agent-config.json:
{
  "folder_structure": {
    "requirements": "01-requirements",      // ← Change folder name here
    "architecture": "02-architecture",      // ← Change folder name here
    "code": "03-code",                      // ← Change folder name here
    "tests": "04-tests",                    // ← Change folder name here
    "agent_status": ".agent-status"         // ← Change folder name here
  },
  "progress_tracking": {
    "checkpoint_directory": ".agent-status",
    "checkpoint_files": {
      "session_metadata": ".agent-status/session-metadata.json",
      "ba_checkpoint": ".agent-status/ba-checkpoint.json",
      "architect_checkpoint": ".agent-status/architect-checkpoint.json",
      "developer_checkpoint": ".agent-status/developer-checkpoint.json",
      "tester_checkpoint": ".agent-status/tester-checkpoint.json"
    }
  }
}
```

**Result:** If you change `"requirements": "01-requirements"` to `"requirements": "requirements"`, all agents will use the `requirements/` folder instead!

### Checkpoint File Reference

| File | What It Tracks | Configured In |
|------|----------------|---------------|
| `session-metadata.json` | Session ID, project name, current phase | `progress_tracking.checkpoint_files.session_metadata` |
| `orchestrator-progress.json` | Overall phase/chunk progress | `progress_tracking.checkpoint_files.orchestrator_progress` |
| `ba-checkpoint.json` | BA confidence, questions asked | `progress_tracking.checkpoint_files.ba_checkpoint` |
| `architect-checkpoint.json` | Chunks designed, diagrams created | `progress_tracking.checkpoint_files.architect_checkpoint` |
| `developer-checkpoint.json` | Chunks completed, LOC written | `progress_tracking.checkpoint_files.developer_checkpoint` |
| `tester-checkpoint.json` | Tests run, bugs found | `progress_tracking.checkpoint_files.tester_checkpoint` |
| `execution-trace.log` | Complete event timeline | `progress_tracking.checkpoint_files.execution_trace` |

### Handoff File Reference

| File | What It Contains | Configured In |
|------|------------------|---------------|
| `ba-to-architect.json` | Requirements summary, confidence level | `progress_tracking.handoff_files.ba_to_architect` |
| `architect-to-tester.json` | Test generation instructions | `progress_tracking.handoff_files.architect_to_tester` |
| `architect-to-developer-chunks.json` | Chunk breakdown, dependencies | `progress_tracking.handoff_files.architect_to_developer` |
| `dev-chunk-{N}-to-tester.json` | Chunk implementation details | `progress_tracking.handoff_files.dev_chunk_to_tester_pattern` |
| `tester-chunk-{N}-results.json` | Test results per chunk | `progress_tracking.handoff_files.tester_chunk_results_pattern` |
| `tester-final-validation.json` | Final integration test results | `progress_tracking.handoff_files.tester_final_validation` |

**All paths are configurable!** Change them in `agent-config.json` to match your project structure.

---

## How to Use

### Starting a New Project

1. **Run orchestrator agent:**
   ```bash
   # Orchestrator automatically checks for existing session
   # None found → Creates new session
   # Begins Phase 0 (requirements collection)
   ```

2. **Agents work automatically:**
   - Create checkpoints on start
   - Update checkpoints every 5 minutes
   - Create handoff manifests when complete
   - Commit deliverables at milestones

### Resuming After Crash

1. **System crashes during development**

2. **Restart orchestrator agent:**
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   RECOVERY MODE AVAILABLE
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Session ID: ses-20251020-143000
   Project: Task Management System
   Current phase: phase-4-chunk-development
   Resume from: chunk-3-development
   
   Instructions: Developer was implementing Chunk 3.
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Would you like to resume? (y/n)
   ```

3. **Confirm recovery (y):**
   - Orchestrator reads session metadata
   - Invokes Developer agent with checkpoint
   - Developer resumes from Chunk 3

4. **Or start fresh (n):**
   - Creates new session
   - Begins from Phase 0

---

## ⚙️ Customizing Configuration

### Before Starting a New Project

**Recommended: Review and customize agent-config.json**

```bash
# 1. View default configuration
cat agent-config.defaults.json

# 2. Copy to main config (if not exists)
cp agent-config.defaults.json agent-config.json

# 3. Edit for your project
nano agent-config.json
```

### Common Customizations

#### Change Virtual Environment Location
```json
{
  "environment": {
    "venv_path": "my-venv"  // Change from "venv" to "my-venv"
  }
}
```

#### Adjust Quality Gates
```json
{
  "quality_gates": {
    "ba_confidence_threshold": 98,     // More strict (default: 95)
    "code_coverage_threshold": 90      // Higher coverage (default: 80)
  }
}
```

#### Change Folder Names
```json
{
  "folder_structure": {
    "code": "src",              // Use "src" instead of "03-code"
    "tests": "tests"            // Use "tests" instead of "04-tests"
  }
}
```

#### Configure Defect Tracking
```json
{
  "defect_tracking": {
    "enabled": true,
    "defect_file": "bugs/defects.json",  // Custom location
    "auto_create_issues": true           // Create GitHub issues
  }
}
```

#### Technology Preferences
```json
{
  "agent_behavior": {
    "architect": {
      "technology_preferences": {
        "prefer_standard_library": true,
        "max_external_dependencies": 5
      }
    },
    "developer": {
      "coding_standard": "pep8",
      "require_type_hints": true
    }
  }
}
```

### Configuration Examples by Project Type

**Python Web API:**
```json
{
  "environment": {
    "isolation_type": "venv",
    "python_version": "3.11"
  },
  "agent_behavior": {
    "developer": {"coding_standard": "pep8"}
  }
}
```

**Node.js Application:**
```json
{
  "environment": {
    "isolation_type": "npm",
    "node_version": "20"
  },
  "folder_structure": {
    "code": "src",
    "tests": "tests"
  }
}
```

**Data Science Project:**
```json
{
  "environment": {
    "isolation_type": "conda",
    "requirements_file": "environment.yml"
  },
  "quality_gates": {
    "code_coverage_threshold": 70  // Lower for experimental
  }
}
```

---

## 🔍 Inspecting State & Monitoring Progress

### Real-Time Project Status

**NEW: Human-Readable Status Report**

The system now generates a comprehensive status report in both JSON and Markdown formats!

```bash
# 🎯 EASIEST: Read human-readable status
cat .agent-status/project-status.md

# Sample output:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Project Status Report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Project: Task Management System
# Phase: Phase 4 - Chunk Development (68% complete)
# Active Agent: Developer
# Current Task: Implementing Chunk 5
# Chunks: 4/12 completed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Configuration:**
```json
{
  "status_reporting": {
    "human_readable_summary": ".agent-status/project-status.md"  // ← Change path here
  }
}
```

### Progress Dashboard

View real-time progress across all agents:

```bash
# View complete dashboard
cat .agent-status/progress-dashboard.json

# Overall progress
cat .agent-status/progress-dashboard.json | jq '.overall_progress'

# Output:
# {
#   "phase": "phase-4-chunk-development",
#   "percentage_complete": 68,
#   "estimated_completion": "2025-11-03T18:00:00Z"
# }

# Agent status
cat .agent-status/progress-dashboard.json | jq '.agent_status'

# Chunk progress
cat .agent-status/progress-dashboard.json | jq '.chunks_progress'

# Quality gates
cat .agent-status/progress-dashboard.json | jq '.quality_gates'
```

**Configuration:**
```json
{
  "progress_tracking": {
    "progress_dashboard": {
      "dashboard_file": ".agent-status/progress-dashboard.json"  // ← Change path here
    }
  }
}
```

### System Heartbeat

Check if the system is alive and what it's doing:

```bash
cat .agent-status/heartbeat.json

# Output:
# {
#   "last_heartbeat": "2025-11-03T14:35:00Z",
#   "active_agent": "developer",
#   "status": "running",
#   "current_operation": "writing unit tests for chunk 5"
# }
```

**Configuration:**
```json
{
  "progress_tracking": {
    "monitoring": {
      "heartbeat_file": ".agent-status/heartbeat.json",  // ← Change path here
      "heartbeat_interval_seconds": 60
    }
  }
}
```

### View Current Session
```bash
cat .agent-status/session-metadata.json
```

**Configuration location:** `progress_tracking.checkpoint_files.session_metadata`

Example output:
```json
{
  "session_id": "ses-20251020-143000",
  "project_name": "Task Management System",
  "current_phase": "phase-4-chunk-development",
  "current_chunk": 3,
  "phase_status": {
    "phase_1_ba_analysis": "completed",
    "phase_2_architecture": "completed",
    "phase_3_test_generation": "completed",
    "phase_4_chunk_development": "in_progress"
  }
}
```

### View Agent Checkpoint
```bash
# Business Analyst
cat .agent-status/ba-checkpoint.json

# Architect
cat .agent-status/architect-checkpoint.json

# Developer
cat .agent-status/developer-checkpoint.json

# Tester
cat .agent-status/tester-checkpoint.json
```

**Configuration location:** `progress_tracking.checkpoint_files.<agent>_checkpoint`

Example output:
```json
{
  "agent": "developer",
  "phase": "chunk-implementation",
  "status": "in_progress",
  "progress": {
    "total_chunks": 12,
    "chunks_completed": 2,
    "current_chunk_number": 3,
    "current_loc_written": 28
  }
}
```

### View Deliverables Manifest

Track all files created by agents:

```bash
# View all deliverables
cat .agent-status/deliverables-manifest.json

# Summary
cat .agent-status/deliverables-manifest.json | jq '.summary'

# Output:
# {
#   "total_expected": 45,
#   "completed": 28,
#   "in_progress": 2,
#   "pending": 15,
#   "missing": 0
# }
```

**Configuration:**
```json
{
  "deliverables_tracking": {
    "deliverables_manifest": ".agent-status/deliverables-manifest.json"  // ← Change path here
  }
}
```

### View Defects/Bugs

```bash
# View all bugs
cat 04-tests/bug-reports/defects.json

# Count by severity
cat 04-tests/bug-reports/defects.json | jq 'group_by(.severity) | map({severity: .[0].severity, count: length})'
```

**Configuration:**
```json
{
  "defect_tracking": {
    "defect_file": "04-tests/bug-reports/defects.json"  // ← Change path here
  }
}
```

### View Execution Trace
```bash
cat .agent-status/execution-trace.log
```

**Configuration location:** `progress_tracking.checkpoint_files.execution_trace`

Example output:
```
[2025-10-20T14:30:00Z] SESSION_START ses-20251020-143000
[2025-10-20T14:31:00Z] HANDOFF user→business-analyst
[2025-10-20T14:50:00Z] QUALITY_GATE phase_1_ba PASSED (confidence: 95%)
[2025-10-20T14:50:00Z] HANDOFF business-analyst→architect
[2025-10-20T15:10:00Z] QUALITY_GATE phase_2_architect PASSED (chunks: 12)
[2025-10-20T15:10:00Z] HANDOFF architect→tester
[2025-10-20T15:18:00Z] QUALITY_GATE phase_3_test_generation PASSED
[2025-10-20T15:18:00Z] HANDOFF architect→developer (chunk 1)
[2025-10-20T15:25:00Z] CHUNK_COMPLETE chunk_1
[2025-10-20T15:25:00Z] HANDOFF developer→tester (chunk 1)
```

### View Handoff Manifest
```bash
cat 01-requirements/.handoff/ba-to-architect.json
```

**Configuration location:** `progress_tracking.handoff_files.ba_to_architect`

Example output:
```json
{
  "handoff_type": "ba-to-architect",
  "from_agent": "business-analyst",
  "to_agent": "architect",
  "phase_summary": {
    "confidence_level": 95,
    "questions_asked": 27
  },
  "deliverables": {
    "requirements_specification": {
      "path": "01-requirements/requirements-specification.md",
      "functional_requirements": 22
    }
  },
  "architectural_hints": {
    "complexity_preference": "simple",
    "suggested_pattern": "layered-architecture"
  }
}
```

### Quick Monitoring Commands

```bash
# Quick status check
cat .agent-status/project-status.md

# Is system running?
cat .agent-status/heartbeat.json | jq '.status'

# What phase are we in?
cat .agent-status/session-metadata.json | jq '.current_phase'

# How many chunks done?
cat .agent-status/progress-dashboard.json | jq '.chunks_progress'

# Any blockers?
cat .agent-status/project-status.json | jq '.blockers'

# View bugs
cat $(jq -r '.defect_tracking.defect_file' agent-config.json)
```

**All file paths come from agent-config.json!**

---

## Checkpoint Update Frequency

| Agent | Checkpoint Update Triggers |
|-------|---------------------------|
| **Business Analyst** | Every 5 min, before question batch, after mockup, after confidence update |
| **Architect** | Every 5 min, before chunk design, after diagram, before asking questions |
| **Developer** | Every 5 min, before starting chunk, after completing chunk, before running tests |
| **Tester** | Every 5 min, before executing tests, after documenting results, after reporting bugs |
| **Orchestrator** | After agent handoff, phase transition, chunk completion |

---

## Git Commit Patterns

### What's Committed
✅ Handoff manifests (`*/.handoff/*.json`)
✅ Deliverables (requirements, architecture docs, code, tests)
✅ Agent configuration updates

### What's NOT Committed
❌ Checkpoint files (`.agent-status/*.json`)
❌ Execution trace log (`.agent-status/execution-trace.log`)
❌ Session metadata (`.agent-status/session-metadata.json`)

### Commit Message Format
```
<type>(<scope>): <description>

<details>

Phase: <phase name>
<metrics>
```

Examples:
```
docs(ba): document question batch 3 responses

- Asked 3 questions about user workflows
- Updated requirements draft with answers
- Confidence increased to 65%

Phase: 1 (Requirements Analysis)
Questions: 9/27 asked
```

```
feat(chunk-3): implement Database Connection

- Load connection from config
- Handle connection errors
- Graceful shutdown
- LOC: 32 (estimated: 30-35) ✓
- Unit tests: 3/3 passing ✓

Chunk: 3/12 (Database Connection)
Level: 1 (Core)
Status: Ready for testing
```

---

## Troubleshooting

### Problem: Checkpoint file missing
**Solution:** Normal on first run. Agent will create new checkpoint.

### Problem: Handoff manifest missing
**Cause:** Previous phase incomplete
**Solution:** Check git log for last phase commit, may need to restart from previous phase

### Problem: Recovery prompt not appearing
**Check:**
1. `.agent-status/session-metadata.json` exists
2. `resume_point.can_resume` is `true`
3. Agent checkpoint file exists

**Solution:** May need to start fresh session if files corrupted

### Problem: Agent seems stuck
**Check:**
1. View current checkpoint: `cat .agent-status/{agent}-checkpoint.json`
2. View execution trace: `cat .agent-status/execution-trace.log`
3. Check `next_action` in checkpoint

**Solution:** Resume from checkpoint or start fresh

### Problem: Can't find checkpoint/status files
**Solution:**
```bash
# Check configuration for file locations
cat agent-config.json | jq '.progress_tracking'

# Verify checkpoint directory exists
ls -la .agent-status/

# List all checkpoint files
ls -la .agent-status/*.json
```

### Problem: Status files in wrong location
**Cause:** Custom configuration changed default paths

**Solution:**
```bash
# Find where status file should be
cat agent-config.json | jq '.status_reporting.human_readable_summary'

# Example output: ".agent-status/project-status.md"
# Now read from that location
cat .agent-status/project-status.md
```

### Problem: Defect file not found
**Solution:**
```bash
# Check configured location
cat agent-config.json | jq '.defect_tracking.defect_file'

# Read from that location
DEFECT_FILE=$(jq -r '.defect_tracking.defect_file' agent-config.json)
cat "$DEFECT_FILE"
```

### Problem: Virtual environment in wrong location
**Solution:**
```bash
# Check configured venv path
cat agent-config.json | jq '.environment.venv_path'

# Update if needed
# Edit agent-config.json and change "venv_path" value
```

---

## Key Benefits

| Benefit | Description |
|---------|-------------|
| 🛡️ **No Work Lost** | Checkpoint every 5 minutes, resume from any point |
| 🔄 **Seamless Recovery** | Complete state recovery after crashes |
| 📦 **Clear Handoffs** | Structured context transfer between agents |
| 📊 **Full Traceability** | Git history + execution trace + session metadata |
| ✅ **Quality Gates** | 95% BA confidence, 100% test pass per chunk, final validation |
| 🚀 **Production Ready** | Self-contained, no external scripts, uses only Claude Code tools |

---

## Next Steps

1. **Try it out:**
   - Start orchestrator agent with a project request
   - Watch agents create checkpoints automatically
   - Monitor `.agent-status/` directory for checkpoints

2. **Test recovery:**
   - Let BA ask a few questions
   - Stop/crash the system
   - Restart orchestrator
   - Confirm recovery when prompted

3. **Inspect handoffs:**
   - After BA completes, check `01-requirements/.handoff/ba-to-architect.json`
   - See what context is passed to next agent
   - Follow handoff chain through project

4. **Review execution trace:**
   - Check `.agent-status/execution-trace.log`
   - See complete timeline of events
   - Understand phase transitions

---

## 📋 Configuration Files Quick Reference

### Main Files

| File | Purpose | Edit? |
|------|---------|-------|
| **agent-config.json** | ⭐ Main configuration (customize per project) | ✅ YES |
| **agent-config.defaults.json** | Default values template | ❌ Use as reference |
| **QUICK-START.md** | This file - system guide | 📖 Read |
| **README.md** | Agent descriptions | 📖 Read |
| **IMPLEMENTATION-SUMMARY.md** | Technical details | 📖 Read |

### Configuration Sections

| Section in agent-config.json | What It Controls |
|-------------------------------|------------------|
| `project_metadata` | Project name, git settings |
| `folder_structure` | Deliverable folder names |
| `environment` | Virtual env, Python/Node versions |
| `progress_tracking` | ⭐ Checkpoint file locations |
| `deliverables_tracking` | Expected files per phase |
| `quality_gates` | Pass thresholds |
| `agent_behavior` | How each agent behaves |
| `defect_tracking` | Bug log location |
| `git_workflow` | Commit strategy |
| `status_reporting` | Status file locations |

### Where File Paths Are Defined

All these paths come from `agent-config.json`:

```bash
# Checkpoint files
jq '.progress_tracking.checkpoint_files' agent-config.json

# Status files
jq '.status_reporting' agent-config.json

# Defect file
jq '.defect_tracking.defect_file' agent-config.json

# Virtual environment
jq '.environment.venv_path' agent-config.json

# Folder structure
jq '.folder_structure' agent-config.json
```

---

## 🎯 One-Page Configuration Summary

```json
{
  // Project settings
  "project_metadata": {
    "project_name": "auto",      // Auto-detect from user input
    "git_enabled": true
  },

  // Where deliverables go
  "folder_structure": {
    "requirements": "01-requirements",
    "architecture": "02-architecture",
    "code": "03-code",
    "tests": "04-tests"
  },

  // Environment setup
  "environment": {
    "venv_path": "venv",         // ⭐ Change if using different venv location
    "python_version": "auto"
  },

  // Progress tracking (where to find status)
  "progress_tracking": {
    "checkpoint_files": {
      "session_metadata": ".agent-status/session-metadata.json",
      "ba_checkpoint": ".agent-status/ba-checkpoint.json",
      "developer_checkpoint": ".agent-status/developer-checkpoint.json"
      // ... other agents
    },
    "progress_dashboard": {
      "dashboard_file": ".agent-status/progress-dashboard.json"  // ⭐ Real-time status
    },
    "monitoring": {
      "heartbeat_file": ".agent-status/heartbeat.json"  // ⭐ Is system alive?
    }
  },

  // Status reporting
  "status_reporting": {
    "human_readable_summary": ".agent-status/project-status.md"  // ⭐ READ THIS!
  },

  // Quality thresholds
  "quality_gates": {
    "ba_confidence_threshold": 95,          // ⭐ Adjust if needed
    "test_pass_rate_per_chunk": 100         // ⭐ Must be 100%
  },

  // Bug tracking
  "defect_tracking": {
    "defect_file": "04-tests/bug-reports/defects.json"  // ⭐ Where bugs are logged
  }
}
```

**⭐ = Most commonly customized settings**

---

## Documentation

- **IMPLEMENTATION-SUMMARY.md** - Comprehensive technical documentation
- **agent-instructions1.md** - Original implementation instructions
- **README.md** - Project overview
- **QUICK-START.md** - This file

For detailed technical information, see [IMPLEMENTATION-SUMMARY.md](./IMPLEMENTATION-SUMMARY.md)
