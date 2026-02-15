"""
CHUNK-009: Dynamic Table Creation

Creates book-specific tables dynamically for each uploaded book.
Each book gets 7 processed data tables with a unique table prefix.
"""

from sqlalchemy import text
from src.database.connection import engine
from src.utils.sanitization import generate_table_prefix


def create_raw_pages_table(table_prefix: str):
    """Create raw_pages table for original page images extracted from PDF"""
    table_name = f"raw_{table_prefix}_pages"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Page Identification
        page_number INTEGER NOT NULL UNIQUE,

        -- Original Page Image (INPUT for OCR)
        original_image_data BYTEA NOT NULL,
        original_format VARCHAR(20) NOT NULL,
        original_width INTEGER NOT NULL,
        original_height INTEGER NOT NULL,
        original_size_bytes INTEGER NOT NULL,

        -- Hierarchy (Document Structure)
        chapter VARCHAR(255),
        topic VARCHAR(255),
        sub_topic VARCHAR(255),

        -- Skip Pages Feature (Requirement 4)
        is_skipped BOOLEAN DEFAULT FALSE,
        is_ready_for_extraction BOOLEAN DEFAULT FALSE,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_pages_number ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_pages_skipped ON {table_name}(is_skipped)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_pages_ready ON {table_name}(is_ready_for_extraction)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_raw_knowledge_units_table(table_prefix: str):
    """Create raw_knowledge_units table for unsplit OCR results (full page text per engine)"""
    table_name = f"raw_{table_prefix}_knowledge_units"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Pages
        raw_page_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,

        -- OCR Metadata
        ocr_engine VARCHAR(50) NOT NULL,
        ocr_run_timestamp TIMESTAMP DEFAULT NOW(),

        -- Full Page Text (UNSPLIT)
        full_page_text TEXT NOT NULL,
        text_length INTEGER NOT NULL,

        -- OCR Quality Metrics
        confidence_score NUMERIC(5,2) NOT NULL,
        language VARCHAR(50) NOT NULL,

        -- Extracted Images on this Page
        extracted_image_ids TEXT[],

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        -- Foreign Key Constraint
        FOREIGN KEY (raw_page_id) REFERENCES raw_{table_prefix}_pages(id) ON DELETE CASCADE
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_ku_page ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_ku_engine ON {table_name}(ocr_engine)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_ku_raw_page ON {table_name}(raw_page_id)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_raw_paragraph_images_table(table_prefix: str):
    """Create raw_paragraph_images table for user-selected paragraph image clips"""
    table_name = f"raw_{table_prefix}_paragraph_images"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Pages
        raw_page_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,

        -- Selection Coordinates (on the original page image)
        selection_x INTEGER NOT NULL,
        selection_y INTEGER NOT NULL,
        selection_width INTEGER NOT NULL,
        selection_height INTEGER NOT NULL,

        -- Cropped Image Data
        image_data BYTEA NOT NULL,
        image_format VARCHAR(20) NOT NULL DEFAULT 'png',

        -- Image Dimensions (of the cropped image itself)
        image_width INTEGER NOT NULL,
        image_height INTEGER NOT NULL,
        image_size_bytes INTEGER NOT NULL,

        -- User Notes/Description
        user_notes TEXT,
        description TEXT,

        -- Workflow Status
        approval_status VARCHAR(50) DEFAULT 'pending',

        -- Category/Tags
        category VARCHAR(100),
        tags TEXT[],

        -- User/Session Info
        created_by VARCHAR(100),

        -- Display Control
        display_order INTEGER NOT NULL DEFAULT 0,
        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,

        -- Selected Level (for hierarchy positioning)
        selected_level_number INTEGER,
        selected_level_text VARCHAR(500),

        -- OCR Text (copy of text also stored in linked KU)
        extracted_text TEXT,
        ocr_confidence NUMERIC(5,2),

        -- Level Titles (5 levels for hierarchy positioning)
        level_1_title VARCHAR(500),
        level_2_title VARCHAR(500),
        level_3_title VARCHAR(500),
        level_4_title VARCHAR(500),
        level_5_title VARCHAR(500),

        -- Linked Knowledge Unit
        linked_knowledge_unit_id INTEGER,

        -- Title Hierarchy Foreign Keys (Requirement 4)
        l1_title_id INTEGER,
        l2_title_id INTEGER,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        -- Foreign Key Constraint
        FOREIGN KEY (raw_page_id) REFERENCES raw_{table_prefix}_pages(id) ON DELETE CASCADE
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_page ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_raw_page ON {table_name}(raw_page_id)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_status ON {table_name}(approval_status)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_category ON {table_name}(category)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_order ON {table_name}(display_order)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_img_enabled ON {table_name}(is_enabled)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_l1_title ON {table_name}(l1_title_id)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_para_l2_title ON {table_name}(l2_title_id)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_raw_diagram_images_table(table_prefix: str):
    """Create raw_diagram_images table for user-selected diagram image clips"""
    table_name = f"raw_{table_prefix}_diagram_images"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Pages
        raw_page_id INTEGER NOT NULL,
        page_number INTEGER NOT NULL,

        -- Selection Coordinates (on the original page image)
        selection_x INTEGER NOT NULL,
        selection_y INTEGER NOT NULL,
        selection_width INTEGER NOT NULL,
        selection_height INTEGER NOT NULL,

        -- Cropped Image Data
        image_data BYTEA NOT NULL,
        image_format VARCHAR(20) NOT NULL DEFAULT 'png',

        -- Image Dimensions (of the cropped image itself)
        image_width INTEGER NOT NULL,
        image_height INTEGER NOT NULL,
        image_size_bytes INTEGER NOT NULL,

        -- User Notes/Description
        user_notes TEXT,
        description TEXT,

        -- AI Analysis Fields (NEW)
        extracted_text TEXT,
        diagram_type VARCHAR(100),
        prompt_type VARCHAR(20),
        structured_json JSONB,
        ai_model VARCHAR(100),
        ai_confidence NUMERIC(5,2),
        analyzed_at TIMESTAMP,

        -- Link to Knowledge Unit (user-controlled)
        linked_knowledge_unit_id INTEGER,

        -- Level Titles (5 levels for hierarchy positioning)
        level_1_title VARCHAR(500),
        level_2_title VARCHAR(500),
        level_3_title VARCHAR(500),
        level_4_title VARCHAR(500),
        level_5_title VARCHAR(500),

        -- Workflow Status
        approval_status VARCHAR(50) DEFAULT 'pending',

        -- Category/Tags
        category VARCHAR(100),
        tags TEXT[],

        -- Level (like paragraphs)
        level VARCHAR(50),

        -- User/Session Info
        created_by VARCHAR(100),

        -- Display Control
        display_order INTEGER NOT NULL DEFAULT 0,
        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,

        -- Selected Level (for hierarchy positioning)
        selected_level_number INTEGER,
        selected_level_text VARCHAR(500),

        -- Title Hierarchy Foreign Keys (Requirement 4)
        l1_title_id INTEGER,
        l2_title_id INTEGER,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        -- Foreign Key Constraint
        FOREIGN KEY (raw_page_id) REFERENCES raw_{table_prefix}_pages(id) ON DELETE CASCADE
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_page ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_raw_page ON {table_name}(raw_page_id)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_status ON {table_name}(approval_status)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_category ON {table_name}(category)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_order ON {table_name}(display_order)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_img_enabled ON {table_name}(is_enabled)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_l1_title ON {table_name}(l1_title_id)",
            f"CREATE INDEX IF NOT EXISTS idx_raw_{table_prefix}_diag_l2_title ON {table_name}(l2_title_id)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_knowledge_units_table(table_prefix: str):
    """Create knowledge_units table for semantic text chunks with 80 attributes"""
    table_name = f"{table_prefix}_knowledge_units"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        unit_id SERIAL PRIMARY KEY,

        -- Foreign Key to Raw Knowledge Units (parent OCR extraction)
        raw_knowledge_unit_id INTEGER,

        -- Primary text (best OCR result after evaluation)
        text_content TEXT NOT NULL,

        -- OCR metadata
        ocr_method VARCHAR(20),
        confidence_score DECIMAL(5,2),

        -- Page information
        page_number INTEGER NOT NULL,
        position_x INTEGER,
        position_y INTEGER,

        -- Language
        language VARCHAR(20),

        -- Hierarchy
        chapter VARCHAR(255),
        topic VARCHAR(255),
        sub_topic VARCHAR(255),

        -- Verification
        verified BOOLEAN DEFAULT FALSE,
        notes TEXT,

        -- System-reserved attributes (1-8)
        attr1_value TEXT,  -- related_image
        attr2_value TEXT,  -- easyocr_text (FULL TEXT)
        attr3_value TEXT,  -- surya_ocr_text (FULL TEXT)
        attr4_value TEXT,  -- tesseract_text (FULL TEXT)
        attr5_value TEXT,  -- easyocr_confidence
        attr6_value TEXT,  -- surya_ocr_confidence
        attr7_value TEXT,  -- tesseract_confidence
        attr8_value TEXT DEFAULT 'enabled',  -- record_status ('enabled' or 'disabled')

        -- User-defined attributes (9-80)
        attr9_value TEXT,
        attr10_value TEXT,
        attr11_value TEXT,
        attr12_value TEXT,
        attr13_value TEXT,
        attr14_value TEXT,
        attr15_value TEXT,
        attr16_value TEXT,
        attr17_value TEXT,
        attr18_value TEXT,
        attr19_value TEXT,
        attr20_value TEXT,
        attr21_value TEXT,
        attr22_value TEXT,
        attr23_value TEXT,
        attr24_value TEXT,
        attr25_value TEXT,
        attr26_value TEXT,
        attr27_value TEXT,
        attr28_value TEXT,
        attr29_value TEXT,
        attr30_value TEXT,
        attr31_value TEXT,
        attr32_value TEXT,
        attr33_value TEXT,
        attr34_value TEXT,
        attr35_value TEXT,
        attr36_value TEXT,
        attr37_value TEXT,
        attr38_value TEXT,
        attr39_value TEXT,
        attr40_value TEXT,
        attr41_value TEXT,
        attr42_value TEXT,
        attr43_value TEXT,
        attr44_value TEXT,
        attr45_value TEXT,
        attr46_value TEXT,
        attr47_value TEXT,
        attr48_value TEXT,
        attr49_value TEXT,
        attr50_value TEXT,
        attr51_value TEXT,
        attr52_value TEXT,
        attr53_value TEXT,
        attr54_value TEXT,
        attr55_value TEXT,
        attr56_value TEXT,
        attr57_value TEXT,
        attr58_value TEXT,
        attr59_value TEXT,
        attr60_value TEXT,
        attr61_value TEXT,
        attr62_value TEXT,
        attr63_value TEXT,
        attr64_value TEXT,
        attr65_value TEXT,
        attr66_value TEXT,
        attr67_value TEXT,
        attr68_value TEXT,
        attr69_value TEXT,
        attr70_value TEXT,
        attr71_value TEXT,
        attr72_value TEXT,
        attr73_value TEXT,
        attr74_value TEXT,
        attr75_value TEXT,
        attr76_value TEXT,
        attr77_value TEXT,
        attr78_value TEXT,
        attr79_value TEXT,
        attr80_value TEXT,

        -- Embeddings
        embedding_vector VECTOR(384),

        -- Record merging/splitting tracking
        merged_into_record_id INTEGER,
        original_record_ids TEXT[],

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_pages_table(table_prefix: str):
    """Create pages table for page-level information with marking rectangles"""
    table_name = f"{table_prefix}_pages"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        page_id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL UNIQUE,

        -- Foreign Key to Raw Pages (for original image data)
        raw_page_id INTEGER,

        -- Marker rectangles only (no image data stored here)
        marked_rectangles JSONB,
        marker_generated BOOLEAN DEFAULT FALSE,
        processed BOOLEAN DEFAULT FALSE,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_images_table(table_prefix: str):
    """Create images table for extracted images with AI analysis and SVG generation"""
    table_name = f"{table_prefix}_images"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        image_id SERIAL PRIMARY KEY,

        -- Image identification
        image_identifier VARCHAR(50) UNIQUE NOT NULL,
        page_number INTEGER NOT NULL,

        -- Original image
        image_path VARCHAR(500),
        image_data BYTEA NOT NULL,

        -- Image metadata
        image_type VARCHAR(50),
        dimensions VARCHAR(20),
        file_size INTEGER,

        -- AI Analysis Results (Claude Sonnet 4.5)
        ai_description TEXT,
        structured_json JSONB,
        svg_code TEXT,

        -- Processing metadata
        confidence_score DECIMAL(5,2),
        analyzed_at TIMESTAMP DEFAULT NOW(),
        analyzed_during_ocr VARCHAR(20),

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_processing_state_table(table_prefix: str):
    """Create processing_state table (single-row) with OCR completion tracking"""
    table_name = f"{table_prefix}_processing_state"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY DEFAULT 1,

        -- Progress tracking
        total_pages INTEGER NOT NULL,
        current_page INTEGER DEFAULT 0,

        -- Page scan progress (extraction to raw_pages)
        pages_scanned INTEGER DEFAULT 0,

        -- OCR completion flags (3 engines)
        easyocr_complete BOOLEAN DEFAULT false,
        surya_ocr_complete BOOLEAN DEFAULT false,
        tesseract_complete BOOLEAN DEFAULT false,

        -- OCR page counts (number of pages processed by each engine)
        easyocr_pages_processed INTEGER DEFAULT 0,
        surya_pages_processed INTEGER DEFAULT 0,
        tesseract_pages_processed INTEGER DEFAULT 0,

        -- Verification/Splitting progress
        pages_split_verified INTEGER DEFAULT 0,

        -- Image processing flag
        images_processed BOOLEAN DEFAULT false,

        -- Pipeline completion
        evaluation_complete BOOLEAN DEFAULT false,
        splitter_complete BOOLEAN DEFAULT false,
        marker_complete BOOLEAN DEFAULT false,

        -- Current agent
        current_agent VARCHAR(50),

        -- Overall status
        status VARCHAR(50) DEFAULT 'pending',

        -- Timestamps
        last_updated TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP DEFAULT NOW(),
        completed_at TIMESTAMP,

        CHECK (id = 1)
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_settings_table(table_prefix: str):
    """Create settings table (single-row)"""
    table_name = f"{table_prefix}_settings"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY DEFAULT 1,
        language VARCHAR(50) DEFAULT 'auto',
        ocr_quality VARCHAR(50) DEFAULT 'balanced',
        extraction_sensitivity VARCHAR(50) DEFAULT 'balanced',

        -- Diagram analysis prompts (2026-01-07)
        diagram_prompt TEXT,
        equation_prompt TEXT,
        table_prompt TEXT,

        -- OCR attribute selections (2026-01-07)
        ocr_attr1_id INTEGER,
        ocr_attr2_id INTEGER,
        ocr_attr3_id INTEGER,

        -- Manual attribute selections (2026-01-07)
        manual_attr1_id INTEGER,
        manual_attr2_id INTEGER,
        manual_attr3_id INTEGER,

        -- OCR text area labels (2026-01-07)
        ocr_label1 VARCHAR(200),
        ocr_label2 VARCHAR(200),
        ocr_label3 VARCHAR(200),

        -- Manual text area labels (2026-01-07)
        manual_label1 VARCHAR(200),
        manual_label2 VARCHAR(200),
        manual_label3 VARCHAR(200),

        CHECK (id = 1)
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_hierarchy_table(table_prefix: str):
    """Create hierarchy table for document structure"""
    table_name = f"{table_prefix}_hierarchy"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        node_id SERIAL PRIMARY KEY,
        parent_id INTEGER,
        level INTEGER,
        title VARCHAR(500),
        page_number INTEGER
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_attribute_keys_table(table_prefix: str):
    """Create attribute_keys table for 80 attributes (8 system-reserved + 72 user-defined)"""
    table_name = f"{table_prefix}_attribute_keys"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        attr_number INTEGER NOT NULL UNIQUE CHECK (attr_number BETWEEN 1 AND 80),
        key_name VARCHAR(100),
        is_system_reserved BOOLEAN DEFAULT false,
        is_editable BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def create_pipeline_config_table(table_prefix: str):
    """Create pipeline_config table for Claude pipeline steps (per book)"""
    table_name = f"{table_prefix}_pipeline_config"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        step_order INTEGER NOT NULL,
        step_name VARCHAR(100) NOT NULL,
        prompt_template TEXT,
        input_source VARCHAR(20) NOT NULL,      -- 'postgresql' or 'chromadb'
        input_field VARCHAR(100),               -- PostgreSQL column name or ChromaDB operation
        input_params JSONB,                     -- Additional params (e.g., max_results for search)
        output_destination VARCHAR(20) NOT NULL, -- 'postgresql' or 'chromadb'
        output_field VARCHAR(100),              -- PostgreSQL column name or ChromaDB operation
        claude_model VARCHAR(50),               -- 'sonnet-4', 'opus-4.5', 'haiku', NULL for no API call
        applies_to VARCHAR(20) DEFAULT 'paragraphs', -- 'paragraphs', 'diagrams', 'both'
        on_failure VARCHAR(30) DEFAULT 'skip_remaining', -- 'skip_remaining', 'continue'
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(step_order)
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create index
        index_sql = text(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_pipeline_config_order
        ON {table_name}(step_order)
        WHERE is_active = true
        """)
        conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()


def create_task_queue_table(table_prefix: str):
    """Create task_queue table for pipeline processing tasks (per book)"""
    table_name = f"{table_prefix}_task_queue"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        entity_type VARCHAR(20) NOT NULL,       -- 'paragraph' or 'diagram'
        entity_id INTEGER NOT NULL,             -- ID in paragraph_images or diagram_images table
        current_step INTEGER DEFAULT 1,
        total_steps INTEGER NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',   -- pending, running, completed, failed, paused
        priority INTEGER DEFAULT 0,

        -- Claude API caching (critical for cost control)
        api_response JSONB,                     -- Cached Claude response
        api_called_at TIMESTAMP,
        api_model_used VARCHAR(50),
        api_tokens_used INTEGER,

        -- Retry handling
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        last_error TEXT,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT NOW(),

        UNIQUE(entity_type, entity_id)
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create index for efficient querying
        index_sql = text(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_task_queue_pending
        ON {table_name} (entity_type, status, priority)
        WHERE status = 'pending'
        """)
        conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()


