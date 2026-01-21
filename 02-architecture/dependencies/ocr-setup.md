# OCR Setup Guide - Cross-Platform (Ubuntu Dev → Windows 11 Deploy)

## 🎯 Overview

This guide covers setting up the 3-tier OCR system for quality-first text extraction:
- **Tier 1:** PaddleOCR (GPU) - Primary, 90% of pages, 2-3 sec/page
- **Tier 2:** Surya OCR (GPU) - Fallback, 8% of pages, 8-10 sec/page
- **Tier 3:** Tesseract (CPU) - Final fallback, 2% of pages, 60 sec/page

**Hardware:** NVIDIA RTX 4070 Laptop (8GB VRAM)
**Development:** Ubuntu
**Deployment:** Windows 11

---

## 📋 Prerequisites

### Ubuntu Development Environment

#### 1. NVIDIA Drivers & CUDA Toolkit 11.8

```bash
# Check NVIDIA driver
nvidia-smi

# Install CUDA Toolkit 11.8
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run
sudo sh cuda_11.8.0_520.61.05_linux.run

# Add to ~/.bashrc
export PATH=/usr/local/cuda-11.8/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH

# Reload
source ~/.bashrc

# Verify
nvcc --version  # Should show CUDA 11.8
```

#### 2. cuDNN 8.9 for CUDA 11.8

```bash
# Download from NVIDIA (requires login):
# https://developer.nvidia.com/cudnn

# Extract and install
tar -xzvf cudnn-linux-x86_64-8.9.x.x_cuda11-archive.tar.xz
cd cudnn-linux-x86_64-8.9.x.x_cuda11-archive

sudo cp include/cudnn*.h /usr/local/cuda-11.8/include
sudo cp lib/libcudnn* /usr/local/cuda-11.8/lib64
sudo chmod a+r /usr/local/cuda-11.8/include/cudnn*.h /usr/local/cuda-11.8/lib64/libcudnn*
```

#### 3. System Packages

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    build-essential \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara

# Verify Tesseract
tesseract --version  # Should show 4.x or 5.x
```

---

### Windows 11 Deployment Environment

#### 1. Python 3.11

```powershell
# Download from: https://www.python.org/downloads/windows/
# Install Python 3.11.x (64-bit)
# ✅ Check "Add Python to PATH" during installation
```

#### 2. NVIDIA CUDA Toolkit 11.8

```powershell
# Download from:
# https://developer.nvidia.com/cuda-11-8-0-download-archive

# Run installer: cuda_11.8.0_522.06_windows.exe
# Installation path: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\

# Verify (in PowerShell)
nvcc --version  # Should show CUDA 11.8
```

#### 3. cuDNN 8.9 for CUDA 11.8

```powershell
# Download from NVIDIA (requires login):
# https://developer.nvidia.com/cudnn

# Extract cudnn-windows-x86_64-8.9.x.x_cuda11-archive.zip

# Copy files:
# From: cudnn-windows-x86_64-8.9.x.x_cuda11-archive\bin\cudnn*.dll
# To: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\

# From: cudnn-windows-x86_64-8.9.x.x_cuda11-archive\include\cudnn*.h
# To: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\

# From: cudnn-windows-x86_64-8.9.x.x_cuda11-archive\lib\x64\cudnn*.lib
# To: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\
```

#### 4. Tesseract OCR

```powershell
# Download from:
# https://github.com/UB-Mannheim/tesseract/wiki

# Run installer: tesseract-ocr-w64-setup-5.x.x.exe
# Installation path: C:\Program Files\Tesseract-OCR\

# Add to PATH:
# System Properties → Environment Variables → Path → New:
# C:\Program Files\Tesseract-OCR\

# Download Arabic language data:
# From: https://github.com/tesseract-ocr/tessdata
# Files: eng.traineddata, ara.traineddata
# Copy to: C:\Program Files\Tesseract-OCR\tessdata\

