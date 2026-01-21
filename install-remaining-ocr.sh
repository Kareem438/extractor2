#!/bin/bash

#############################################
# Install Remaining OCR Engines
# PaddleOCR, Surya OCR, Tesseract
# Date: 2025-11-12
#############################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Installing Remaining OCR Engines${NC}"
echo -e "${CYAN}========================================${NC}\n"

# Check if running as root for tesseract
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Note: Tesseract requires sudo. You may be prompted for password.${NC}\n"
fi

#############################################
# 1. PaddleOCR (GPU)
#############################################
echo -e "${CYAN}[1/3] Installing PaddleOCR with GPU support...${NC}"

# Check if already installed
python3 -c "from paddleocr import PaddleOCR" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PaddleOCR already installed${NC}\n"
else
    echo -e "${CYAN}Installing paddlepaddle-gpu...${NC}"
    pip3 install paddlepaddle-gpu --break-system-packages

    echo -e "${CYAN}Installing paddleocr...${NC}"
    pip3 install paddleocr --break-system-packages

    # Verify
    python3 -c "from paddleocr import PaddleOCR; print('✅ PaddleOCR installed successfully')" 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PaddleOCR installation complete${NC}\n"
    else
        echo -e "${RED}❌ PaddleOCR installation failed${NC}\n"
    fi
fi

#############################################
# 2. Surya OCR (GPU)
#############################################
echo -e "${CYAN}[2/3] Installing Surya OCR...${NC}"

# Check if already installed
python3 -c "import surya" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Surya OCR already installed${NC}\n"
else
    echo -e "${CYAN}Installing surya-ocr...${NC}"
    pip3 install surya-ocr --break-system-packages

    # Verify
    python3 -c "import surya; print('✅ Surya OCR installed successfully')" 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Surya OCR installation complete${NC}\n"
    else
        echo -e "${RED}❌ Surya OCR installation failed${NC}\n"
    fi
fi

#############################################
# 3. Tesseract (CPU)
#############################################
echo -e "${CYAN}[3/3] Installing Tesseract OCR...${NC}"

# Check if tesseract command exists
if command -v tesseract &> /dev/null; then
    echo -e "${GREEN}✅ Tesseract command already installed${NC}"
else
    echo -e "${CYAN}Installing tesseract system package...${NC}"
    sudo apt update
    sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Tesseract system package installed${NC}"
    else
        echo -e "${RED}❌ Tesseract system package installation failed${NC}"
    fi
fi

# Check Python wrapper
python3 -c "import pytesseract" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ pytesseract already installed${NC}\n"
else
    echo -e "${CYAN}Installing pytesseract Python wrapper...${NC}"
    pip3 install pytesseract --break-system-packages

    # Verify
    python3 -c "import pytesseract; print('✅ pytesseract installed successfully')" 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ pytesseract installation complete${NC}\n"
    else
        echo -e "${RED}❌ pytesseract installation failed${NC}\n"
    fi
fi

#############################################
# Final Verification
#############################################
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Final Verification${NC}"
echo -e "${CYAN}========================================${NC}\n"

python3 << 'EOF'
engines = {
    'PaddleOCR': 'from paddleocr import PaddleOCR',
    'Surya OCR': 'import surya',
    'Tesseract': 'import pytesseract',
    'EasyOCR': 'import easyocr'
}

success = 0
failed = 0

for name, import_cmd in engines.items():
    try:
        exec(import_cmd)
        print(f'✅ {name:15s} READY')
        success += 1
    except ImportError:
        print(f'❌ {name:15s} NOT INSTALLED')
        failed += 1

print(f'\nStatus: {success}/4 OCR engines ready')

if failed == 0:
    print('✅ All OCR engines installed successfully!')
else:
    print(f'⚠️  {failed} engine(s) need attention')
EOF

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Installation script complete!${NC}"
echo -e "${CYAN}========================================${NC}"
