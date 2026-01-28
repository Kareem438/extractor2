"""
CHUNK-031: FastAPI Application Setup

Main FastAPI application with middleware, static files, and router configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
import os
from src.config import settings
from src.utils.logging_config import setup_logging, logger

# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Knowledge Extraction System",
    version="1.0.0",
    description="Extract and verify knowledge from documents with AI-powered OCR and semantic chunking",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7777", "http://127.0.0.1:7777"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create frontend directories if they don't exist
frontend_static_dir = os.path.join(os.path.dirname(__file__), "frontend", "static")
os.makedirs(frontend_static_dir, exist_ok=True)

# Mount static files if directory exists
if os.path.exists(frontend_static_dir):
    app.mount("/static", StaticFiles(directory=frontend_static_dir), name="static")
    logger.info(f"Mounted static files from {frontend_static_dir}")
else:
    logger.warning(f"Static directory not found: {frontend_static_dir}")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Knowledge Extraction System API")
    logger.info(f"API Documentation: http://localhost:7777/docs")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    
    # Auto-load Surya OCR and DocLayout-YOLO on startup
    logger.info("=" * 80)
    logger.info("AUTO-LOADING MODELS ON STARTUP")
    logger.info("=" * 80)
    
    # Load Surya OCR
    try:
        from src.services.ocr_sequential import load_surya_models
        logger.info("[1/2] Loading Surya OCR models...")
        result = load_surya_models()
        if result['success']:
            logger.info(f"✅ Surya OCR: {result['message']}")
        else:
            logger.warning(f"⚠️ Surya OCR: {result['message']}")
    except Exception as e:
        logger.error(f"❌ Failed to load Surya OCR: {e}")
    
    # Load DocLayout-YOLO
    try:
        from src.services.layout_detection_service import layout_detection_service, check_model_exists
        logger.info("[2/2] Loading DocLayout-YOLO model...")
        
        # Check if model file exists
        model_exists, model_msg = check_model_exists()
        if model_exists:
            success = layout_detection_service.load_model()
            if success:
                logger.info(f"✅ DocLayout-YOLO: Model loaded successfully")
            else:
                logger.warning(f"⚠️ DocLayout-YOLO: Failed to load model")
        else:
            logger.warning(f"⚠️ DocLayout-YOLO: {model_msg}")
    except Exception as e:
        logger.error(f"❌ Failed to load DocLayout-YOLO: {e}")
    
    logger.info("=" * 80)
    logger.info("STARTUP MODEL LOADING COMPLETE")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Knowledge Extraction System API")


@app.get("/")
async def root():
    """Root endpoint - redirect to library page."""
    return RedirectResponse(url="/library")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Knowledge Extraction System",
        "version": "1.0.0"
    }


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Serve the upload page."""
    upload_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "upload.html")
    try:
        with open(upload_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Upload page not found</h1>", status_code=404)


@app.get("/library", response_class=HTMLResponse)
async def library_page():
    """Serve the book library page."""
    library_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "library.html")
    try:
        with open(library_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Library page not found</h1>", status_code=404)


@app.get("/verification", response_class=HTMLResponse)
async def verification_page():
    """Serve the verification interface page."""
    verification_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "verification.html")
    try:
        with open(verification_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Verification page not found</h1>", status_code=404)


@app.get("/book-settings", response_class=HTMLResponse)
async def book_settings_page():
    """Serve the book settings page."""
    settings_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "book-settings.html")
    try:
        with open(settings_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Book settings page not found</h1>", status_code=404)


@app.get("/verify-pages", response_class=HTMLResponse)
async def verify_pages_page():
    """Serve the verify pages page."""
    verify_pages_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "verify-pages.html")
    try:
        with open(verify_pages_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Verify pages page not found</h1>", status_code=404)


@app.get("/edit-paragraphs", response_class=HTMLResponse)
async def edit_paragraphs_page():
    """Serve the edit paragraphs page."""
    edit_paragraphs_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "edit-paragraphs.html")
    try:
        with open(edit_paragraphs_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Edit paragraphs page not found</h1>", status_code=404)


@app.get("/edit-diagrams", response_class=HTMLResponse)
async def edit_diagrams_page():
    """Serve the edit diagrams page."""
    edit_diagrams_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "edit-diagrams.html")
    try:
        with open(edit_diagrams_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Edit diagrams page not found</h1>", status_code=404)


@app.get("/review-raw", response_class=HTMLResponse)
async def review_raw_page():
    """Serve the review raw data page."""
    review_raw_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "review-raw.html")
    try:
        with open(review_raw_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Review raw page not found</h1>", status_code=404)


@app.get("/pipeline-config", response_class=HTMLResponse)
async def pipeline_config_page():
    """Serve the pipeline configuration page."""
    pipeline_config_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "pipeline-config.html")
    try:
        with open(pipeline_config_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Pipeline configuration page not found</h1>", status_code=404)


@app.get("/pipeline-dashboard", response_class=HTMLResponse)
async def pipeline_dashboard_page():
    """Serve the pipeline dashboard page."""
    pipeline_dashboard_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "pipeline-dashboard.html")
    try:
        with open(pipeline_dashboard_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Pipeline dashboard page not found</h1>", status_code=404)


@app.get("/auto-slicer", response_class=HTMLResponse)
async def auto_slicer_page():
    """Serve the Auto-slicer page."""
    auto_slicer_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "auto-slicer.html")
    try:
        with open(auto_slicer_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Auto-slicer page not found</h1>", status_code=404)


@app.get("/layout-review", response_class=HTMLResponse)
async def layout_review_page():
    """Serve the Layout Review page for reviewing YOLO-detected regions."""
    layout_review_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "layout-review.html")
    try:
        with open(layout_review_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Layout review page not found</h1>", status_code=404)


@app.get("/extract-knowledge", response_class=HTMLResponse)
async def extract_knowledge_page():
    """Serve the Extract Knowledge Units page."""
    extract_knowledge_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "extract-knowledge.html")
    try:
        with open(extract_knowledge_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Extract knowledge page not found</h1>", status_code=404)


@app.get("/extraction-dashboard", response_class=HTMLResponse)
async def extraction_dashboard_page():
    """Serve the Extraction Dashboard page (Phase 3D)."""
    dashboard_html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "extraction-dashboard.html")
    try:
        with open(dashboard_html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Extraction dashboard page not found</h1>", status_code=404)


@app.get("/l1-title-attributes", response_class=HTMLResponse)
async def l1_title_attributes_page():
    """Serve the L1 Title Attribute Editor page."""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "l1-title-attributes.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>L1 Title Attributes page not found</h1>", status_code=404)


