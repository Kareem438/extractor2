#!/bin/bash

##############################################################################
# Knowledge Extraction System - Automated Setup Script
# Platform: Linux/Mac (Windows users: run commands manually in PowerShell)
# Created: 2025-11-03
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

##############################################################################
# Step 1: Check Prerequisites
##############################################################################

print_header "Step 1: Checking Prerequisites"

# Check Python version
print_info "Checking Python version..."
if command -v python3.9 &> /dev/null; then
    PYTHON_CMD=python3.9
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if (( $(echo "$PYTHON_VERSION >= 3.9" | bc -l) )); then
        PYTHON_CMD=python3
    else
        print_error "Python 3.9+ required, found Python $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3.9+ not found. Please install Python 3.9 or higher."
    exit 1
fi

print_success "Python found: $($PYTHON_CMD --version)"

# Check pip
print_info "Checking pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip not found. Please install pip."
    exit 1
fi
print_success "pip found: $($PYTHON_CMD -m pip --version)"

# Check Tesseract (optional, warn if missing)
print_info "Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    print_success "Tesseract found: $(tesseract --version | head -n 1)"
else
    print_warning "Tesseract OCR not found. You'll need to install it manually."
    print_info "Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara"
    print_info "Mac: brew install tesseract tesseract-lang"
fi

# Check PostgreSQL connection (optional, check later)
print_info "PostgreSQL connection will be checked after configuration."

##############################################################################
# Step 2: Create Virtual Environment
##############################################################################

print_header "Step 2: Creating Virtual Environment"

if [ -d "venv" ]; then
    print_warning "Virtual environment 'venv' already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing venv..."
        rm -rf venv
    else
        print_info "Using existing venv."
    fi
fi

if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created."
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

print_success "Virtual environment activated."

##############################################################################
# Step 3: Upgrade pip
##############################################################################

print_header "Step 3: Upgrading pip"

print_info "Upgrading pip..."
pip install --upgrade pip --quiet
print_success "pip upgraded to $(pip --version)"

##############################################################################
# Step 4: Install Python Dependencies
##############################################################################

print_header "Step 4: Installing Python Dependencies"

if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found!"
    exit 1
fi

print_info "Installing dependencies from requirements.txt..."
print_warning "This will take 5-10 minutes and download ~1.65 GB..."

pip install -r requirements.txt

print_success "All Python dependencies installed."

##############################################################################
# Step 5: Download AI Models
##############################################################################

print_header "Step 5: Downloading AI Models"

print_warning "Downloading AI models (~1.4 GB). This may take 10-20 minutes..."

# Download SBERT model
print_info "Downloading SBERT model (420 MB)..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" || {
    print_warning "SBERT model download may have failed (will retry on first use)"
}
print_success "SBERT model downloaded."

# Download BLIP model
print_info "Downloading BLIP model (990 MB)..."
python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base'); BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')" || {
    print_warning "BLIP model download may have failed (will retry on first use)"
}
print_success "BLIP model downloaded."

# Download spaCy model
print_info "Downloading spaCy English model (12 MB)..."
python -m spacy download en_core_web_sm || {
    print_warning "spaCy model download failed (will retry on first use)"
}
print_success "spaCy model downloaded."

##############################################################################
# Step 6: Create Configuration Files
##############################################################################

print_header "Step 6: Creating Configuration Files"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_info "Creating .env from .env.example..."
        cp .env.example .env
        print_success ".env file created."
        print_warning "IMPORTANT: Edit .env and configure your database connection!"
    else
        print_info "Creating default .env file..."
        cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://knowledge_app:your_password@localhost:5432/knowledge_extraction

# Tesseract Configuration
TESSERACT_PATH=/usr/bin/tesseract

# Model Cache Directory
MODEL_CACHE_DIR=~/.cache/models

# Processing Configuration
CHECKPOINT_FREQUENCY=50
BATCH_INSERT_SIZE=50

# Image Configuration
IMAGE_MAX_WIDTH=800
IMAGE_MAX_HEIGHT=600
EOF
        print_success ".env file created."
        print_warning "IMPORTANT: Edit .env and configure your database connection!"
    fi
else
    print_info ".env file already exists (not modified)."
fi

##############################################################################
# Step 7: Test Database Connection
##############################################################################

print_header "Step 7: Testing Database Connection"

print_info "Checking database connection..."
print_warning "Make sure PostgreSQL is running and .env is configured!"

python -c "
import sys
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL or 'your_password' in DATABASE_URL:
    print('ERROR: Please configure DATABASE_URL in .env file!')
    sys.exit(1)

try:
    from sqlalchemy import create_engine
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    print('SUCCESS: Database connection working!')
    conn.close()
except Exception as e:
    print(f'WARNING: Database connection failed: {e}')
    print('Please check your DATABASE_URL and ensure PostgreSQL is running.')
    sys.exit(0)  # Don't fail setup, just warn
" || print_warning "Database connection test skipped or failed. Configure .env and retry."

##############################################################################
# Step 8: Initialize Database (Optional)
##############################################################################

print_header "Step 8: Database Initialization"

read -p "Do you want to initialize the database now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "src/database/init_db.py" ]; then
        print_info "Initializing database..."
        python src/database/init_db.py || {
            print_warning "Database initialization failed. You can run it manually later:"
            print_info "python src/database/init_db.py"
        }
    else
        print_warning "src/database/init_db.py not found. Skipping database initialization."
    fi
else
    print_info "Database initialization skipped. Run manually when ready:"
    print_info "python src/database/init_db.py"
fi

##############################################################################
# Step 9: Verify Installation
##############################################################################

print_header "Step 9: Verifying Installation"

print_info "Running verification checks..."

# Check Python packages
print_info "Checking Python packages..."
python -c "
import fastapi
import sqlalchemy
import PIL
import cv2
import pytesseract
import fitz
import sentence_transformers
import transformers
print('All critical packages imported successfully!')
" && print_success "Python packages OK" || print_error "Some packages failed to import"

# Check Tesseract
if command -v tesseract &> /dev/null; then
    print_success "Tesseract OCR OK"
else
    print_warning "Tesseract OCR not found in PATH"
fi

##############################################################################
# Setup Complete
##############################################################################

print_header "Setup Complete!"

print_success "Knowledge Extraction System setup finished successfully!"
echo ""
print_info "Next steps:"
echo "  1. Edit .env file with your database credentials"
echo "  2. Ensure PostgreSQL is running with pgvector extension"
echo "  3. Initialize database: python src/database/init_db.py"
echo "  4. Start application: python src/main.py"
echo "  5. Open browser: http://localhost:8000"
echo ""
print_info "To activate virtual environment in future sessions:"
echo "  source venv/bin/activate"
echo ""
print_info "For detailed instructions, see:"
echo "  02-architecture/dependencies/prerequisites-checklist.md"
echo ""

print_success "Happy developing!"
echo ""

##############################################################################
# Windows PowerShell Alternative Commands
##############################################################################

cat << 'EOF' > SETUP_WINDOWS.txt
# Windows PowerShell Setup Commands
# Run these commands in PowerShell (as Administrator if needed)

# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download AI models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
python -c "from transformers import BlipProcessor, BlipForConditionalGeneration; BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base'); BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')"
python -m spacy download en_core_web_sm

# 5. Create .env file
copy .env.example .env
# Edit .env with notepad or your preferred editor

# 6. Initialize database
python src\database\init_db.py

# 7. Run application
python src\main.py

# 8. Open browser
start http://localhost:8000

EOF

print_info "Windows setup commands saved to: SETUP_WINDOWS.txt"

