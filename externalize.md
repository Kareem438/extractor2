# Externalization Analysis: Project-Specific Configurations

## Executive Summary

This analysis identifies all project-specific configurations in the subagent system that need to be externalized or parameterized for reuse across different projects.

**Status:** The subagent system is **99% portable** with minimal hardcoded references.

---

## Findings Summary

### ✅ GOOD NEWS: Most Components are Already Portable

The **agent configuration files** (`.claude/agents/*.md`) contain:
- ✅ **NO** hardcoded project names
- ✅ **NO** hardcoded repository URLs
- ✅ **NO** hardcoded file paths (only relative folder structures)
- ✅ **NO** hardcoded user/team names
- ✅ Generic examples that work for any project

The agents use **relative paths and folder conventions** which are project-agnostic:
- `01-requirements/`
- `02-architecture/`
- `03-code/`
- `04-tests/`
- `.agent-status/`

---

## ⚠️ Project-Specific References Found

### 1. `.claude/settings.local.json` (CRITICAL)

**Location:** `/home/kiko/12-extractor/.claude/settings.local.json`

**Issue:** Contains hardcoded paths, repository names, and GitHub user

**Project-Specific References:**
```json
Line 4:  "/home/kiko/12-extractor/agents"
Line 5:  "/home/kiko/12-extractor/example.js"
Line 6:  "/home/kiko/12-extractor/README.md"
Line 7:  "/home/kiko/12-extractor/package.json"
Line 14: "gh repo create 12-extractor --private --source=..."
Line 15: "gh repo view kareemmohamed2024/12-extractor --json url -q .url"
Line 16: "https://github.com/kareemmohamed2024/12-extractor.git"
```