def create_step_progress_table(table_prefix: str):
    """Create step_progress table for per-record step tracking (per book)"""
    table_name = f"{table_prefix}_step_progress"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        entity_type VARCHAR(20) NOT NULL,       -- 'paragraph' or 'diagram'
        entity_id INTEGER NOT NULL,
        step_order INTEGER NOT NULL,
        step_name VARCHAR(100),
        status VARCHAR(20) DEFAULT 'pending',   -- pending, running, completed, failed, skipped

        -- Results
        api_response JSONB,                     -- Claude response for this step
        output_value TEXT,                      -- What was written to output field
        error_message TEXT,

        -- Timing
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        duration_ms INTEGER,

        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        UNIQUE(entity_type, entity_id, step_order)
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create index for efficient querying
        index_sql = text(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_prefix}_step_progress_entity
        ON {table_name} (entity_type, entity_id, step_order)
        """)
        conn.execute(index_sql)
        conn.commit()
    finally:
        conn.close()


def insert_default_processing_state(table_prefix: str, total_pages: int):
    """Insert default row into processing_state table"""
    table_name = f"{table_prefix}_processing_state"

    sql = text(f"""
    INSERT INTO {table_name} (id, total_pages, current_page, status)
    VALUES (1, :total_pages, 0, 'pending')
    ON CONFLICT (id) DO NOTHING
    """)

    with engine.connect() as conn:
        conn.execute(sql, {"total_pages": total_pages})
        conn.commit()


def insert_default_settings(table_prefix: str):
    """Insert default row into settings table"""
    table_name = f"{table_prefix}_settings"

    sql = text(f"""
    INSERT INTO {table_name} (id, language, ocr_quality, extraction_sensitivity)
    VALUES (1, 'auto', 'balanced', 'balanced')
    ON CONFLICT (id) DO NOTHING
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def insert_default_attribute_keys(table_prefix: str):
    """Insert 40 default rows into attribute_keys table (8 system-reserved + 32 user-defined)"""
    table_name = f"{table_prefix}_attribute_keys"

    # System-reserved attributes (1-8)
    system_attributes = {
        1: 'related_image',
        2: 'easyocr_text',
        3: 'surya_ocr_text',
        4: 'tesseract_text',
        5: 'easyocr_confidence',
        6: 'surya_ocr_confidence',
        7: 'tesseract_confidence',
        8: 'record_status'
    }

    with engine.connect() as conn:
        # Insert system-reserved attributes (1-8)
        for attr_num, key_name in system_attributes.items():
            sql = text(f"""
            INSERT INTO {table_name} (attr_number, key_name, is_system_reserved, is_editable)
            VALUES (:attr_num, :key_name, true, false)
            ON CONFLICT (attr_number) DO NOTHING
            """)
            conn.execute(sql, {"attr_num": attr_num, "key_name": key_name})

        # Insert user-defined attributes (9-80)
        for i in range(9, 81):
            sql = text(f"""
            INSERT INTO {table_name} (attr_number, key_name, is_system_reserved, is_editable)
            VALUES (:attr_num, NULL, false, true)
            ON CONFLICT (attr_number) DO NOTHING
            """)
            conn.execute(sql, {"attr_num": i})

        conn.commit()