# Verify
tesseract --version
tesseract --list-langs  # Should show: eng, ara
```

---

## 🐍 Python Virtual Environment Setup

### Ubuntu Development

**Script:** `setup-ocr-ubuntu.sh`

```bash
#!/bin/bash
# OCR Setup for Ubuntu Development Environment
# RTX 4070 Laptop (8GB VRAM)

set -e

echo "🚀 Setting up OCR environment for Ubuntu..."

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA 11.8 support
echo "📦 Installing PyTorch with CUDA 11.8..."
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118

# Install PaddlePaddle GPU version
echo "📦 Installing PaddlePaddle GPU..."
python -m pip install paddlepaddle-gpu==2.6.0 -i https://mirror.baidu.com/pypi/simple

# Install OCR packages
echo "📦 Installing OCR libraries..."
pip install paddleocr==2.7.3
pip install surya-ocr==0.4.14
pip install pytesseract==0.3.10

# Install PDF & Image processing
echo "📦 Installing PDF/Image libraries..."
pip install PyMuPDF==1.23.26
pip install opencv-python==4.9.0
pip install Pillow==10.2.0
pip install numpy==1.26.3

# Verify GPU access
echo "✅ Verifying GPU access..."
python -c "import paddle; print(f'PaddlePaddle GPU devices: {paddle.device.cuda.device_count()}')"
python -c "import torch; print(f'PyTorch CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'PyTorch CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo "✅ OCR environment setup complete for Ubuntu!"
echo "Activate with: source venv/bin/activate"
```

**Usage:**
```bash
chmod +x setup-ocr-ubuntu.sh
./setup-ocr-ubuntu.sh
```

---

### Windows 11 Deployment

**Script:** `setup-ocr-windows.ps1`

```powershell
# OCR Setup for Windows 11 Deployment Environment
# RTX 4070 Laptop (8GB VRAM)

Write-Host "🚀 Setting up OCR environment for Windows 11..." -ForegroundColor Green

# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA 11.8 support
Write-Host "📦 Installing PyTorch with CUDA 11.8..." -ForegroundColor Cyan
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118

# Install PaddlePaddle GPU version (Windows)
Write-Host "📦 Installing PaddlePaddle GPU..." -ForegroundColor Cyan
pip install paddlepaddle-gpu==2.6.0 -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html

# Install OCR packages
Write-Host "📦 Installing OCR libraries..." -ForegroundColor Cyan
pip install paddleocr==2.7.3
pip install surya-ocr==0.4.14
pip install pytesseract==0.3.10

# Install PDF & Image processing
Write-Host "📦 Installing PDF/Image libraries..." -ForegroundColor Cyan
pip install PyMuPDF==1.23.26
pip install opencv-python==4.9.0
pip install Pillow==10.2.0
pip install numpy==1.26.3

# Set Tesseract environment variable
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata"

# Verify GPU access
Write-Host "✅ Verifying GPU access..." -ForegroundColor Green
python -c "import paddle; print(f'PaddlePaddle GPU devices: {paddle.device.cuda.device_count()}')"
python -c "import torch; print(f'PyTorch CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'PyTorch CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

Write-Host "✅ OCR environment setup complete for Windows 11!" -ForegroundColor Green
Write-Host "Activate with: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
```

**Usage:**
```powershell
# Allow script execution (run as Administrator once)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run setup
.\setup-ocr-windows.ps1
```

---

## 🧪 Testing OCR Setup

**Test Script:** `test-ocr.py`

```python
"""
Test OCR setup on both Ubuntu and Windows
Tests all 3 tiers: PaddleOCR, Surya, Tesseract
"""

import sys
import time
import numpy as np
from PIL import Image

