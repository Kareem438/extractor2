# Local LLM for Arabic Document Layout Analysis

## Project Overview
Research and requirements gathering for running a local open-source LLM on a PC with 6GB GPU to automatically identify page boundaries in Arabic documents, outlining paragraphs, titles, and diagrams.

## Hardware Constraints
- **GPU:** NVIDIA RTX 4070 Laptop (8GB VRAM total)
- **System RAM:** 64GB
- **Platform:** Windows
- **Reserved for Surya OCR:** ~2GB (user estimate)
- **Available for Layout Detection:** ~6GB

## Requirements Gathering

### Batch 1 - Questions & Answers

**Q1: What is the primary document format you'll be processing?**
- A) Scanned PDFs (image-based)
- B) Native/Digital PDFs (text-layer present)
- C) Mixed (both scanned and digital)
- D) Images only (JPG, PNG, TIFF)

**Answer:** A) Scanned PDFs (image-based)

---

**Q2: What is the expected volume of documents to process?**
- A) Small batch (1-10 documents at a time)
- B) Medium batch (10-50 documents at a time)
- C) Large batch (50-200 documents at a time)
- D) Continuous processing (streaming/real-time)

**Answer:** Custom - The system will process images from the Knowledge Extractor system, where a single book can have 300-2000 pages, and each page is stored as a single image.

---

### Batch 2 - Questions & Answers

**Q3: What level of accuracy is required for boundary detection?**
- A) High accuracy (>95%) - manual review acceptable for corrections
- B) Very high accuracy (>98%) - minimal manual intervention
- C) Perfect accuracy (>99%) - critical documents, no errors allowed
- D) Moderate accuracy (>85%) - speed prioritized over precision

**Answer:** Aiming for 98% (very high), but flexible based on hardware constraints. User wants to see options with their hardware requirements. **Important:** Documents can be in Arabic OR English - need to clarify if one LLM can handle both languages.

---

**Q4: What is the expected output format for detected boundaries?**
- A) Bounding box coordinates (x, y, width, height)
- B) Polygon coordinates (for irregular shapes)
- C) Segmented image crops (separate images per region)
- D) All of the above

**Answer:** Bounding boxes with:
- Classification: diagram vs paragraph
- For diagrams: parent paragraph identification
- Integration: Will programmatically call extractor APIs to define paragraphs and diagrams automatically

---

### Batch 3 - Questions & Answers

**Q5: What types of diagrams need to be detected?**
- A) Simple charts (bar, line, pie)
- B) Complex diagrams (flowcharts, network diagrams, scientific figures)
- C) Tables and structured data
- D) All types including mixed content

**Answer:** D) All types including mixed content

---

**Q6: How should the system handle complex page layouts?**
- A) Single-column text only
- B) Multi-column layouts (newspapers, textbooks)
- C) Mixed layouts with floating elements
- D) All layout types

**Answer:** D) All layout types

---

### Batch 4 - Questions & Answers

**Q7: What is your preference for processing speed vs accuracy trade-off?**
- A) Accuracy first (slower, but higher quality)
- B) Balanced (reasonable speed with good accuracy)
- C) Speed first (faster, may sacrifice some accuracy)
- D) Configurable per-run

**Answer:** A) Accuracy first

---

**Q8: Should the solution integrate with your existing OCR engines (PaddleOCR, Surya, Tesseract)?**
- A) Yes, use layout detection + existing OCR
- B) No, use a single all-in-one solution
- C) Hybrid - layout detection local, OCR can be either
- D) Prefer solutions that include their own OCR

**Answer:** A) Yes - integrate with existing OCR, specifically **Surya OCR at 600 DPI only** for text extraction

---

### Batch 5 - Questions & Answers

**Q9: What is your preference for model deployment/management?**
- A) Simple single-file model (easy to manage)
- B) Hugging Face integration (access to model hub)
- C) Docker container (isolated environment)
- D) Direct Python integration (pip install)

**Answer:** Prefer simple local deployments, but open to other options if they provide better results. Research should present multiple options with trade-offs.

---

**Q10: Do you need the system to learn and improve from corrections?**
- A) No, static model is fine
- B) Yes, fine-tune on my specific documents
- C) Yes, but only store corrections for future reference
- D) Prefer out-of-the-box models with no training

**Answer:** Prefer out-of-the-box/static models, but fine-tuning capability would be a nice-to-have bonus.

---

### Batch 6 - Questions & Answers

