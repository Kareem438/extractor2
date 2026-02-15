"""
V2 Extraction Service

Core rolling window extraction engine for V2 cloud-based knowledge extraction.
Handles: rolling window algorithm, smart jump logic, L1/L2 title injection,
retry logic, cost tracking, pause/resume/cancel controls.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import text
from src.database.connection import engine
from src.services.llm_provider_service import LLMProviderService
from src.services.xml_parser_service import XMLParserService
from src.services.few_shot_service import FewShotService
from src.utils.logging_config import logger


# Extraction state per book (in-memory)
_extraction_states: Dict[int, Dict[str, Any]] = {}


class V2ExtractionService:
    """Core V2 extraction engine with rolling window algorithm."""

    def __init__(self):
        self.llm_service = LLMProviderService()
        self.xml_parser = XMLParserService()
        self.few_shot_service = FewShotService()

    # =========================================================================
    # State Management
    # =========================================================================

    def get_state(self, book_id: int) -> Dict[str, Any]:
        """Get current extraction state for a book."""
        if book_id not in _extraction_states:
            _extraction_states[book_id] = {
                "status": "idle",  # idle, running, paused, cancelled, completed, error
                "current_page": 0,
                "total_pages": 0,
                "knowledge_pages_extracted": 0,
                "total_api_calls": 0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cached_tokens": 0,
                "errors": [],
                "last_error": None,
                "started_at": None,
                "provider": None,
                "model": None,
                "min_delay": 5.0,
                "retry_count": 0,
                "cooldown_until": None,
            }
        return _extraction_states[book_id]

    def pause(self, book_id: int) -> bool:
        """Pause extraction."""
        state = self.get_state(book_id)
        if state["status"] == "running":
            state["status"] = "paused"
            logger.info(f"V2 extraction paused for book {book_id}")
            return True
        return False

    def resume(self, book_id: int) -> bool:
        """Resume paused extraction."""
        state = self.get_state(book_id)
        if state["status"] == "paused":
            state["status"] = "running"
            logger.info(f"V2 extraction resumed for book {book_id}")
            return True
        return False

    def cancel(self, book_id: int) -> bool:
        """Cancel extraction."""
        state = self.get_state(book_id)
        if state["status"] in ("running", "paused"):
            state["status"] = "cancelled"
            logger.info(f"V2 extraction cancelled for book {book_id}")
            return True
        return False

    # =========================================================================
    # Pre-requisite Checks
    # =========================================================================

    def check_prerequisites(self, book_id: int) -> Dict[str, Any]:
        """Check all prerequisites before starting extraction."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return {"ready": False, "checks": {"book_exists": False}}

        checks = {}

        # 1. L1 titles defined
        l1_table = f"{table_prefix}_level1_titles"
        with engine.connect() as conn:
            r = conn.execute(text(f"SELECT COUNT(*) FROM {l1_table}"))
            l1_count = r.scalar()
        checks["l1_titles_defined"] = l1_count > 0

        # 2. L2 titles defined
        l2_table = f"{table_prefix}_level2_titles"
        with engine.connect() as conn:
            r = conn.execute(text(f"SELECT COUNT(*) FROM {l2_table}"))
            l2_count = r.scalar()
        checks["l2_titles_defined"] = l2_count > 0

        # 3. API key configured (at least one enabled provider)
        enabled = self.llm_service.get_enabled_providers()
        checks["api_key_configured"] = len(enabled) > 0

        # 4. Few-shot examples sent
        sent = self.few_shot_service.get_sent_examples(book_id)
        checks["few_shots_sent"] = len(sent) > 0

        ready = all(checks.values())
        return {
            "ready": ready,
            "checks": checks,
            "l1_count": l1_count,
            "l2_count": l2_count,
            "enabled_providers": len(enabled),
            "few_shots_sent": len(sent)
        }

    # =========================================================================
    # Title Hierarchy Loading
    # =========================================================================

    def _load_l1_titles(self, table_prefix: str) -> List[Dict]:
        """Load L1 titles with page ranges."""
        table = f"{table_prefix}_level1_titles"
        with engine.connect() as conn:
            r = conn.execute(text(f"""
                SELECT id, title_text, start_page, end_page
                FROM {table} ORDER BY start_page
            """))
            return [{"id": row[0], "text": row[1], "start": row[2], "end": row[3]}
                    for row in r.fetchall()]

    def _load_l2_titles(self, table_prefix: str) -> List[Dict]:
        """Load L2 titles with page ranges."""
        table = f"{table_prefix}_level2_titles"
        with engine.connect() as conn:
            r = conn.execute(text(f"""
                SELECT id, title_text, start_page, end_page, level1_title_id
                FROM {table} ORDER BY start_page
            """))
            return [{"id": row[0], "text": row[1], "start": row[2], "end": row[3],
                     "l1_id": row[4]}
                    for row in r.fetchall()]

    def _find_title_for_page(self, titles: List[Dict], page: int) -> Optional[Dict]:
        """Find the title that covers a given page number."""
        for t in titles:
            if t["start"] <= page <= (t["end"] or 99999):
                return t
        return None

    # =========================================================================
    # Prompt Management
    # =========================================================================

    def get_prompts(self, book_id: int) -> Dict[str, str]:
        """Get system and extraction prompts for a book (from settings or defaults)."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return {"system_prompt": self._default_system_prompt(),
                    "extraction_prompt": self._default_extraction_prompt()}

        settings_table = f"{table_prefix}_settings"
        with engine.connect() as conn:
            r = conn.execute(text(f"""
                SELECT setting_value FROM {settings_table}
                WHERE setting_key = 'v2_system_prompt'
            """))
            row = r.fetchone()
            system_prompt = row[0] if row else None

            r = conn.execute(text(f"""
                SELECT setting_value FROM {settings_table}
                WHERE setting_key = 'v2_extraction_prompt'
            """))
            row = r.fetchone()
            extraction_prompt = row[0] if row else None

        return {
            "system_prompt": system_prompt or self._default_system_prompt(),
            "extraction_prompt": extraction_prompt or self._default_extraction_prompt()
        }

    def save_prompts(self, book_id: int, system_prompt: str, extraction_prompt: str) -> bool:
        """Save custom prompts for a book."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return False

        settings_table = f"{table_prefix}_settings"
        with engine.connect() as conn:
            for key, value in [("v2_system_prompt", system_prompt),
                               ("v2_extraction_prompt", extraction_prompt)]:
                conn.execute(text(f"""
                    INSERT INTO {settings_table} (setting_key, setting_value)
                    VALUES (:key, :val)
                    ON CONFLICT (setting_key) DO UPDATE SET setting_value = :val
                """), {"key": key, "val": value})
            conn.commit()
        return True

    def _default_system_prompt(self) -> str:
        return """You are an expert physics textbook content extractor. Your task is to analyze textbook page images and extract structured knowledge in XML format.

CRITICAL REQUIREMENTS:
1. Extract ALL content with full fidelity — capture enough detail that the original content could be regenerated from your extraction, including formatting styles, emphasis, and layout.
2. Use the provided XML schema with 9 categories (A through I).
3. Each knowledge page represents content between consecutive L3 (sub-section) boundaries.
4. L1 and L2 titles are provided by the system — do NOT extract them from the page. Use the provided values.
5. L3 titles (sub-section boundaries) are YOUR responsibility to identify and extract.
6. Maintain reading order and element relationships.
7. For equations, use LaTeX format.
8. For diagrams, provide detailed physics-specific descriptions.
9. Classify difficulty, concept type, and exam relevance accurately for Egyptian Thanawiya Amma physics.
10. Generate enrichment content (explanations, pain points, FAQ) that adds genuine educational value."""

    def _default_extraction_prompt(self) -> str:
        return """Analyze the following textbook page(s) and extract ALL knowledge content in XML format.

CONTEXT:
- L1 Title (Chapter): {{l1_title}}
- L2 Title (Section): {{l2_title}}
- Page range: {{page_range}}
- Previous L3 title ended at: {{prev_l3_title}}

INSTRUCTIONS:
1. Identify L3 boundaries (sub-section breaks) within these pages.
2. For each knowledge page (content between L3 boundaries), output a <knowledge_page> XML element.
3. Include ALL 9 categories (A-I) of tags as defined in the schema.
4. Capture the FULL content — every paragraph, equation, diagram, example, and problem.
5. Ensure content fidelity is high enough to regenerate the original material.

OUTPUT FORMAT:
<extraction>
  <knowledge_page>
    <!-- Category A: Text Extraction -->
    <arabic_text>...</arabic_text>
    <english_text>...</english_text>
    <equation>...</equation>
    <!-- ... all other tags ... -->
    
    <!-- Category B: Structural Metadata -->
    <l3_title>...</l3_title>
    <page_range>start-end</page_range>
    <!-- ... -->
    
    <!-- Categories C through I -->
    <!-- ... all tags ... -->
  </knowledge_page>
</extraction>

If the pages span multiple L3 boundaries, output multiple <knowledge_page> elements."""

    # =========================================================================
    # Core Extraction Engine
    # =========================================================================

    async def start_extraction(self, book_id: int, provider_name: str,
                                min_delay: float = 5.0) -> Dict[str, Any]:
        """
        Start the rolling window extraction process.
        
        This is the main entry point — runs as a background task.
        """
        state = self.get_state(book_id)
        if state["status"] == "running":
            return {"error": "Extraction already running"}

        # Get book info
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return {"error": "Book not found"}

        total_pages = self._get_total_pages(book_id)

        # Check prerequisites
        prereqs = self.check_prerequisites(book_id)
        if not prereqs["ready"]:
            failed = [k for k, v in prereqs["checks"].items() if not v]
            return {"error": f"Prerequisites not met: {', '.join(failed)}"}

        # Initialize state
        state.update({
            "status": "running",
            "current_page": 1,
            "total_pages": total_pages,
            "knowledge_pages_extracted": 0,
            "total_api_calls": 0,
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cached_tokens": 0,
            "errors": [],
            "last_error": None,
            "started_at": time.time(),
            "provider": provider_name,
            "min_delay": min_delay,
            "retry_count": 0,
            "cooldown_until": None,
        })

        # Get provider model name
        provider = self.llm_service.get_provider_by_name(provider_name)
        state["model"] = provider["model_name"] if provider else "unknown"

        # Run extraction in background
        asyncio.create_task(self._run_extraction(book_id, provider_name, table_prefix))

        return {"message": "Extraction started", "total_pages": total_pages}

    async def _run_extraction(self, book_id: int, provider_name: str, table_prefix: str):
        """Main extraction loop — runs as background task."""
        state = self.get_state(book_id)
        
        try:
            # Load context
            l1_titles = self._load_l1_titles(table_prefix)
            l2_titles = self._load_l2_titles(table_prefix)
            prompts = self.get_prompts(book_id)
            
            current_page = state["current_page"]
            total_pages = state["total_pages"]
            last_l3_title = None
            window_size = 4

            while current_page <= total_pages:
                # Check pause/cancel
                if state["status"] == "cancelled":
                    logger.info(f"V2 extraction cancelled at page {current_page}")
                    break

                if state["status"] == "paused":
                    while state["status"] == "paused":
                        await asyncio.sleep(1)
                    if state["status"] == "cancelled":
                        break

                # Check cooldown
                if state["cooldown_until"] and time.time() < state["cooldown_until"]:
                    wait_time = state["cooldown_until"] - time.time()
                    logger.info(f"Cooldown: waiting {wait_time:.0f}s")
                    await asyncio.sleep(wait_time)
                    state["cooldown_until"] = None

                # Determine window pages
                window_end = min(current_page + window_size - 1, total_pages)
                window_pages = list(range(current_page, window_end + 1))

                # Find L1/L2 for current page
                l1 = self._find_title_for_page(l1_titles, current_page)
                l2 = self._find_title_for_page(l2_titles, current_page)

                state["current_page"] = current_page

                # Get page images
                images = []
                for p in window_pages:
                    img = self.few_shot_service.get_page_image_base64(book_id, p)
                    if img:
                        images.append(img)

                if not images:
                    logger.warning(f"No images for pages {window_pages}, skipping")
                    current_page = window_end + 1
                    continue

                # Build prompt with L1/L2 injection
                extraction_prompt = prompts["extraction_prompt"]
                extraction_prompt = extraction_prompt.replace("{{l1_title}}", l1["text"] if l1 else "Unknown")
                extraction_prompt = extraction_prompt.replace("{{l2_title}}", l2["text"] if l2 else "Unknown")
                extraction_prompt = extraction_prompt.replace("{{page_range}}", f"{current_page}-{window_end}")
                extraction_prompt = extraction_prompt.replace("{{prev_l3_title}}", last_l3_title or "Start of section")

                messages = [
                    {"role": "system", "content": prompts["system_prompt"]},
                    {"role": "user", "content": extraction_prompt}
                ]

                # Call LLM with retry logic
                response = await self._call_with_retry(
                    book_id, provider_name, messages, images, window_pages, table_prefix
                )

                if response is None:
                    # Retry exhausted — try expanded window or skip
                    if window_size == 4:
                        window_size = 8
                        logger.info(f"Expanding window to 8 pages at page {current_page}")
                        continue
                    else:
                        # Log error and skip
                        self._log_extraction(table_prefix, current_page, window_end,
                                             window_pages, None, 0, 0, 0, 0, 0,
                                             "failed", "Retry exhausted", provider_name,
                                             state["model"])
                        state["errors"].append(f"Page {current_page}: retry exhausted")
                        current_page = window_end + 1
                        window_size = 4
                        continue

                # Parse XML response
                try:
                    parsed_pages = self.xml_parser.parse_xml_response(response["content"])
                except ValueError as e:
                    logger.error(f"XML parse error at page {current_page}: {e}")
                    state["errors"].append(f"Page {current_page}: XML parse error")
                    current_page = window_end + 1
                    window_size = 4
                    continue

                # Save knowledge pages
                last_end_page = current_page
                for kp_data in parsed_pages:
                    kp_id = self._save_knowledge_page(
                        table_prefix, book_id, kp_data,
                        l1["id"] if l1 else None,
                        l2["id"] if l2 else None,
                        window_pages, provider_name, state["model"]
                    )
                    state["knowledge_pages_extracted"] += 1

                    # Track last L3 and end page
                    if kp_data["tags"].get("l3_title"):
                        last_l3_title = kp_data["tags"]["l3_title"]

                    page_range = self.xml_parser.get_page_range(kp_data["raw_xml"])
                    if page_range:
                        last_end_page = max(last_end_page, page_range[1])

                # Log extraction
                self._log_extraction(
                    table_prefix, current_page, window_end, window_pages,
                    None, response.get("input_tokens", 0),
                    response.get("output_tokens", 0),
                    response.get("input_tokens_cached", 0),
                    0, response.get("processing_time_ms", 0),
                    "success", None, provider_name, state["model"]
                )

                # Update cost tracking
                self._update_cost(state, response)

                # Smart jump: start next window from last KP end page
                current_page = max(last_end_page, window_end) + 1
                window_size = 4  # Reset window size

                # Throttle
                await asyncio.sleep(state["min_delay"])

            # Extraction complete
            if state["status"] != "cancelled":
                state["status"] = "completed"
            logger.info(f"V2 extraction finished for book {book_id}: "
                        f"{state['knowledge_pages_extracted']} KPs, "
                        f"${state['total_cost']:.4f} total cost")

        except Exception as e:
            logger.error(f"V2 extraction error for book {book_id}: {e}", exc_info=True)
            state["status"] = "error"
            state["last_error"] = str(e)

    # =========================================================================
    # Retry Logic
    # =========================================================================

    async def _call_with_retry(self, book_id: int, provider_name: str,
                                messages: List[Dict], images: List[str],
                                window_pages: List[int], table_prefix: str
                                ) -> Optional[Dict[str, Any]]:
        """
        Call LLM with retry logic:
        Phase 1: 3 immediate retries
        Phase 2: 15min cooldown, then 3 more retries
        Phase 3: Alert user (pause extraction)
        """
        state = self.get_state(book_id)
        max_retries_per_phase = 3

        for phase in (1, 2):
            for attempt in range(1, max_retries_per_phase + 1):
                try:
                    response = await self.llm_service.call_llm(
                        provider_name, messages, max_tokens=4096,
                        temperature=0.1, images=images
                    )

                    # Validate XML
                    is_valid, error = self.xml_parser.validate_xml(response["content"])
                    if is_valid:
                        state["retry_count"] = 0
                        return response
                    else:
                        logger.warning(f"Invalid XML (attempt {attempt}, phase {phase}): {error}")
                        state["retry_count"] += 1

                except TimeoutError:
                    logger.warning(f"LLM timeout (attempt {attempt}, phase {phase})")
                    state["retry_count"] += 1
                except Exception as e:
                    error_str = str(e)
                    # Handle rate limiting
                    if "429" in error_str or "rate" in error_str.lower():
                        logger.warning(f"Rate limited, backing off...")
                        await asyncio.sleep(state["min_delay"] * 2)
                    logger.warning(f"LLM error (attempt {attempt}, phase {phase}): {e}")
                    state["retry_count"] += 1

                # Brief delay between retries
                await asyncio.sleep(2)

            # After phase 1 exhausted, enter cooldown before phase 2
            if phase == 1:
                logger.info(f"Phase 1 retries exhausted, entering 15min cooldown")
                state["cooldown_until"] = time.time() + 900  # 15 minutes
                state["status"] = "paused"
                state["last_error"] = "Retries exhausted — 15min cooldown before phase 2"

                # Wait for cooldown
                while time.time() < state["cooldown_until"]:
                    if state["status"] == "cancelled":
                        return None
                    await asyncio.sleep(5)

                state["status"] = "running"
                state["cooldown_until"] = None

        # All retries exhausted — alert user
        state["status"] = "error"
        state["last_error"] = "All retries exhausted. User intervention required."
        logger.error(f"V2 extraction: all retries exhausted at pages {window_pages}")
        return None

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _save_knowledge_page(self, table_prefix: str, book_id: int,
                              kp_data: Dict[str, Any],
                              l1_id: Optional[int], l2_id: Optional[int],
                              window_pages: List[int],
                              provider: str, model: str) -> int:
        """Save a parsed knowledge page to the V2 table."""
        table_name = f"v2_{table_prefix}_knowledge_pages"
        qf = kp_data["queryable_fields"]

        # Determine page range
        page_range = self.xml_parser.get_page_range(kp_data["raw_xml"])
        start_page = page_range[0] if page_range else window_pages[0]
        end_page = page_range[1] if page_range else window_pages[-1]

        # Build parsed JSON
        parsed_json = json.dumps(kp_data["tags"])

        with engine.connect() as conn:
            result = conn.execute(text(f"""
                INSERT INTO {table_name} (
                    l1_title_id, l2_title_id, l3_title_text, l3_title_end_text,
                    start_page, end_page, summary,
                    difficulty_score, concept_type, bloom_taxonomy_level,
                    physics_domain, exam_relevance, extraction_confidence,
                    has_worked_example, has_problem_set, element_count,
                    raw_xml, parsed_json,
                    llm_provider, model_name, window_pages
                ) VALUES (
                    :l1_id, :l2_id, :l3_title, :l3_end,
                    :start_page, :end_page, :summary,
                    :difficulty, :concept_type, :bloom,
                    :domain, :exam_rel, :confidence,
                    :worked_ex, :problem_set, :elem_count,
                    :raw_xml, :parsed_json,
                    :provider, :model, :window_pages
                ) RETURNING id
            """), {
                "l1_id": l1_id,
                "l2_id": l2_id,
                "l3_title": qf.get("l3_title_text"),
                "l3_end": kp_data["tags"].get("l3_title_end", kp_data["tags"].get("l3_title")),
                "start_page": start_page,
                "end_page": end_page,
                "summary": kp_data["summary"],
                "difficulty": qf.get("difficulty_score"),
                "concept_type": qf.get("concept_type"),
                "bloom": qf.get("bloom_taxonomy_level"),
                "domain": qf.get("physics_domain"),
                "exam_rel": qf.get("exam_relevance"),
                "confidence": qf.get("extraction_confidence"),
                "worked_ex": qf.get("has_worked_example", False),
                "problem_set": qf.get("has_problem_set", False),
                "elem_count": kp_data["element_count"],
                "raw_xml": kp_data["raw_xml"],
                "parsed_json": parsed_json,
                "provider": provider,
                "model": model,
                "window_pages": json.dumps(window_pages)
            })
            conn.commit()
            return result.scalar()

    def _log_extraction(self, table_prefix: str, start_page: int, end_page: int,
                         window_pages: List[int], kp_id: Optional[int],
                         input_tokens: int, output_tokens: int, cached_tokens: int,
                         cost_total: float, processing_time_ms: int,
                         status: str, error_msg: Optional[str],
                         provider: str, model: str):
        """Log an extraction API call."""
        table_name = f"v2_{table_prefix}_extraction_log"
        with engine.connect() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_name} (
                    window_start_page, window_end_page, window_pages,
                    knowledge_page_id, input_tokens_uncached, input_tokens_cached,
                    output_tokens, cost_total, processing_time_ms,
                    status, error_message, llm_provider, model_name
                ) VALUES (
                    :start, :end, :pages, :kp_id,
                    :input_tokens, :cached_tokens, :output_tokens,
                    :cost, :time_ms, :status, :error, :provider, :model
                )
            """), {
                "start": start_page, "end": end_page,
                "pages": json.dumps(window_pages),
                "kp_id": kp_id,
                "input_tokens": input_tokens,
                "cached_tokens": cached_tokens,
                "output_tokens": output_tokens,
                "cost": cost_total,
                "time_ms": processing_time_ms,
                "status": status, "error": error_msg,
                "provider": provider, "model": model
            })
            conn.commit()

    def _update_cost(self, state: Dict, response: Dict):
        """Update running cost totals in state."""
        input_tokens = response.get("input_tokens", 0)
        output_tokens = response.get("output_tokens", 0)
        cached_tokens = response.get("input_tokens_cached", 0)
        uncached_tokens = input_tokens - cached_tokens

        # GPT-5 pricing estimates (per 1M tokens)
        input_price = 1.25 / 1_000_000
        cached_price = 0.125 / 1_000_000
        output_price = 10.0 / 1_000_000

        cost = (uncached_tokens * input_price +
                cached_tokens * cached_price +
                output_tokens * output_price)

        state["total_api_calls"] += 1
        state["total_input_tokens"] += input_tokens
        state["total_output_tokens"] += output_tokens
        state["total_cached_tokens"] += cached_tokens
        state["total_cost"] += cost

    # =========================================================================
    # Dry Run
    # =========================================================================

    async def dry_run(self, book_id: int, provider_name: str,
                       page_number: int) -> Dict[str, Any]:
        """
        Run extraction on a single page without saving results.
        Used for testing prompts and reviewing output quality.
        """
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return {"error": "Book not found"}

        l1_titles = self._load_l1_titles(table_prefix)
        l2_titles = self._load_l2_titles(table_prefix)
        prompts = self.get_prompts(book_id)

        l1 = self._find_title_for_page(l1_titles, page_number)
        l2 = self._find_title_for_page(l2_titles, page_number)

        # Get page image
        img = self.few_shot_service.get_page_image_base64(book_id, page_number)
        if not img:
            return {"error": f"No image found for page {page_number}"}

        # Build prompt
        extraction_prompt = prompts["extraction_prompt"]
        extraction_prompt = extraction_prompt.replace("{{l1_title}}", l1["text"] if l1 else "Unknown")
        extraction_prompt = extraction_prompt.replace("{{l2_title}}", l2["text"] if l2 else "Unknown")
        extraction_prompt = extraction_prompt.replace("{{page_range}}", str(page_number))
        extraction_prompt = extraction_prompt.replace("{{prev_l3_title}}", "Start of section")

        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": extraction_prompt}
        ]

        try:
            response = await self.llm_service.call_llm(
                provider_name, messages, max_tokens=4096,
                temperature=0.1, images=[img]
            )

            # Parse but don't save
            is_valid, error = self.xml_parser.validate_xml(response["content"])
            parsed = None
            if is_valid:
                try:
                    parsed = self.xml_parser.parse_xml_response(response["content"])
                except Exception:
                    pass

            return {
                "raw_response": response["content"],
                "xml_valid": is_valid,
                "xml_error": error if not is_valid else None,
                "parsed": parsed,
                "input_tokens": response.get("input_tokens", 0),
                "output_tokens": response.get("output_tokens", 0),
                "cached_tokens": response.get("input_tokens_cached", 0),
                "processing_time_ms": response.get("processing_time_ms", 0),
                "provider": provider_name,
                "model": response.get("model", ""),
                "l1_title": l1["text"] if l1 else None,
                "l2_title": l2["text"] if l2 else None,
            }
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # Cost & Status Queries
    # =========================================================================

    def get_extraction_stats(self, book_id: int) -> Dict[str, Any]:
        """Get extraction statistics from the log table."""
        table_prefix = self._get_table_prefix(book_id)
        if not table_prefix:
            return {}

        log_table = f"v2_{table_prefix}_extraction_log"
        kp_table = f"v2_{table_prefix}_knowledge_pages"

        with engine.connect() as conn:
            # Log stats
            r = conn.execute(text(f"""
                SELECT COUNT(*) as total_calls,
                       SUM(input_tokens_uncached) as total_uncached,
                       SUM(input_tokens_cached) as total_cached,
                       SUM(output_tokens) as total_output,
                       SUM(cost_total) as total_cost,
                       SUM(processing_time_ms) as total_time,
                       COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                       COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
                FROM {log_table}
            """))
            log_stats = r.fetchone()

            # KP count
            r = conn.execute(text(f"SELECT COUNT(*) FROM {kp_table}"))
            kp_count = r.scalar()

        return {
            "knowledge_pages": kp_count,
            "total_api_calls": log_stats[0] or 0,
            "total_uncached_tokens": log_stats[1] or 0,
            "total_cached_tokens": log_stats[2] or 0,
            "total_output_tokens": log_stats[3] or 0,
            "total_cost": float(log_stats[4] or 0),
            "total_processing_time_ms": log_stats[5] or 0,
            "success_calls": log_stats[6] or 0,
            "failed_calls": log_stats[7] or 0,
            "cache_hit_rate": (float(log_stats[2] or 0) / max(float(log_stats[1] or 0) + float(log_stats[2] or 0), 1)) * 100
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_table_prefix(self, book_id: int) -> Optional[str]:
        """Get table prefix for a book."""
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT table_prefix FROM books_metadata WHERE book_id = :id"
            ), {"id": book_id})
            row = r.fetchone()
        return row[0] if row else None

    def _get_total_pages(self, book_id: int) -> int:
        """Get total pages for a book."""
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT total_pages FROM books_metadata WHERE book_id = :id"
            ), {"id": book_id})
            row = r.fetchone()
        return row[0] if row else 0