def create_book_tables(book_id: int, sanitized_name: str, total_pages: int, extraction_method: str = "v2"):
    """
    Create book-specific tables based on extraction method.

    Args:
        book_id: Unique book identifier
        sanitized_name: Sanitized book name for table prefix
        total_pages: Total number of pages in the book
        extraction_method: 'v1', 'v2', or 'both' (default: 'v2')

    Tables created for ALL methods:
    - raw_pages (page images from PDF)
    - pages (page-level info with marking rectangles)
    - processing_state (processing progress)
    - settings (book settings)
    - level1_titles, level2_titles (title hierarchy)

    Additional tables for V1:
    - raw_knowledge_units, raw_paragraph_images, raw_diagram_images
    - knowledge_units, images, hierarchy, attribute_keys
    - pipeline_config, task_queue, step_progress
    - layout_detections, knowledge_pages, cloud_ocr_pages

    Additional tables for V2:
    - v2_knowledge_pages, v2_extraction_log, v2_few_shot_examples, v2_attribute_keys
    """
    # Generate table prefix
    table_prefix = generate_table_prefix(book_id, sanitized_name)

    # === SHARED TABLES (always created) ===
    create_raw_pages_table(table_prefix)
    create_pages_table(table_prefix)
    create_processing_state_table(table_prefix)
    create_settings_table(table_prefix)
    insert_default_processing_state(table_prefix, total_pages)
    insert_default_settings(table_prefix)

    # Title hierarchy tables (needed for both V1 and V2)
    create_level1_titles_table(table_prefix)
    create_level2_titles_table(table_prefix)

    # === V1 TABLES ===
    if extraction_method in ('v1', 'both'):
        create_raw_knowledge_units_table(table_prefix)
        create_raw_paragraph_images_table(table_prefix)
        create_raw_diagram_images_table(table_prefix)
        create_knowledge_units_table(table_prefix)
        create_images_table(table_prefix)
        create_hierarchy_table(table_prefix)
        create_attribute_keys_table(table_prefix)
        create_pipeline_config_table(table_prefix)
        create_task_queue_table(table_prefix)
        create_step_progress_table(table_prefix)
        insert_default_attribute_keys(table_prefix)
        create_layout_detections_table(table_prefix)
        create_knowledge_pages_table(table_prefix)
        create_cloud_ocr_pages_table(table_prefix)

    # === V2 TABLES ===
    if extraction_method in ('v2', 'both'):
        create_v2_book_tables(table_prefix)