**Q11: What is the typical quality of your scanned documents?**
- A) High quality (clean scans, good contrast)
- B) Medium quality (some noise, occasional skew)
- C) Low quality (poor scans, significant noise)
- D) Variable (mix of all quality levels)

**Answer:** A) High quality (clean scans, good contrast)

---

**Q12: Do you need real-time preview of detected boundaries before processing?**
- A) Yes, interactive preview and adjustment
- B) Yes, but just visual confirmation
- C) No, batch process without preview
- D) Optional - nice to have but not required

**Answer:** Configurable hybrid approach:
- User specifies N pages for interactive preview/adjustment
- After N pages, switch to automated batch processing without user review

---

### Batch 7 - Final Confirmation

**Q13: To summarize, should the LLM/model be specifically for layout detection only (then pass to Surya OCR), or should it also handle text reading?**
- A) Layout detection only (paragraph/diagram boundaries) - OCR by Surya
- B) Layout detection + text reading in one model
- C) Layout detection + optional OCR capability

**Answer:** A) Layout detection only + minimal reading capability to understand diagram titles (for correctly linking diagrams to parent paragraphs). Full OCR handled by Surya.

---

**Q14: What is the priority order for the research?**
- A) Focus on models that fit 6GB GPU first
- B) Focus on accuracy first, then check GPU requirements
- C) Provide tiered options (light/medium/heavy models)
- D) All options with clear trade-off analysis

**Answer:** D) All options with clear trade-off analysis

---

## Consolidated Requirements Summary

### Hardware Constraints
- **GPU:** NVIDIA RTX 4070 Laptop (8GB VRAM total)
- **System RAM:** 64GB
- **Platform:** Windows
- **VRAM Budget:** ~6GB for layout model (reserving ~2GB for Surya OCR)
- **Preference:** Simple local deployment

### Functional Requirements
1. **Document Layout Detection**
   - Detect paragraph boundaries (bounding boxes)
   - Detect diagram boundaries (bounding boxes)
   - Classify regions as paragraph vs diagram
   - Link diagrams to parent paragraphs via title reading

2. **Language Support**
   - Arabic documents (primary)
   - English documents (secondary)
   - Single model should handle both languages

3. **Integration**
   - Output bounding boxes to existing Knowledge Extractor system
   - Use Surya OCR at 600 DPI for text extraction
   - Programmatic API calls to define paragraphs/diagrams

### Processing Requirements
- **Volume:** 300-2000 pages per book, each page as separate image
- **Quality:** High quality scans (clean, good contrast)
- **Accuracy Target:** 98% (flexible based on hardware)
- **Speed:** Accuracy prioritized over speed
- **Layouts:** All types (single-column, multi-column, mixed, floating elements)
- **Diagram Types:** All (charts, flowcharts, tables, scientific figures, mixed)

### Workflow Requirements
- Configurable interactive preview for N pages (user-specified)
- Then switch to automated batch processing
- Out-of-the-box models preferred (fine-tuning as nice-to-have)

### Research Scope
- Provide all viable options with trade-off analysis
- Compare VRAM requirements, accuracy, speed
- Clarify if single model handles Arabic + English

---

## Research Findings

### Research Date: January 2026

### Sources Consulted
- GitHub repositories (Surya, PaddleOCR, DocLayout-YOLO, Marker, LayoutParser, Unstructured.io)
- Hugging Face model documentation
- ArXiv papers (DiT, DocLayout-YOLO, RT-DETR)
- PyPI package documentation
- Microsoft Research (LayoutLM, DiT, Florence-2)
- Technical blogs and benchmarks (Roboflow, MarkTechPost, E2E Networks)
- KITAB-Bench Arabic OCR benchmark (ACL 2025)

---

## Model Comparison Matrix

| Model | VRAM (Inference) | Arabic Support | Accuracy (mAP) | Speed | Fits 6GB? | Layout + Classify |
|-------|------------------|----------------|----------------|-------|-----------|-------------------|
| **DocLayout-YOLO** | ~4-6 GB | Yes (universal) | 70-79% | 85.5 FPS | YES | YES |
| **Surya Layout** | ~7 GB (default) | Yes (90+ langs) | High | Good | CONFIGURABLE | YES |
| **PaddleOCR PP-Structure** | ~3-4 GB | Yes (109 langs) | Good | Fast | YES | YES |
| **Marker** | ~2 GB/task | Yes (Surya-based) | High | 122 pg/s | YES | YES |
| **DiT-base** | ~1-2 GB | Universal | Good | Fast | YES | YES |
| **DiT-large** | ~2-4 GB | Universal | Higher | Medium | YES | YES |
| **LayoutParser** | ~4-8 GB | Depends on model | Good | Medium | BORDERLINE | YES |
| **Florence-2** | ~5-6 GB (BF16) | Yes | High | ~1s/img | YES (BF16) | YES |
| **Qwen2.5-VL-3B** | ~5.75 GB (BF16) | Yes | High | Medium | YES (BF16) | YES |