def test_gpu_availability():
    """Test GPU availability for PyTorch and PaddlePaddle"""
    print("=" * 60)
    print("Testing GPU Availability")
    print("=" * 60)

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"✅ PyTorch CUDA available: {cuda_available}")
        if cuda_available:
            print(f"   Device: {torch.cuda.get_device_name(0)}")
            print(f"   CUDA Version: {torch.version.cuda}")
            print(f"   VRAM Total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    except Exception as e:
        print(f"❌ PyTorch error: {e}")
        return False

    try:
        import paddle
        gpu_count = paddle.device.cuda.device_count()
        print(f"✅ PaddlePaddle GPU devices: {gpu_count}")
    except Exception as e:
        print(f"❌ PaddlePaddle error: {e}")
        return False

    return cuda_available and gpu_count > 0

def test_paddleocr():
    """Test PaddleOCR (Tier 1)"""
    print("\n" + "=" * 60)
    print("Testing PaddleOCR (Tier 1 - Primary)")
    print("=" * 60)

    try:
        from paddleocr import PaddleOCR

        print("Loading PaddleOCR English model...")
        start = time.time()
        ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True, show_log=False)
        load_time = time.time() - start
        print(f"✅ PaddleOCR loaded in {load_time:.2f}s")

        # Create test image
        img = Image.new('RGB', (800, 100), color='white')
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "PaddleOCR Test: Quality-First Extraction", fill='black')
        img_array = np.array(img)

        print("Running OCR...")
        start = time.time()
        result = ocr.ocr(img_array, cls=True)
        ocr_time = time.time() - start

        if result and result[0]:
            text = result[0][0][1][0]
            confidence = result[0][0][1][1]
            print(f"✅ PaddleOCR success in {ocr_time:.2f}s")
            print(f"   Text: {text}")
            print(f"   Confidence: {confidence:.2%}")
            return True
        else:
            print("❌ No text detected")
            return False

    except Exception as e:
        print(f"❌ PaddleOCR error: {e}")
        return False

def test_surya():
    """Test Surya OCR (Tier 2)"""
    print("\n" + "=" * 60)
    print("Testing Surya OCR (Tier 2 - Fallback)")
    print("=" * 60)

    try:
        from surya.ocr import run_ocr
        from surya.model.detection.segformer import load_model as load_det_model
        from surya.model.recognition.model import load_model as load_rec_model
        from surya.model.detection.processor import load_processor as load_det_processor
        from surya.model.recognition.processor import load_processor as load_rec_processor

        print("Loading Surya models...")
        start = time.time()
        det_model = load_det_model()
        det_processor = load_det_processor()
        rec_model = load_rec_model()
        rec_processor = load_rec_processor()
        load_time = time.time() - start
        print(f"✅ Surya loaded in {load_time:.2f}s")

        # Create test image
        img = Image.new('RGB', (800, 100), color='white')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "Surya OCR Test: State-of-the-Art Quality", fill='black')

        print("Running OCR...")
        start = time.time()
        predictions = run_ocr([img], [['en']], det_model, det_processor, rec_model, rec_processor)
        ocr_time = time.time() - start

        if predictions and predictions[0].text_lines:
            text = predictions[0].text_lines[0].text
            confidence = predictions[0].text_lines[0].confidence
            print(f"✅ Surya success in {ocr_time:.2f}s")
            print(f"   Text: {text}")
            print(f"   Confidence: {confidence:.2%}")
            return True
        else:
            print("❌ No text detected")
            return False

    except Exception as e:
        print(f"❌ Surya error: {e}")
        return False