def create_layout_detections_table(table_prefix: str):
    """Create layout_detections table for YOLO-detected regions and corrections.

    This table stores:
    - Detected regions from DocLayout-YOLO
    - User corrections for fine-tuning
    - Links to paragraphs/diagrams after OCR
    """
    table_name = f"raw_{table_prefix}_layout_detections"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL,

        -- Detection info
        class_name VARCHAR(50) NOT NULL,
        class_id INTEGER,
        x INTEGER NOT NULL,
        y INTEGER NOT NULL,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        confidence FLOAT,

        -- Original detection (before corrections)
        original_x INTEGER,
        original_y INTEGER,
        original_width INTEGER,
        original_height INTEGER,
        original_class VARCHAR(50),

        -- Correction tracking
        was_corrected BOOLEAN DEFAULT FALSE,
        correction_type VARCHAR(30),
        correction_timestamp TIMESTAMP,

        -- Relationships
        parent_region_id INTEGER,

        -- Links to other tables
        linked_paragraph_id INTEGER,
        linked_diagram_id INTEGER,
        linked_knowledge_unit_id INTEGER,

        -- OCR result for this region
        ocr_text TEXT,
        ocr_confidence FLOAT,

        -- Review status
        review_status VARCHAR(30) DEFAULT 'pending',
        reviewed_at TIMESTAMP,

        -- Model info
        model_version INTEGER,
        detection_batch_id VARCHAR(50),

        -- Export tracking
        exported_for_training BOOLEAN DEFAULT FALSE,
        exported_at TIMESTAMP,

        -- Title Hierarchy Foreign Keys (Requirement 4)
        l1_title_id INTEGER,
        l2_title_id INTEGER,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_layout_det_page ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_layout_det_class ON {table_name}(class_name)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_layout_det_status ON {table_name}(review_status)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_layout_det_corrected ON {table_name}(was_corrected) WHERE was_corrected = true",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_layout_det_parent ON {table_name}(parent_region_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_ld_l1_title ON {table_name}(l1_title_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_ld_l2_title ON {table_name}(l2_title_id)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_level1_titles_table(table_prefix: str):
    """Create level1_titles table with 200 custom attributes for chapter-level titles.
    
    Each L1 title covers a page range and can have up to 200 custom attributes
    with user-definable names and values.
    """
    table_name = f"{table_prefix}_level1_titles"
    
    # Build attribute columns (200 pairs of name/value)
    attr_columns = []
    for i in range(1, 201):
        attr_columns.append(f"attr{i}_name VARCHAR(100)")
        attr_columns.append(f"attr{i}_value TEXT")
    
    attr_columns_sql = ",\n        ".join(attr_columns)
    
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        title_text VARCHAR(500) NOT NULL,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,
        display_order INTEGER DEFAULT 0,
        
        -- Cross-book access writable range (Requirement 5)
        external_writable_start INTEGER DEFAULT 151,
        external_writable_end INTEGER DEFAULT 200,
        
        -- 200 custom attributes (name + value pairs)
        {attr_columns_sql},
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)
    
    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
        
        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_l1_pages ON {table_name}(start_page, end_page)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_l1_order ON {table_name}(display_order)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_level2_titles_table(table_prefix: str):
    """Create level2_titles table with 150 custom attributes for section-level titles.
    
    Each L2 title covers a page range within its parent L1 title and can have
    up to 150 custom attributes with user-definable names and values.
    """
    table_name = f"{table_prefix}_level2_titles"
    l1_table = f"{table_prefix}_level1_titles"
    
    # Build attribute columns (150 pairs of name/value)
    attr_columns = []
    for i in range(1, 151):
        attr_columns.append(f"attr{i}_name VARCHAR(100)")
        attr_columns.append(f"attr{i}_value TEXT")
    
    attr_columns_sql = ",\n        ".join(attr_columns)
    
    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        title_text VARCHAR(500) NOT NULL,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,
        parent_l1_id INTEGER,
        display_order INTEGER DEFAULT 0,
        
        -- Cross-book access writable range (Requirement 5)
        external_writable_start INTEGER DEFAULT 101,
        external_writable_end INTEGER DEFAULT 150,
        
        -- 150 custom attributes (name + value pairs)
        {attr_columns_sql},
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)
    
    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
        
        # Create indexes
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_l2_pages ON {table_name}(start_page, end_page)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_l2_parent ON {table_name}(parent_l1_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_l2_order ON {table_name}(display_order)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_knowledge_pages_table(table_prefix: str):
    """Create knowledge_pages table for Qwen VL structured output grouped by L3 title."""
    table_name = f"{table_prefix}_knowledge_pages"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        l3_title TEXT,
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,
        l1_title_id INTEGER,
        l2_title_id INTEGER,
        l1_title_text VARCHAR(500),
        l2_title_text VARCHAR(500),
        content JSONB NOT NULL,
        ocr_engine VARCHAR(50) DEFAULT 'qwen-cloud',
        model_name VARCHAR(100),
        cached_tokens INTEGER DEFAULT 0,
        total_input_tokens INTEGER DEFAULT 0,
        total_output_tokens INTEGER DEFAULT 0,
        status VARCHAR(30) DEFAULT 'extracted',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_kp_pages ON {table_name}(start_page, end_page)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_kp_status ON {table_name}(status)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_kp_l3 ON {table_name}(l3_title)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_cloud_ocr_pages_table(table_prefix: str):
    """Create cloud_ocr_pages table for per-page cloud extraction tracking."""
    table_name = f"{table_prefix}_cloud_ocr_pages"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL UNIQUE,
        status VARCHAR(20) DEFAULT 'pending',
        error_message TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cached_tokens INTEGER,
        processing_time_ms INTEGER,
        model_name VARCHAR(100),
        attempt_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_cop_status ON {table_name}(status)",
            f"CREATE INDEX IF NOT EXISTS idx_{table_prefix}_cop_page ON {table_name}(page_number)"
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()



# ============================================================================
# V2 EXTRACTION TABLES
# ============================================================================

def create_v2_knowledge_pages_table(table_prefix: str):
    """Create V2 knowledge_pages table for cloud LLM extraction results.
    
    Stores knowledge pages (content between consecutive L3 titles) with:
    - Dedicated queryable columns for key fields
    - Raw XML from LLM response
    - Parsed JSON for enrichment queries
    - 80 user-defined attributes
    """
    table_name = f"v2_{table_prefix}_knowledge_pages"

    # Build 80 attribute columns
    attr_columns = ",\n        ".join(
        [f"attr{i}_value TEXT" for i in range(1, 81)]
    )

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,

        -- Title hierarchy (queryable, FK IDs)
        l1_title_id INTEGER,
        l2_title_id INTEGER,
        l3_title_text VARCHAR(500),
        l3_title_end_text VARCHAR(500),

        -- Page range (queryable)
        start_page INTEGER NOT NULL,
        end_page INTEGER NOT NULL,

        -- Summary (queryable)
        summary TEXT,

        -- Classification (queryable)
        difficulty_score INTEGER,
        concept_type VARCHAR(50),
        bloom_taxonomy_level VARCHAR(20),
        physics_domain VARCHAR(50),
        exam_relevance VARCHAR(10),
        extraction_confidence VARCHAR(10),
        has_worked_example BOOLEAN DEFAULT FALSE,
        has_problem_set BOOLEAN DEFAULT FALSE,
        element_count INTEGER DEFAULT 0,

        -- Review (queryable)
        verified BOOLEAN DEFAULT FALSE,
        notes TEXT,
        record_status VARCHAR(20) DEFAULT 'enabled',

        -- Full content storage
        raw_xml TEXT,
        parsed_json JSONB,

        -- 80 user-defined attributes
        {attr_columns},

        -- Extraction metadata
        llm_provider VARCHAR(50),
        model_name VARCHAR(100),
        window_pages TEXT,

        -- Timestamps
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_pages ON {table_name}(start_page, end_page)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_l1 ON {table_name}(l1_title_id)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_l2 ON {table_name}(l2_title_id)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_l3 ON {table_name}(l3_title_text)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_status ON {table_name}(record_status)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_verified ON {table_name}(verified)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_difficulty ON {table_name}(difficulty_score)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_domain ON {table_name}(physics_domain)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_kp_concept ON {table_name}(concept_type)",
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_v2_extraction_log_table(table_prefix: str):
    """Create V2 extraction_log table for per-API-call tracking."""
    table_name = f"v2_{table_prefix}_extraction_log"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        window_start_page INTEGER NOT NULL,
        window_end_page INTEGER NOT NULL,
        window_pages TEXT,
        knowledge_page_id INTEGER,

        -- Token tracking
        input_tokens_cached INTEGER DEFAULT 0,
        input_tokens_uncached INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,

        -- Cost tracking
        cost_input_cached NUMERIC(10,6) DEFAULT 0,
        cost_input_uncached NUMERIC(10,6) DEFAULT 0,
        cost_output NUMERIC(10,6) DEFAULT 0,
        cost_total NUMERIC(10,6) DEFAULT 0,

        -- Timing
        processing_time_ms INTEGER,

        -- Status
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        attempt_number INTEGER DEFAULT 1,
        retry_phase INTEGER DEFAULT 1,

        -- Model info
        llm_provider VARCHAR(50),
        model_name VARCHAR(100),

        created_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_elog_status ON {table_name}(status)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_elog_pages ON {table_name}(window_start_page, window_end_page)",
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_v2_few_shot_examples_table(table_prefix: str):
    """Create V2 few_shot_examples table for annotated training pages."""
    table_name = f"v2_{table_prefix}_few_shot_examples"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        page_number INTEGER NOT NULL,
        annotated_image_path TEXT,
        annotation_data JSONB,
        cache_name VARCHAR(200),
        sent_to_llm BOOLEAN DEFAULT FALSE,
        sent_at TIMESTAMP,
        llm_provider VARCHAR(50),
        model_name VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()

        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_fs_page ON {table_name}(page_number)",
            f"CREATE INDEX IF NOT EXISTS idx_v2_{table_prefix}_fs_sent ON {table_name}(sent_to_llm)",
        ]
        for index_sql in indexes:
            conn.execute(text(index_sql))
        conn.commit()
    finally:
        conn.close()