---

## Detailed Model Analysis

### Tier 1: Recommended for 6GB GPU (Native Fit)

#### 1. DocLayout-YOLO (TOP RECOMMENDATION)
- **GitHub:** https://github.com/opendatalab/DocLayout-YOLO
- **Installation:** `pip install doclayout-yolo`
- **VRAM:** ~4-6 GB for inference (YOLOv10-based, efficient)
- **Accuracy:** 70.3% (D4LA), 79.7% (DocLayNet), 78.8% (DocStructBench)
- **Speed:** 85.5 FPS (real-time capable)
- **Languages:** Universal (language-agnostic for layout detection)
- **Output:** Bounding boxes with class labels (title, text, figure, table, etc.)
- **Pros:**
  - State-of-the-art for document layout
  - Fast and accurate
  - Simple Python API
  - Handles complex layouts
  - Hugging Face integration
- **Cons:**
  - Layout detection only (needs separate OCR)
  - May need fine-tuning for Arabic-specific layouts

#### 2. Marker PDF (INTEGRATED SOLUTION)
- **GitHub:** https://github.com/datalab-to/marker
- **Installation:** `pip install marker-pdf[full]`
- **VRAM:** ~2 GB per task
- **Speed:** 122 pages/second on H100
- **Languages:** 90+ including Arabic (uses Surya internally)
- **Output:** Structured markdown with bounding box JSON
- **Pros:**
  - Already uses Surya OCR internally
  - Multi-column layout handling
  - Table and equation support
  - Debug mode saves layout images with bounding boxes
  - Preprocesses (deskew, noise removal)
- **Cons:**
  - Full pipeline (may want layout-only mode)
  - Outputs markdown, not raw bounding boxes

#### 3. PaddleOCR PP-StructureV3 (MOST EFFICIENT)
- **GitHub:** https://github.com/PaddlePaddle/PaddleOCR
- **Installation:** `pip install paddleocr`
- **VRAM:** ~3-4 GB (configurable)
- **Languages:** 109 languages including Arabic
- **Speed:** Varies by model variant (mobile/server)
- **Accuracy:** Good for standard documents
- **Pros:**
  - Most resource-efficient
  - Server and mobile variants
  - CPU fallback available
  - Extensive Arabic support
- **Cons:**
  - Requires Flash Attention 2 for Arabic (reduces VRAM from 40GB to 3.3GB!)
  - PaddlePaddle framework (not PyTorch)

#### 4. DiT (Document Image Transformer)
- **Hugging Face:** https://huggingface.co/microsoft/dit-large
- **VRAM:**
  - DiT-base (~86M params): ~1-2 GB
  - DiT-large (~304M params): ~2-4 GB
- **Languages:** Universal (self-supervised pre-training)
- **Tasks:** Layout analysis, table detection, document classification
- **Pros:**
  - Very lightweight
  - Microsoft-backed
  - Pre-trained on 42M document images
  - Multiple sizes available
- **Cons:**
  - May need fine-tuning for specific use cases
  - Lower out-of-box accuracy than specialized models

### Tier 2: Configurable for 6GB GPU

#### 5. Surya Layout Detection
- **GitHub:** https://github.com/datalab-to/surya
- **Installation:** `pip install surya-ocr`
- **VRAM (default):** ~7 GB (batch size 32)
- **VRAM (configurable):** ~220 MB per batch item
- **Languages:** 90+ including Arabic
- **Accuracy:** High (used by Marker)
- **Configuration for 6GB:**
  ```bash
  export LAYOUT_BATCH_SIZE=24  # ~5.3 GB
  export DETECTOR_BATCH_SIZE=20  # ~5.6 GB
  ```
- **Pros:**
  - Already in your system
  - Excellent multilingual support
  - Reading order detection
  - Table recognition
- **Cons:**
  - Default settings exceed 6GB
  - Need to tune batch sizes

### Tier 3: Vision-Language Models (Advanced)

