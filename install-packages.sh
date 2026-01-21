#!/bin/bash

#############################################
# Knowledge Extraction System - Package Installer
# Installs: EasyOCR, ChromaDB, Sentence Transformers
# Date: 2025-11-12
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Log file
LOGFILE="/mnt/h/12-extractor/installation.log"
PROJECT_DIR="/mnt/h/12-extractor"

# Counters
SUCCESS_COUNT=0
FAILURE_COUNT=0
TOTAL_STEPS=8

# Function to print colored messages
print_header() {
    echo -e "\n${BLUE}================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "$LOGFILE"
    ((SUCCESS_COUNT++))
}

print_error() {
    echo -e "${RED}❌ FAILED:${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED: $1" >> "$LOGFILE"
    ((FAILURE_COUNT++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOGFILE"
}

print_info() {
    echo -e "${CYAN}ℹ️  INFO:${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOGFILE"
}

print_progress() {
    echo -e "${CYAN}⏳ PROGRESS:${NC} $1"
}

# Function to check if package is installed
check_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Start logging
echo "================================================================" > "$LOGFILE"
echo "Installation Log - $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGFILE"
echo "================================================================" >> "$LOGFILE"

print_header "Knowledge Extraction System - Package Installation"
print_info "Installation started at $(date '+%Y-%m-%d %H:%M:%S')"
print_info "Log file: $LOGFILE"
print_info "Total steps: $TOTAL_STEPS"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

#############################################
# STEP 1: Check Python version
#############################################
print_header "Step 1/$TOTAL_STEPS: Checking Python Version"
PYTHON_VERSION=$(python3 --version 2>&1)
if [ $? -eq 0 ]; then
    print_success "Python found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

#############################################
# STEP 2: Check pip
#############################################
print_header "Step 2/$TOTAL_STEPS: Checking pip"
PIP_VERSION=$(pip3 --version 2>&1)
if [ $? -eq 0 ]; then
    print_success "pip found: $PIP_VERSION"
else
    print_error "pip3 not found. Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
    if [ $? -eq 0 ]; then
        print_success "pip installed successfully"
    else
        print_error "Failed to install pip"
        exit 1
    fi
fi

#############################################
# STEP 3: Install System Dependencies
#############################################
print_header "Step 3/$TOTAL_STEPS: Installing System Dependencies"
print_progress "Installing build-essential, python3-dev..."

sudo apt update >> "$LOGFILE" 2>&1
if [ $? -eq 0 ]; then
    print_success "apt update completed"
else
    print_warning "apt update had some warnings (continuing...)"
fi

sudo apt install -y python3-dev build-essential libmagic1 >> "$LOGFILE" 2>&1
if [ $? -eq 0 ]; then
    print_success "System dependencies installed"
else
    print_warning "Some system dependencies may have failed (continuing...)"
fi

#############################################
# STEP 4: Install PyTorch (EasyOCR dependency)
#############################################
print_header "Step 4/$TOTAL_STEPS: Installing PyTorch"
print_info "This may take 5-10 minutes depending on your connection..."

# Check if torch already installed
if check_package "torch"; then
    TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
    print_success "PyTorch already installed: $TORCH_VERSION"
    ((SUCCESS_COUNT++))
else
    print_progress "Installing PyTorch..."

    pip3 install torch torchvision --break-system-packages >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ] && check_package "torch"; then
        TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
        print_success "PyTorch installed successfully: $TORCH_VERSION"
    else
        print_error "PyTorch installation failed. Check log: $LOGFILE"
        print_info "Trying alternative installation method..."

        pip3 install torch torchvision --break-system-packages --no-cache-dir >> "$LOGFILE" 2>&1

        if check_package "torch"; then
            print_success "PyTorch installed with alternative method"
        else
            print_error "PyTorch installation failed completely"
        fi
    fi
fi

#############################################
# STEP 5: Install OpenCV (EasyOCR dependency)
#############################################
print_header "Step 5/$TOTAL_STEPS: Installing OpenCV"

if check_package "cv2"; then
    print_success "OpenCV already installed"
    ((SUCCESS_COUNT++))
else
    print_progress "Installing OpenCV..."

    pip3 install opencv-python-headless --break-system-packages >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ] && check_package "cv2"; then
        print_success "OpenCV installed successfully"
    else
        print_error "OpenCV installation failed"
    fi
fi

#############################################
# STEP 6: Install EasyOCR
#############################################
print_header "Step 6/$TOTAL_STEPS: Installing EasyOCR"
print_info "This is the longest step - may take 10-15 minutes..."
print_info "Downloading models and dependencies..."

if check_package "easyocr"; then
    EASYOCR_VERSION=$(python3 -c "import easyocr; print(easyocr.__version__)" 2>/dev/null)
    print_success "EasyOCR already installed: $EASYOCR_VERSION"
    ((SUCCESS_COUNT++))
else
    print_progress "Installing EasyOCR (this will take a while)..."

    # Show progress indicator
    pip3 install easyocr --break-system-packages 2>&1 | tee -a "$LOGFILE" | while IFS= read -r line; do
        echo -ne "${CYAN}.${NC}"
    done
    echo ""

    if check_package "easyocr"; then
        EASYOCR_VERSION=$(python3 -c "import easyocr; print(easyocr.__version__)" 2>/dev/null)
        print_success "EasyOCR installed successfully: $EASYOCR_VERSION"
    else
        print_error "EasyOCR installation failed"
        print_info "Trying with --no-cache-dir..."

        pip3 install easyocr --break-system-packages --no-cache-dir >> "$LOGFILE" 2>&1

        if check_package "easyocr"; then
            print_success "EasyOCR installed with alternative method"
        else
            print_error "EasyOCR installation failed completely"
            print_warning "You may need to install manually or check network connection"
        fi
    fi