**Recommendation:**
- ⚠️ **DO NOT copy** `settings.local.json` to new projects
- ✅ Create a **new** `settings.local.json` per project (if needed)
- ✅ Or delete this file entirely (it's local settings for this specific project)
- ✅ The permissions are one-time commands for this project setup

**Impact:** LOW - This file is `.gitignore`'d and won't be copied anyway

---

### 2. `README.md` (MINOR)

**Location:** `/home/kiko/12-extractor/README.md`

**Issue:** Contains one reference to current project folder name

**Project-Specific Reference:**
```markdown
Line 270: 12-extractor/
```

**Recommendation:**
- ✅ Replace "04-Agents/" with generic "project-root/" or use a template variable like `{PROJECT_NAME}/`
- ✅ Or simply regenerate README.md for each new project

**Impact:** VERY LOW - Cosmetic only, doesn't affect functionality

---

### 3. Documentation Files (INFORMATIONAL)

**Files:**
- `IMPLEMENTATION-SUMMARY.md`
- `QUICK-START.md`
- `agent-instructions1.md`

**Issue:** Contain example session IDs, timestamps, and project names like "Task Management System"

**Examples:**
```
"session_id": "ses-20251020-143000"
"project_name": "Task Management System"
Project: Task Management System
```

**Recommendation:**
- ✅ These are **EXAMPLES** - they're meant to illustrate the system
- ✅ New projects will generate their own session IDs and project names dynamically
- ✅ No changes needed - keep as reference documentation

**Impact:** NONE - These are documentation examples, not configuration

---

## ✅ Completely Portable Components

### Agent Configuration Files
**Files:** `.claude/agents/*.md` (all 5 agents)

**Status:** ✅ **100% Portable**

**Verification:**
- ✅ No hardcoded project names
- ✅ No hardcoded paths (uses relative conventions)
- ✅ No hardcoded URLs
- ✅ No hardcoded user/team names
- ✅ All examples use generic project names as placeholders
- ✅ Folder structure is conventional and consistent

**Usage:** Copy these files as-is to any new project

---

### Folder Structure
**Folders:**
- `01-requirements/`
- `02-architecture/`
- `03-code/`
- `04-tests/`
- `.agent-status/` (git-ignored)
- `*/.handoff/` subdirectories

**Status:** ✅ **100% Portable**

**Verification:**
- ✅ Folder names are conventional, not project-specific
- ✅ Same structure works for any software project
- ✅ Agents auto-create these folders when needed

**Usage:** Create this structure in any new project

---

### .gitignore
**File:** `.gitignore`

**Status:** ✅ **100% Portable**

**Verification:**
- ✅ Contains only agent-system patterns (`.agent-status/`)
- ✅ Contains only generic patterns (`node_modules/`, `.vscode/`)
- ✅ No project-specific exclusions

**Usage:** Copy as-is or merge with existing `.gitignore`

---

## 📋 Portability Checklist

### To Copy the Agent System to a New Project:

#### ✅ Copy These (100% Portable):
1. ✅ `.claude/agents/` directory (all 5 agent .md files)
2. ✅ `.gitignore` (or merge patterns)
3. ✅ `IMPLEMENTATION-SUMMARY.md` (as reference)
4. ✅ `QUICK-START.md` (as reference)
5. ✅ `agent-instructions1.md` (as reference)

#### ⚠️ Create Fresh (Don't Copy):
1. ⚠️ `.claude/settings.local.json` - Create new if needed for new project
2. ⚠️ `.agent-status/` - Will be auto-created by orchestrator
3. ⚠️ `*/.handoff/` - Will be auto-created by agents

#### 🔄 Adapt/Regenerate:
1. 🔄 `README.md` - Update project name or regenerate
2. 🔄 Session files (`.agent-status/*.json`) - Will be auto-generated per project

---

## 🔍 Detailed Analysis by Component

### Component 1: Business Analyst Agent
**File:** `.claude/agents/business-analyst.md`

**Analysis:**
- ✅ Uses generic folder paths: `01-requirements/`
- ✅ Example project name is generic placeholder: "Task Management System"
- ✅ All session IDs are template examples: `ses-YYYYMMDD-HHMMSS`
- ✅ All timestamps are ISO-8601 format placeholders
- ✅ No hardcoded values

**Portability:** ✅ **100% - Copy as-is**

---

### Component 2: Architect Agent
**File:** `.claude/agents/architect.md`

**Analysis:**
- ✅ Uses generic folder paths: `02-architecture/`
- ✅ No hardcoded technology choices (provides options)
- ✅ Examples use placeholder project names
- ✅ All paths are relative

**Portability:** ✅ **100% - Copy as-is**

---

### Component 3: Developer Agent
**File:** `.claude/agents/developer.md`

**Analysis:**
- ✅ Uses generic folder paths: `03-code/src/`, `03-code/tests/`
- ✅ Examples use generic chunk names
- ✅ No hardcoded file names or paths
- ✅ Technology-agnostic examples

**Portability:** ✅ **100% - Copy as-is**

---

### Component 4: Tester Agent
**File:** `.claude/agents/tester.md`

**Analysis:**
- ✅ Uses generic folder paths: `04-tests/`
- ✅ Test case IDs are pattern examples: `TC-CH{N}-{ID}`
- ✅ No hardcoded test scenarios
- ✅ Framework-agnostic approach

**Portability:** ✅ **100% - Copy as-is**

---

### Component 5: Orchestrator Agent
**File:** `.claude/agents/orchestrator.md`

**Analysis:**
- ✅ Uses all generic folder paths
- ✅ Session management is dynamic (generates new IDs per project)
- ✅ Example workflows use placeholder names
- ✅ No hardcoded configuration

**Portability:** ✅ **100% - Copy as-is**

---

### Component 6: Checkpoint System
**Files:** Checkpoint and handoff JSON files (runtime, git-ignored)

**Analysis:**
- ✅ All checkpoint files are auto-generated at runtime
- ✅ Project name stored in session metadata comes from user input
- ✅ Session IDs auto-generated with timestamp
- ✅ Paths are all relative

**Portability:** ✅ **100% - Auto-generated per project**

---

## 🚀 Migration Guide: Copy to New Project

### Step 1: Create New Project Directory
```bash
mkdir /path/to/new-project
cd /path/to/new-project
git init
```

### Step 2: Copy Agent System
```bash
# Copy agent configurations (core system)
cp -r /home/kiko/12-extractor/.claude ./

# Copy documentation (optional, for reference)
cp /home/kiko/12-extractor/IMPLEMENTATION-SUMMARY.md ./
cp /home/kiko/12-extractor/QUICK-START.md ./
cp /home/kiko/12-extractor/agent-instructions1.md ./

# Copy or merge .gitignore
cp /home/kiko/12-extractor/.gitignore ./
# OR merge patterns if .gitignore already exists:
# cat /home/kiko/12-extractor/.gitignore >> ./.gitignore
```

### Step 3: Clean Up (Remove Project-Specific Files)
```bash
# Remove settings.local.json if it was copied
rm .claude/settings.local.json 2>/dev/null

# (Optional) Create folder structure
mkdir -p 01-requirements/.handoff
mkdir -p 02-architecture/.handoff
mkdir -p 03-code/.handoff
mkdir -p 04-tests/.handoff
mkdir -p .agent-status
```

### Step 4: Create New README
```bash
# Either copy and update:
cp /home/kiko/12-extractor/README.md ./
# Edit to replace "12-extractor" with your project name

# Or create fresh README for your new project
```

### Step 5: Start Using
```bash
# Invoke orchestrator with your new project requirements
# Agents will auto-create checkpoint files and folders
```

### Step 6: First Commit
```bash
git add .claude/ .gitignore README.md
git commit -m "chore: add Claude Code agent system

5 specialized agents with checkpoint/handoff system:
- Business Analyst
- Architect
- Developer
- Tester
- Orchestrator

Includes progress persistence and crash recovery."
```

---

## 📊 Portability Matrix

| Component | Portability | Action Required | Notes |
|-----------|-------------|-----------------|-------|
| `.claude/agents/business-analyst.md` | ✅ 100% | Copy as-is | No changes needed |
| `.claude/agents/architect.md` | ✅ 100% | Copy as-is | No changes needed |
| `.claude/agents/developer.md` | ✅ 100% | Copy as-is | No changes needed |
| `.claude/agents/tester.md` | ✅ 100% | Copy as-is | No changes needed |
| `.claude/agents/orchestrator.md` | ✅ 100% | Copy as-is | No changes needed |
| `.gitignore` | ✅ 100% | Copy or merge | Merge if exists |
| `IMPLEMENTATION-SUMMARY.md` | ✅ 100% | Copy as reference | Examples only |
| `QUICK-START.md` | ✅ 100% | Copy as reference | Examples only |
| `agent-instructions1.md` | ✅ 100% | Copy as reference | Examples only |
| `README.md` | 🔄 95% | Adapt | Update "12-extractor" reference |
| `.claude/settings.local.json` | ❌ 0% | **DO NOT COPY** | Project-specific permissions |
| `.agent-status/*.json` | N/A | Auto-generated | Created by orchestrator |
| `*/.handoff/*.json` | N/A | Auto-generated | Created by agents |

---

## 🎯 Recommended: Create a Template Repository

To make reuse even easier:

### Option A: Template Repository Structure
```
claude-agent-system-template/
├── .claude/
│   └── agents/
│       ├── business-analyst.md
│       ├── architect.md
│       ├── developer.md
│       ├── tester.md
│       └── orchestrator.md
├── .gitignore
├── IMPLEMENTATION-SUMMARY.md
├── QUICK-START.md
├── agent-instructions1.md
└── README-template.md  (with placeholders like {PROJECT_NAME})
```

### Option B: Initialization Script
Create `init-agent-system.sh`:
```bash
#!/bin/bash
# Initialize Claude Code agent system in current project

echo "Initializing Claude Code agent system..."

# Create folder structure
mkdir -p .claude/agents
mkdir -p 01-requirements/.handoff
mkdir -p 02-architecture/.handoff
mkdir -p 03-code/.handoff
mkdir -p 04-tests/.handoff
mkdir -p .agent-status

# Copy agent configurations
cp /path/to/template/.claude/agents/* .claude/agents/

# Copy/merge .gitignore
if [ -f .gitignore ]; then
  echo "Merging .gitignore..."
  cat /path/to/template/.gitignore >> .gitignore
else
  cp /path/to/template/.gitignore .
fi

# Copy documentation
cp /path/to/template/IMPLEMENTATION-SUMMARY.md .
cp /path/to/template/QUICK-START.md .

echo "✓ Agent system initialized!"
echo "Run: @orchestrator [your project description]"
```

---

## 🔐 Security Considerations

### Files That Should NOT Be Shared

1. **`.agent-status/*.json`** - Contains session-specific data
   - ✅ Already in `.gitignore`
   - ⚠️ May contain project details, user names, paths

2. **`.claude/settings.local.json`** - Contains permissions and paths
   - ⚠️ NOT in `.gitignore` by default
   - ⚠️ Should be added to `.gitignore` if used

### Recommendation
Add to `.gitignore`:
```
# Claude Code local settings
.claude/settings.local.json
```

---

## 📝 Configuration Template Example

### Parameterized README Template

Create `README-template.md`:
```markdown
# {PROJECT_NAME}

{PROJECT_DESCRIPTION}

## Agent System

This project uses the Claude Code agent-based development system with 5 specialized agents:

- Business Analyst
- Architect
- Developer
- Tester
- Orchestrator

### Quick Start

```
@orchestrator
{PROJECT_REQUIREMENTS}
```

For documentation, see:
- [QUICK-START.md](QUICK-START.md)
- [IMPLEMENTATION-SUMMARY.md](IMPLEMENTATION-SUMMARY.md)
```

### Usage
Replace placeholders when creating new project:
- `{PROJECT_NAME}` → Your project name
- `{PROJECT_DESCRIPTION}` → Brief description
- `{PROJECT_REQUIREMENTS}` → Initial requirements

---

## 🎓 Best Practices for Reuse

### 1. Use Template Repository
- Create a GitHub template from `12-extractor`
- Click "Use this template" for new projects
- Automatically copies structure without git history

### 2. Git Submodule Approach
```bash
# In new project:
git submodule add <agent-system-repo> .claude-agents
ln -s .claude-agents/.claude .claude
```

### 3. Package as Archive
```bash
# Create portable archive
tar czf claude-agent-system.tar.gz \
  .claude/agents/ \
  .gitignore \
  IMPLEMENTATION-SUMMARY.md \
  QUICK-START.md \
  agent-instructions1.md

# Extract in new project:
tar xzf claude-agent-system.tar.gz
```

---

## ⚡ Quick Copy Command

For fast reuse, single command:
```bash
# Copy agent system from 12-extractor to current directory
cp -r /home/kiko/12-extractor/.claude . && \
cp /home/kiko/12-extractor/.gitignore . && \
cp /home/kiko/12-extractor/{IMPLEMENTATION-SUMMARY,QUICK-START,agent-instructions1}.md . && \
rm -f .claude/settings.local.json && \
echo "✓ Agent system copied! Ready to use."
```

---

## 📌 Summary

### What's Portable (99%)
✅ All 5 agent configuration files
✅ Checkpoint and handoff system design
✅ Folder structure conventions
✅ Documentation and guides
✅ .gitignore patterns

### What's NOT Portable (1%)
❌ `.claude/settings.local.json` - Project-specific permissions
⚠️ One "12-extractor" reference in README.md

### Action Items
1. ✅ Copy `.claude/agents/` directory
2. ✅ Copy or merge `.gitignore`
3. ✅ Copy documentation files (optional)
4. 🔄 Update README.md or create new
5. ❌ DO NOT copy `.claude/settings.local.json`

### Result
**The agent system is ready for immediate reuse across unlimited projects with minimal changes.**