#### 6. Florence-2 (Microsoft)
- **Hugging Face:** https://huggingface.co/microsoft/Florence-2-large
- **VRAM:** ~5-6 GB (BF16/FP16)
- **Languages:** Multilingual including Arabic
- **Tasks:** OCR, layout, VQA, captioning, detection
- **Pros:**
  - Multi-task single model
  - Can understand diagram titles (your requirement!)
  - Good for linking diagrams to paragraphs
- **Cons:**
  - ~1 second per image inference
  - May need BF16 precision to fit

#### 7. Qwen2.5-VL-3B
- **VRAM:** 11.5 GB (FP32) or 5.75 GB (BF16)
- **Languages:** Excellent multilingual including Arabic
- **Pros:**
  - State-of-the-art VLM capabilities
  - Can understand document context
  - Text reading for diagram titles
- **Cons:**
  - Requires BF16 precision
  - Slower than specialized layout models

### Tier 4: Requires More VRAM (Reference Only)

| Model | VRAM Required | Notes |
|-------|---------------|-------|
| Surya (defaults) | 9-10 GB | Reduce batch size for 6GB |
| Donut | 16+ GB | OCR-free document understanding |
| LayoutLMv3 | 8+ GB | For fine-tuning; inference may fit |
| Florence-2 (fine-tuning) | 20 GB | Inference only on 6GB |

---

## Arabic Language Specific Findings

### KITAB-Bench (ACL 2025)
The most comprehensive Arabic OCR benchmark evaluates layout detection with:
- 8,809 samples across 9 domains
- mAP@0.5 and mAP@0.5:0.95 metrics
- Tests headers, paragraphs, and complex layouts

**Key Finding:** For Arabic documents:
- GPT-4o and Gemini significantly outperform traditional OCR
- Surya performs well for standard text but struggles with tables/charts
- RT-DETR Layout achieves competitive performance for layout detection
- **PaddleOCR with Flash Attention 2 is critical** for Arabic (reduces VRAM from 40GB to 3.3GB)

### Arabic-Specific Challenges
- Right-to-left text direction
- Connected script requiring special handling
- Diacritical marks affecting line boundaries
- Multi-script documents (Arabic + English mixed)

### Recommended Approach for Arabic
1. Use **DocLayout-YOLO** for layout detection (language-agnostic)
2. Use **Surya OCR at 600 DPI** for text extraction (90+ language support)
3. For diagram title reading, use **Florence-2** or pass to Claude API

---

## Recommended Solutions

### Primary Recommendation: DocLayout-YOLO + Surya Integration

**Why:**
- DocLayout-YOLO fits comfortably in 6GB VRAM
- Already using Surya for OCR (no new dependencies)
- State-of-the-art layout detection accuracy
- Real-time processing speed
- Language-agnostic (works for Arabic + English)

**Architecture:**
```
Page Image
    ↓
DocLayout-YOLO (layout detection, ~4 GB VRAM)
    ↓
Bounding Boxes + Classes (paragraph, title, figure, table, etc.)
    ↓
For each region:
    - If paragraph/title → Surya OCR at 600 DPI
    - If diagram → Store as diagram, optionally use Florence-2 for title
    ↓
Output to Knowledge Extractor API
```

### Alternative 1: Marker (All-in-One)
Use if you want a single integrated solution. Marker already uses Surya internally and provides layout + OCR + structured output.

### Alternative 2: DiT + Surya
Use DiT-base for minimal VRAM usage (~1-2 GB) if you need to run other processes simultaneously.

### Alternative 3: Florence-2 (For Diagram Understanding)
Add Florence-2 specifically for understanding diagram titles and linking to parent paragraphs. Can run alongside DocLayout-YOLO.

---

## Implementation Plan

### Phase 1: Setup DocLayout-YOLO
```python
# Installation
pip install doclayout-yolo

# Basic usage
from doclayout_yolo import DocLayoutYOLO

model = DocLayoutYOLO.from_pretrained()
results = model.predict("page_image.png")

# Results contain bounding boxes with classes:
# - title, text, figure, table, list, etc.
```

### Phase 2: Integration with Knowledge Extractor
1. Add new API endpoint: `POST /api/auto-boundaries/{book_id}/detect`
2. Process page images from database
3. Return bounding boxes with classifications
4. Store results for review

### Phase 3: Workflow Integration
1. User opens Auto-Boundaries page
2. Selects page range for processing
3. Model detects layouts and classifies regions
4. Interactive review for N pages
5. Automated processing for remaining pages
6. Results stored as paragraph_images and diagram_images