def test_tesseract():
    """Test Tesseract (Tier 3)"""
    print("\n" + "=" * 60)
    print("Testing Tesseract (Tier 3 - CPU Fallback)")
    print("=" * 60)

    try:
        import pytesseract
        from PIL import Image, ImageDraw

        # Check Tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
        except Exception as e:
            print(f"❌ Tesseract not found. Is it installed and in PATH?")
            print(f"   Error: {e}")
            return False

        # Check available languages
        langs = pytesseract.get_languages()
        print(f"   Available languages: {', '.join(langs)}")

        if 'eng' not in langs or 'ara' not in langs:
            print("❌ Missing required languages (eng, ara)")
            return False

        # Create test image
        img = Image.new('RGB', (800, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "Tesseract Test: CPU Fallback", fill='black')

        print("Running OCR...")
        start = time.time()
        text = pytesseract.image_to_string(img, lang='eng')
        ocr_time = time.time() - start

        if text.strip():
            print(f"✅ Tesseract success in {ocr_time:.2f}s")
            print(f"   Text: {text.strip()}")
            return True
        else:
            print("❌ No text detected")
            return False

    except Exception as e:
        print(f"❌ Tesseract error: {e}")
        return False

def main():
    """Run all OCR tests"""
    print("\n" + "="* 60)
    print("OCR Setup Verification")
    print("3-Tier Strategy: PaddleOCR → Surya → Tesseract")
    print("=" * 60)

    results = {
        'GPU': test_gpu_availability(),
        'PaddleOCR (Tier 1)': test_paddleocr(),
        'Surya (Tier 2)': test_surya(),
        'Tesseract (Tier 3)': test_tesseract()
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")

    all_passed = all(results.values())
    print("=" * 60)
    if all_passed:
        print("✅ All OCR components ready!")
        return 0
    else:
        print("❌ Some components failed. Check errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

**Run Test:**
```bash
# Ubuntu
python test-ocr.py

# Windows
python test-ocr.py
```

---

## 📊 Expected Performance

**300-page book on RTX 4070:**

| Tier | Engine | Pages | Time/Page | Total Time | Accuracy (EN) | Accuracy (AR) |
|------|--------|-------|-----------|------------|---------------|---------------|
| 1 | PaddleOCR | 270 (90%) | 2-3 sec | 9-13 min | 96-98% | 92-95% |
| 2 | Surya | 24 (8%) | 8-10 sec | 3-4 min | 97-99% | 94-97% |
| 3 | Tesseract | 6 (2%) | 60 sec | 6 min | 90-95% | 75-85% |
| **Total** | | 300 | | **18-23 min** | **96-98%** | **92-95%** |

---

## 🔧 Troubleshooting

### PaddleOCR Issues

**Error: CUDA out of memory**
```python
# Reduce GPU memory allocation in OCR initialization
paddle_ocr = PaddleOCR(
    gpu_mem=4000,  # Reduce from 6000
    rec_batch_num=4  # Reduce from 8
)
```

**Error: Cannot find CUDA library**
```bash
# Ubuntu: Check LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH  # Should include /usr/local/cuda-11.8/lib64

# Windows: Check PATH
echo $env:PATH  # Should include CUDA bin directory
```

### Surya Issues

**Error: Model download timeout**
```bash
# Set longer timeout
export HF_HUB_DOWNLOAD_TIMEOUT=300

# Or manually download models
# https://huggingface.co/vikp/surya_det
# https://huggingface.co/vikp/surya_rec
```

### Tesseract Issues

**Error: TesseractNotFoundError**
```bash
# Ubuntu: Install Tesseract
sudo apt-get install tesseract-ocr

# Windows: Add to PATH
# C:\Program Files\Tesseract-OCR\
```

**Error: Language not found**
```bash
# Ubuntu: Install language data
sudo apt-get install tesseract-ocr-ara

# Windows: Download .traineddata files
# From: https://github.com/tesseract-ocr/tessdata
# Copy to: C:\Program Files\Tesseract-OCR\tessdata\
```

---

## ✅ Verification Checklist

Before proceeding to development:

- [ ] GPU detected by PyTorch (RTX 4070)
- [ ] GPU detected by PaddlePaddle
- [ ] CUDA 11.8 installed and accessible
- [ ] cuDNN 8.9 installed
- [ ] PaddleOCR English model loads successfully
- [ ] PaddleOCR Arabic model loads successfully
- [ ] Surya models load successfully
- [ ] Tesseract installed with eng + ara languages
- [ ] Test script passes all 4 tests
- [ ] VRAM usage under 6GB during OCR

---

**Created:** 2025-11-05
**Updated:** 2025-11-05
**Version:** 1.0