fi

#############################################
# STEP 7: Install ChromaDB
#############################################
print_header "Step 7/$TOTAL_STEPS: Installing ChromaDB"
print_info "Installing ChromaDB and dependencies..."

if check_package "chromadb"; then
    CHROMA_VERSION=$(python3 -c "import chromadb; print(chromadb.__version__)" 2>/dev/null)
    print_success "ChromaDB already installed: $CHROMA_VERSION"
    ((SUCCESS_COUNT++))
else
    print_progress "Installing ChromaDB..."

    pip3 install chromadb --break-system-packages >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ] && check_package "chromadb"; then
        CHROMA_VERSION=$(python3 -c "import chromadb; print(chromadb.__version__)" 2>/dev/null)
        print_success "ChromaDB installed successfully: $CHROMA_VERSION"
    else
        print_error "ChromaDB installation failed"
        print_info "Retrying with --no-cache-dir..."

        pip3 install chromadb --break-system-packages --no-cache-dir >> "$LOGFILE" 2>&1

        if check_package "chromadb"; then
            print_success "ChromaDB installed with alternative method"
        else
            print_error "ChromaDB installation failed completely"
        fi
    fi
fi

#############################################
# STEP 8: Install Sentence Transformers
#############################################
print_header "Step 8/$TOTAL_STEPS: Installing Sentence Transformers"
print_info "Installing sentence-transformers for embeddings..."

if check_package "sentence_transformers"; then
    print_success "Sentence Transformers already installed"
    ((SUCCESS_COUNT++))
else
    print_progress "Installing Sentence Transformers..."

    pip3 install sentence-transformers --break-system-packages >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ] && check_package "sentence_transformers"; then
        print_success "Sentence Transformers installed successfully"
    else
        print_error "Sentence Transformers installation failed"
    fi
fi

#############################################
# FINAL VERIFICATION
#############################################
print_header "Final Verification"
print_info "Verifying all packages..."

FINAL_SUCCESS=0
FINAL_FAILURE=0

# Check EasyOCR
if check_package "easyocr"; then
    EASYOCR_VERSION=$(python3 -c "import easyocr; print(easyocr.__version__)" 2>/dev/null)
    print_success "EasyOCR: $EASYOCR_VERSION"
    ((FINAL_SUCCESS++))
else
    print_error "EasyOCR: NOT INSTALLED"
    ((FINAL_FAILURE++))
fi

# Check ChromaDB
if check_package "chromadb"; then
    CHROMA_VERSION=$(python3 -c "import chromadb; print(chromadb.__version__)" 2>/dev/null)
    print_success "ChromaDB: $CHROMA_VERSION"
    ((FINAL_SUCCESS++))
else
    print_error "ChromaDB: NOT INSTALLED"
    ((FINAL_FAILURE++))
fi

# Check Sentence Transformers
if check_package "sentence_transformers"; then
    print_success "Sentence Transformers: INSTALLED"
    ((FINAL_SUCCESS++))
else
    print_error "Sentence Transformers: NOT INSTALLED"
    ((FINAL_FAILURE++))
fi

# Check PyTorch
if check_package "torch"; then
    TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
    print_success "PyTorch: $TORCH_VERSION"
    ((FINAL_SUCCESS++))
else
    print_error "PyTorch: NOT INSTALLED"
    ((FINAL_FAILURE++))
fi

#############################################
# SUMMARY
#############################################
print_header "Installation Summary"

echo -e "${CYAN}Completed Steps:${NC}    $SUCCESS_COUNT/$TOTAL_STEPS"
echo -e "${CYAN}Final Verification:${NC} $FINAL_SUCCESS/4 packages working"

if [ $FINAL_FAILURE -gt 0 ]; then
    echo -e "${RED}Failed Packages:${NC}    $FINAL_FAILURE/4"
fi

echo ""
echo -e "${CYAN}Installation Time:${NC}  Completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${CYAN}Log File:${NC}           $LOGFILE"
echo ""

# Final status
if [ $FINAL_SUCCESS -eq 4 ]; then
    print_header "✅ ALL PACKAGES INSTALLED SUCCESSFULLY!"
    echo ""
    print_info "Next steps:"
    echo "  1. Initialize ChromaDB collection"
    echo "  2. Process Book 1 with real OCR"
    echo "  3. Sync to ChromaDB for semantic search"
    echo ""
    print_info "Run: python3 -c \"import easyocr, chromadb; print('Ready!')\" to verify"
    exit 0
else
    print_header "⚠️  INSTALLATION COMPLETED WITH WARNINGS"
    echo ""
    print_warning "$FINAL_FAILURE package(s) failed to install"
    print_info "Check log file for details: $LOGFILE"
    echo ""

    if ! check_package "easyocr"; then
        print_info "To retry EasyOCR:"
        echo "  pip3 install easyocr --break-system-packages --no-cache-dir"
    fi

    if ! check_package "chromadb"; then
        print_info "To retry ChromaDB:"
        echo "  pip3 install chromadb --break-system-packages"
    fi

    exit 1
fi