### Phase 4: Optional Florence-2 for Diagrams
```python
# For diagram title extraction
from transformers import AutoProcessor, AutoModelForCausalLM

processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base")
model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base")

# Use for linking diagrams to parent paragraphs
```

---

## Configuration for 6GB GPU

### DocLayout-YOLO
```python
# Runs efficiently on 6GB by default
# For memory-constrained scenarios:
model.predict(image, batch_size=1)  # Single image at a time
```

### Surya (Existing)
```bash
# Set environment variables before running
export LAYOUT_BATCH_SIZE=20    # ~4.4 GB
export DETECTOR_BATCH_SIZE=16  # ~4.5 GB
export RECOGNITION_BATCH_SIZE=256  # ~10 GB → reduce to 64 for ~2.5 GB
```

### Florence-2 (Optional)
```python
# Use bfloat16 to fit in 6GB
model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base",
    torch_dtype=torch.bfloat16
)
```

---

## Summary

**Can you run a local LLM for Arabic document layout analysis on 6GB GPU?**

**YES** - Multiple viable options exist:

| Priority | Model | Fits 6GB? | Arabic | Accuracy | Recommendation |
|----------|-------|-----------|--------|----------|----------------|
| 1 | DocLayout-YOLO | YES | YES | 79.7% | PRIMARY CHOICE |
| 2 | Marker | YES | YES | High | INTEGRATED |
| 3 | DiT-base | YES | YES | Good | LIGHTWEIGHT |
| 4 | Florence-2 | YES (BF16) | YES | High | FOR DIAGRAMS |
| 5 | Surya (tuned) | YES | YES | High | ALREADY HAVE |

**Next Steps:**
1. Confirm recommendation (DocLayout-YOLO + existing Surya)
2. Create integration plan for Knowledge Extractor
3. Implement API endpoints
4. Build UI for boundary review

---

## Concurrent VRAM Analysis: DocLayout-YOLO + Surya OCR

### Your Hardware Profile
| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA RTX 4070 Laptop |
| VRAM | 8GB GDDR6 |
| CUDA Cores | 4,608 |
| Memory Bus | 128-bit @ 16 Gbps |
| System RAM | 64GB |
| Platform | Windows |

### Surya OCR VRAM Usage (Research Findings)

Based on research from GitHub issues and documentation:

| Surya Component | Per-Batch VRAM | Default Batch | Default Total |
|-----------------|----------------|---------------|---------------|
| Text Detector | 280 MB/item | 32 | ~9 GB |
| Text Recognition | 50 MB/item | 256 | ~12.8 GB |
| Layout Detection | 220 MB/item | 32 | ~7 GB |