@app.get("/l2-title-attributes", response_class=HTMLResponse)
async def l2_title_attributes_page():
    """Serve the L2 Title Attribute Editor page."""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "l2-title-attributes.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>L2 Title Attributes page not found</h1>", status_code=404)


@app.get("/cross-book-audit", response_class=HTMLResponse)
async def cross_book_audit_page():
    """Serve the Cross-Book Audit Log page."""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "templates", "cross-book-audit.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Cross-Book Audit Log page not found</h1>", status_code=404)


# Include API routers (will be added in subsequent chunks)
# Note: Routers will be included as they are implemented
try:
    from src.api.routes import upload, processing, books, knowledge_units, images, pages, ocr, search, verify_pages, raw_data_check, image_clips, review_raw, pipeline, worker, auto_slicer, layout_detection, extraction, gpu, title_hierarchy, multi_pdf, cross_book, template_reference

    app.include_router(upload.router, prefix="/api", tags=["Upload"])
    app.include_router(processing.router, prefix="/api", tags=["Processing"])
    app.include_router(books.router, prefix="/api", tags=["Books"])
    app.include_router(knowledge_units.router, prefix="/api", tags=["Knowledge Units"])
    app.include_router(images.router, prefix="/api", tags=["Images"])
    app.include_router(pages.router, prefix="/api", tags=["Pages"])
    app.include_router(ocr.router, prefix="/api", tags=["Sequential OCR"])
    app.include_router(search.router, tags=["Semantic Search"])
    app.include_router(verify_pages.router, prefix="/api", tags=["Verify Pages"])
    app.include_router(raw_data_check.router, prefix="/api", tags=["Raw Data Check"])
    app.include_router(image_clips.router, tags=["Image Clips"])
    app.include_router(review_raw.router, tags=["Review Raw"])
    app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
    app.include_router(worker.router, prefix="/api", tags=["Worker"])
    app.include_router(auto_slicer.router, prefix="/api", tags=["Auto-Slicer"])
    app.include_router(layout_detection.router, tags=["Layout Detection"])
    app.include_router(extraction.router, prefix="/api", tags=["Extraction"])
    app.include_router(gpu.router, prefix="/api", tags=["GPU Management"])
    app.include_router(title_hierarchy.router, prefix="/api", tags=["Title Hierarchy"])
    app.include_router(multi_pdf.router, prefix="/api", tags=["Multi-PDF Upload"])
    app.include_router(cross_book.router, prefix="/api", tags=["Cross-Book Access"])
    app.include_router(template_reference.router, prefix="/api", tags=["Template Reference"])

    logger.info("API routers loaded successfully")
except ImportError as e:
    logger.warning(f"Some API routers not yet implemented: {e}")


# Include WebSocket handler (will be added in subsequent chunks)
try:
    from src.api import websocket
    app.include_router(websocket.router, tags=["WebSocket"])
    logger.info("WebSocket handler loaded successfully")
except ImportError:
    logger.warning("WebSocket handler not yet implemented")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server with uvicorn...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=7777,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
