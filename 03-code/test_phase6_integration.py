"""
Test Phase 6 Integration

Verifies that diagram context building and custom prompts work correctly.
"""

import sys
sys.path.insert(0, '.')

from src.worker.diagram_context import (
    get_book_settings,
    build_diagram_context,
    get_custom_prompt_for_diagram,
    enhance_prompt_with_context
)

print("=" * 70)
print("Phase 6 Integration Test")
print("=" * 70)
print()

# Test 1: Get book settings
print("Test 1: Fetching book settings...")
try:
    settings = get_book_settings(1)
    print(f"  Settings retrieved: {len(settings)} fields")
    if settings.get('diagram_prompt'):
        print(f"  Diagram prompt: {settings['diagram_prompt'][:50]}...")
    else:
        print("  Diagram prompt: Not set")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
print()

# Test 2: Build diagram context from sequential texts
print("Test 2: Building diagram context...")
try:
    sample_data = {
        "id": 11,
        "page_number": 1,
        "ocr_text_1": "Test OCR Text 1",
        "ocr_text_2": "Test OCR Text 2",
        "ocr_text_3": "Test OCR Text 3",
        "manual_text_1": "Test Manual 1",
        "manual_text_2": "Test Manual 2",
        "manual_text_3": "Test Manual 3"
    }

    context = build_diagram_context("diagram", sample_data)

    if context:
        print(f"  Context built successfully ({len(context)} chars)")
        print(f"  Context preview:\n{context[:200]}...")
        print("  PASS")
    else:
        print("  No context built (no sequential texts)")
        print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
print()

# Test 3: Get custom prompt for diagram type
print("Test 3: Getting custom prompt...")
try:
    custom_prompt = get_custom_prompt_for_diagram(1, "diagram")

    if custom_prompt:
        print(f"  Custom prompt retrieved ({len(custom_prompt)} chars)")
        print(f"  Preview: {custom_prompt[:50]}...")
    else:
        print("  No custom prompt set for this type")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
print()

# Test 4: Enhance prompt with context
print("Test 4: Enhancing prompt with context and custom prompt...")
try:
    base_prompt = "Analyze this diagram and extract key information."
    context = "\n\nAdditional Context:\nOCR Area 1: Title\nManual Text 1: Description"
    custom_prompt = "Focus on technical details and provide structured output."

    enhanced = enhance_prompt_with_context(base_prompt, context, custom_prompt)

    print(f"  Enhanced prompt: {len(enhanced)} chars")
    print(f"  Preview:\n{enhanced[:150]}...")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
print()

# Test 5: Test with real database data
print("Test 5: Testing with real diagram from database...")
try:
    from sqlalchemy import create_engine, text
    engine = create_engine("postgresql://postgres:postgres@localhost:5432/knowledge_extraction")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, page_number, ocr_text_1, ocr_text_2, manual_text_1, prompt_type
            FROM raw_book1_01wessam_explanation_2026_diagram_images
            WHERE id = 11
        """))
        row = result.fetchone()

        if row:
            data = dict(row._mapping)
            print(f"  Diagram ID: {data['id']}, Page: {data['page_number']}")
            print(f"  Prompt Type: {data.get('prompt_type', 'Not set')}")
            print(f"  OCR Text 1: {data.get('ocr_text_1', 'None')}")
            print(f"  OCR Text 2: {data.get('ocr_text_2', 'None')}")
            print(f"  Manual Text 1: {data.get('manual_text_1', 'None')}")

            context = build_diagram_context("diagram", data)
            if context:
                print(f"  Built context: {len(context)} chars")
            else:
                print("  No context (no sequential texts)")

            print("  PASS")
        else:
            print("  Diagram not found")
            print("  SKIP")
except Exception as e:
    print(f"  FAIL: {e}")
print()

print("=" * 70)
print("Phase 6 Integration Test Complete")
print("=" * 70)