**Real-World Observation:** Users report Surya using ~6.2 GB VRAM with default settings on RTX 4090 (GitHub Issue #183).

**On RTX 3050 8GB:** Confirmed working with "decent speed" when compiled.

### DocLayout-YOLO VRAM Usage (Estimated)

DocLayout-YOLO is based on YOLOv10. Typical YOLO inference memory:

| Model Variant | Approximate VRAM (Inference) |
|---------------|------------------------------|
| YOLOv10n (nano) | ~0.5-1 GB |
| YOLOv10s (small) | ~1-1.5 GB |
| YOLOv10m (medium) | ~1.5-2.5 GB |
| YOLOv10l (large) | ~2.5-4 GB |
| DocLayout-YOLO | ~2-4 GB (estimated) |

*Note: Exact DocLayout-YOLO inference VRAM not published; estimates based on YOLOv10 architecture.*

---

### Concurrent Usage Strategies

#### Strategy 1: Sequential Processing (RECOMMENDED - SAFEST)

Run models one after the other, not simultaneously.

```
Step 1: Load DocLayout-YOLO → Detect layouts → Unload
Step 2: Load Surya OCR → Extract text from regions → Unload
```

**VRAM Usage:** Maximum of single largest model (~4-6 GB)
**Pros:** No VRAM conflicts, maximum stability
**Cons:** Slight overhead from model loading/unloading

**Implementation:**
```python
import torch
import gc

def detect_layout(image):
    model = load_doclayout_yolo()
    results = model.predict(image)
    del model
    torch.cuda.empty_cache()
    gc.collect()
    return results

def extract_text(image_region):
    # Surya OCR loads here
    text = surya_ocr(image_region)
    torch.cuda.empty_cache()
    return text
```

#### Strategy 2: Concurrent with Reduced Batch Sizes (POSSIBLE)

Run both models with aggressive memory tuning.

**Configuration for 8GB Total:**

```bash
# Surya OCR - Reduced batch sizes
export DETECTOR_BATCH_SIZE=4      # ~1.1 GB (vs 9 GB default)
export RECOGNITION_BATCH_SIZE=16  # ~0.8 GB (vs 12.8 GB default)
export LAYOUT_BATCH_SIZE=4        # ~0.9 GB (vs 7 GB default)
```

**Estimated VRAM Split:**
| Model | Configured VRAM |
|-------|-----------------|
| DocLayout-YOLO | ~2-3 GB |
| Surya (tuned) | ~2-3 GB |
| CUDA overhead | ~1 GB |
| **Total** | **~5-7 GB** |

**Pros:** Faster overall processing
**Cons:** Reduced throughput, potential instability

#### Strategy 3: Hybrid - Layout on GPU, OCR Uses CPU Fallback

Use GPU for fast layout detection, fall back to CPU for OCR.

```bash
# Force Surya to CPU
export TORCH_DEVICE=cpu
```

**VRAM Usage:** ~2-4 GB (DocLayout-YOLO only)
**System RAM:** Surya uses your 64GB RAM
**Pros:** Full GPU power for layout, stable
**Cons:** OCR slower on CPU (~10x), but you have 64GB RAM

---

### Recommended Configuration for RTX 4070 Laptop (8GB)

```bash
# File: set_vram_config.bat (Windows)
# Run before starting the Knowledge Extractor

# DocLayout-YOLO settings
set DOCLAYOUT_BATCH_SIZE=1

# Surya OCR settings for 8GB GPU
set DETECTOR_BATCH_SIZE=8
set RECOGNITION_BATCH_SIZE=32
set LAYOUT_BATCH_SIZE=8
set TORCH_DEVICE=cuda

# PyTorch memory management
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

**Estimated VRAM with these settings:**
| Component | VRAM |
|-----------|------|
| DocLayout-YOLO (batch 1) | ~2 GB |
| Surya Detector (batch 8) | ~2.2 GB |
| Surya Recognition (batch 32) | ~1.6 GB |
| CUDA/PyTorch overhead | ~1 GB |
| **Total (if sequential)** | **~3-4 GB** |
| **Total (if concurrent)** | **~6-7 GB** |

---

### Performance Expectations

#### Sequential Processing (Recommended)
| Operation | Time per Page (Est.) |
|-----------|---------------------|
| Load DocLayout-YOLO | ~2-3 sec (once) |
| Layout detection | ~0.1-0.2 sec |
| Unload + Load Surya | ~3-4 sec |
| OCR per region | ~1-2 sec |
| **Total per page** | **~5-8 sec** |

#### For a 500-page book:
- Layout detection: ~100 seconds (~1.5 min)
- OCR (with model swapping): ~40-50 minutes
- **Total: ~45-55 minutes**

#### With Concurrent Processing (If Stable):
- **Total: ~25-35 minutes** (estimated 30-40% faster)

---

### Memory Overflow Protection

Your 64GB system RAM provides a safety net. Windows/CUDA can use "shared GPU memory" which borrows from system RAM when VRAM is full.

**However, shared memory is ~10x slower than dedicated VRAM.**

To prevent this:
```python
# In your Python code
import torch
torch.cuda.set_per_process_memory_fraction(0.90)  # Use max 90% of VRAM
```

---

### Verification Commands

Run these to monitor VRAM usage during testing:

```bash
# Windows PowerShell - Real-time monitoring
nvidia-smi -l 1

# Or one-time check
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Python VRAM check:**
```python
import torch
print(f"VRAM Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
print(f"VRAM Cached: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
```

---

### Final Answer: Can Both Models Run Together?

| Scenario | Fits in 8GB? | Recommendation |
|----------|--------------|----------------|
| Sequential (one at a time) | **YES** | RECOMMENDED |
| Concurrent (both loaded, tuned batches) | **BORDERLINE** | Test carefully |
| Concurrent (default settings) | **NO** | Will overflow to shared memory |

**Bottom Line:**
- **YES**, DocLayout-YOLO and Surya OCR can coexist on your 8GB RTX 4070
- **Best approach:** Sequential processing with model swapping
- **Alternative:** Concurrent with reduced batch sizes (test for stability)
- Your **64GB system RAM** provides an excellent safety net if VRAM overflows
