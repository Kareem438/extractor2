"""Update documentation files for Windows PostgreSQL setup"""

import os

def update_start_here():
    """Update START-HERE.md"""
    path = r"H:\12-extractor\START-HERE.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update Quick Start section
    content = content.replace(
        "## Quick Start (5 minutes)\n\n### 1. Start PostgreSQL (WSL)\n```bash\nwsl -u root pg_ctlcluster 16 main start\n```\nNote: If version 16 not installed, try 15 or 14.",
        "## Quick Start (3 minutes)\n\n### 1. Verify PostgreSQL Service (Windows)\n```bash\nsc query postgresql-x64-16\n```\nExpected: STATE = RUNNING. If not running: `sc start postgresql-x64-16`"
    )

    # Update Claude Code Automated Startup section
    content = content.replace(
        "Step 1: Start PostgreSQL cluster (version 16, 15, or 14)\nBash(wsl -u root pg_ctlcluster 16 main start)\n\nStep 3: Test database connection",
        "Step 1: Verify PostgreSQL service is running\nBash(sc query postgresql-x64-16)\n\nStep 2: Test database connection"
    )

    content = content.replace(
        "Step 4: Start FastAPI server (use run_in_background=true parameter)",
        "Step 3: Start FastAPI server (use run_in_background=true parameter)"
    )

    content = content.replace(
        "Step 5: Wait and verify health\nBash(sleep 5 && curl -s http://localhost:7777/health)",
        "Step 4: Wait and verify health\nBash(ping -n 6 127.0.0.1 >nul && curl -s http://localhost:7777/health)"
    )

    content = content.replace(
        "- Use `wsl -u root` to run WSL commands without password prompts",
        "- PostgreSQL 16 runs natively on Windows as a Windows service"
    )

    # Update Components section
    content = content.replace(
        "- PostgreSQL Database (WSL)",
        "- PostgreSQL 16 Database (Windows Native)"
    )

    # Update Latest Session section
    content = content.replace(
        "## Latest Session (Dec 31, 2025)\n\n### Completed\n1. **Fixed venv** - Recreated from scratch with Python 3.13\n2. **PyTorch Upgrade** - 2.6.0+cu124 to 2.9.1+cu126\n3. **EasyOCR Fix** - Fixed Windows charmap encoding error\n4. **Documentation Reorganization** - Split into focused files\n5. **GitHub Sync** - All changes committed and pushed\n\n### Fixed Issues\n- EasyOCR charmap encoding error (Unicode progress bar on Windows)\n- HTML template encoding (UTF-8 for Windows compatibility)\n- venv broken after WSL/Windows path mismatch",
        "## Latest Session (Dec 31, 2025)\n\n### Completed\n1. **PostgreSQL Migration** - Migrated from WSL to Windows native PostgreSQL 16\n2. **Database Import** - Successfully imported backup with 33 tables and 1 book\n3. **Configuration Update** - Updated .env to use localhost instead of WSL IP\n4. **System Verification** - All services running correctly on Windows\n5. **Documentation Update** - Updated all docs for Windows PostgreSQL setup\n\n### Fixed Issues\n- WSL PostgreSQL networking issues (replaced with Windows native)\n- Database connection timeout from Windows to WSL\n- Unreliable WSL IP address changes"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Updated START-HERE.md")

def update_environment_config():
    """Update docs/ENVIRONMENT-CONFIG.md"""
    path = r"H:\12-extractor\docs\ENVIRONMENT-CONFIG.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update table
    content = content.replace(
        "| **PostgreSQL** | WSL (Ubuntu) | Accessed via localhost from Windows |",
        "| **PostgreSQL** | Windows (native) | PostgreSQL 16 Windows service |"
    )

    # Update WSL section
    content = content.replace(
        "### WSL Ubuntu - Start PostgreSQL\n\n```bash\nsudo service postgresql start\nsudo service postgresql status\n```",
        "### Windows - PostgreSQL Service\n\n```bash\n# Check service status\nsc query postgresql-x64-16\n\n# Start service if not running\nsc start postgresql-x64-16\n\n# Stop service\nsc stop postgresql-x64-16\n```"
    )

    # Update database connection note
    content = content.replace(
        "The Windows Python app connects to PostgreSQL running in WSL via:",
        "The Python app connects to PostgreSQL running natively on Windows via:"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Updated docs/ENVIRONMENT-CONFIG.md")

def update_quick_commands():
    """Update docs/QUICK-COMMANDS.md"""
    path = r"H:\12-extractor\docs\QUICK-COMMANDS.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update Full System Startup
    content = content.replace(
        "Step 1: Start PostgreSQL cluster (version 16, 15, or 14)\nBash(wsl -u root pg_ctlcluster 16 main start)\n\nStep 3: Test database connection",
        "Step 1: Verify PostgreSQL service is running\nBash(sc query postgresql-x64-16)\n\nStep 2: Test database connection"
    )

    content = content.replace(
        "Step 4: Start FastAPI server (run_in_background=true)",
        "Step 3: Start FastAPI server (run_in_background=true)"
    )

    content = content.replace(
        "Step 5: Verify health\nBash(sleep 5 && curl -s http://localhost:7777/health)",
        "Step 4: Verify health\nBash(ping -n 6 127.0.0.1 >nul && curl -s http://localhost:7777/health)"
    )

    # Update PostgreSQL section
    content = content.replace(
        "## PostgreSQL (WSL)\n\n```\n# Start PostgreSQL cluster (use version installed: 16, 15, or 14)\nBash(wsl -u root pg_ctlcluster 16 main start)\n\n# Stop PostgreSQL cluster\nBash(wsl -u root pg_ctlcluster 16 main stop)\n\n# Check cluster status\nBash(wsl -u root pg_lsclusters)\n```",
        "## PostgreSQL (Windows)\n\n```\n# Check PostgreSQL service status\nBash(sc query postgresql-x64-16)\n\n# Start PostgreSQL service\nBash(sc start postgresql-x64-16)\n\n# Stop PostgreSQL service\nBash(sc stop postgresql-x64-16)\n```"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Updated docs/QUICK-COMMANDS.md")

def update_troubleshooting():
    """Update docs/TROUBLESHOOTING.md"""
    path = r"H:\12-extractor\docs\TROUBLESHOOTING.md"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Update Database Connection Failed section
    content = content.replace(
        "## Database Connection Failed\n\n```bash\n# WSL - Check PostgreSQL status\nsudo service postgresql status\n\n# Restart if needed\nsudo service postgresql restart\n```\n\n```powershell\n# Windows - Test connection",
        "## Database Connection Failed\n\n```bash\n# Check PostgreSQL service status\nsc query postgresql-x64-16\n\n# Restart if needed\nsc stop postgresql-x64-16\nsc start postgresql-x64-16\n```\n\n```powershell\n# Test connection"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Updated docs/TROUBLESHOOTING.md")

def update_next_session_context():
    """Update NEXT-SESSION-CONTEXT.md to mark migration complete"""
    path = r"H:\12-extractor\NEXT-SESSION-CONTEXT.md"

    content = """# Next Session Context - Dec 31, 2025

## COMPLETED: PostgreSQL Migration to Windows

### Migration Status: ✅ Complete

The system has been successfully migrated from WSL PostgreSQL to native Windows PostgreSQL 16.

---

## What Was Completed (Dec 31)

### 1. PostgreSQL Windows Installation
- PostgreSQL 16.11 installed natively on Windows
- Service running as `postgresql-x64-16`
- Database: `knowledge_extraction`

### 2. Database Migration
- Backup created from WSL: `H:\\12-extractor\\db_backup.sql`
- Successfully imported to Windows PostgreSQL
- 33 tables created, 1 book imported
- pgvector extension skipped (not critical for basic functionality)

### 3. Configuration Updated
- `.env` file updated: `localhost` instead of WSL IP (172.24.134.250)
- Database connection tested and verified
- FastAPI server started successfully

### 4. Documentation Updated
- CLAUDE.md - Updated startup instructions for Windows PostgreSQL
- START-HERE.md - Updated quick start guide
- docs/ENVIRONMENT-CONFIG.md - Updated environment details
- docs/QUICK-COMMANDS.md - Updated command reference
- docs/TROUBLESHOOTING.md - Updated troubleshooting guide

---

## System Status

### All Services Running ✅
- **PostgreSQL 16**: Running on Windows (port 5432)
- **FastAPI Server**: Running on Windows (port 7777)
- **Database**: Connected successfully
- **Health Check**: Passing

### Connection Details
- Database Host: `localhost` (Windows)
- Database Port: `5432`
- Database Name: `knowledge_extraction`
- Database User: `postgres`
- Database Password: `postgres`

### Access Points
- Library: http://localhost:7777/library
- API Docs: http://localhost:7777/docs
- Health: http://localhost:7777/health

---

## Previous Session Work (Nov 30)

All previous work is preserved:
- Database migrations for level titles and selected_level columns
- Diagram Details UI v3
- Level Radio Button Selection
- All JavaScript functions for diagram/level handling

---

## Next Steps (Optional)

### pgvector Extension
The pgvector extension is not currently installed. If you need vector embeddings functionality:
1. Download pgvector from: https://github.com/pgvector/pgvector/releases
2. Install for PostgreSQL 16 on Windows
3. Run: `CREATE EXTENSION vector;` in knowledge_extraction database
4. Re-import knowledge_units tables

**Note:** System works fine without pgvector for basic document processing.

---

## Key Files

| File | Purpose |
|------|---------|
| `H:\\12-extractor\\db_backup.sql` | Database backup from WSL (archived) |
| `H:\\12-extractor\\03-code\\.env` | Configuration (updated for Windows) |
| `H:\\12-extractor\\CLAUDE.md` | System startup instructions |

---

**Resume Point:** System is ready to use. Follow startup instructions in CLAUDE.md or START-HERE.md.
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓ Updated NEXT-SESSION-CONTEXT.md")

if __name__ == "__main__":
    print("Updating documentation files for Windows PostgreSQL setup...\n")

    try:
        update_start_here()
        update_environment_config()
        update_quick_commands()
        update_troubleshooting()
        update_next_session_context()

        print("\n✅ All documentation files updated successfully!")
        print("\nUpdated files:")
        print("  - START-HERE.md")
        print("  - docs/ENVIRONMENT-CONFIG.md")
        print("  - docs/QUICK-COMMANDS.md")
        print("  - docs/TROUBLESHOOTING.md")
        print("  - NEXT-SESSION-CONTEXT.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