def create_v2_attribute_keys_table(table_prefix: str):
    """Create V2 attribute_keys table for 80 attributes (independent from V1).
    
    Each attribute has a key_name that can be referenced in LLM prompt templates
    via the TemplateEngine pattern: {{key_name}} -> attrN_value column.
    """
    table_name = f"v2_{table_prefix}_attribute_keys"

    sql = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        attr_number INTEGER NOT NULL UNIQUE CHECK (attr_number BETWEEN 1 AND 80),
        key_name VARCHAR(100),
        is_system_reserved BOOLEAN DEFAULT false,
        is_editable BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn = engine.connect()
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


def insert_default_v2_attribute_keys(table_prefix: str):
    """Insert default V2 attribute keys (80 rows, no system-reserved for V2)."""
    table_name = f"v2_{table_prefix}_attribute_keys"

    conn = engine.connect()
    try:
        for i in range(1, 81):
            sql = text(f"""
                INSERT INTO {table_name} (attr_number, key_name, is_system_reserved, is_editable)
                VALUES (:num, NULL, false, true)
                ON CONFLICT (attr_number) DO NOTHING
            """)
            conn.execute(sql, {"num": i})
        conn.commit()
    finally:
        conn.close()


def create_v2_book_tables(table_prefix: str):
    """Create all V2-specific tables for a book.
    
    Called when extraction_method is 'v2' or 'both'.
    """
    create_v2_knowledge_pages_table(table_prefix)
    create_v2_extraction_log_table(table_prefix)
    create_v2_few_shot_examples_table(table_prefix)
    create_v2_attribute_keys_table(table_prefix)
    insert_default_v2_attribute_keys(table_prefix)
