# Virtual Environment Setup Guide

The virtual environment (`venv/`) is NOT stored in GitHub (too large, platform-specific).
Instead, use the requirements files to recreate it.

## If venv is Missing or Broken

```powershell
# 1. Create new virtual environment (Windows PowerShell)
cd H:\12-extractor
python -m venv venv

# 2. Activate it
.\venv\Scripts\activate

# 3. Upgrade pip first
python -m pip install --upgrade pip

# 4. Install all packages from frozen requirements
pip install -r 03-code/requirements-frozen.txt

# 5. Install PyTorch with CUDA (GPU support) - IMPORTANT!
# The frozen requirements has CPU-only torch, so reinstall with CUDA:
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# 6. Verify GPU support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Quick Verification

```powershell
# Check all critical packages
python -c "
import torch
import easyocr
import surya
import pytesseract
import chromadb
import anthropic
print('PyTorch:', torch.__version__, '- CUDA:', torch.cuda.is_available())
print('All packages OK!')
"
```

## Backup venv (Optional)

To create a backup copy of a working venv:

```powershell
# Create timestamped backup (run from H:\12-extractor)
$timestamp = Get-Date -Format "yyyy-MM-dd"
Copy-Item -Path "venv" -Destination "venv-backup-$timestamp" -Recurse
```

## Restore from Backup

```powershell
# If venv is broken, restore from backup
Remove-Item -Path "venv" -Recurse -Force
Rename-Item -Path "venv-backup-2025-01-15" -NewName "venv"
```

## Key Package Versions (Dec 2025)

| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.13.2 | Windows native |
| PyTorch | 2.9.1+cu126 | CUDA 12.6 for RTX 4070 |
| EasyOCR | 1.7.2 | Arabic + English |
| Surya OCR | 0.17.0 | GPU-accelerated |
| ChromaDB | 1.4.0 | Vector database |
| Anthropic | 0.75.0 | Claude Vision API |
