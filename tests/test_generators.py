#!/usr/bin/env python3
"""Quick test script for generators before integration.

Tests each generator function with sample markdown content.
"""

import sys
from pathlib import Path

# Add src to path (go up one level from tests/ to project root, then into src)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import generators directly from modules to avoid import errors
from chat_a_doc.generators.generate_html import generate_html
from chat_a_doc.generators.generate_txt import generate_txt
from chat_a_doc.generators.generate_markdown import generate_markdown
from chat_a_doc.generators.generate_csv import generate_csv

# Try to import PDF and DOCX generators (may fail if system deps missing)
try:
    from chat_a_doc.generators.generate_pdf import generate_pdf
    PDF_AVAILABLE = True
except (ImportError, OSError) as e:
    PDF_AVAILABLE = False
    print(f"Note: PDF generator not available (system dependencies missing): {e}")

try:
    from chat_a_doc.generators.generate_docx import generate_docx
    DOCX_AVAILABLE = True
except (ImportError, OSError) as e:
    DOCX_AVAILABLE = False
    print(f"Note: DOCX generator not available: {e}")

# Sample markdown content
SAMPLE_MARKDOWN = """# Test Document

This is a **test** document with *formatting*.

## Section 1

- Item 1
- Item 2
- Item 3

### Code Example

```python
def hello():
    print("Hello, World!")
```

## Table

| Name | Age | City |
|------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
"""


def test_html():
    """Test HTML generator."""
    print("Testing HTML generator...")
    try:
        result = generate_html(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, str)
        assert "<h1>" in result or "<h1" in result
        assert "Test Document" in result
        # Save sample output
        output_path = Path(__file__).parent / "test_output" / "test_output.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"✓ HTML generator: PASSED (saved to {output_path})")
        return True
    except Exception as e:
        print(f"✗ HTML generator: FAILED - {e}")
        return False


def test_txt():
    """Test TXT generator."""
    print("Testing TXT generator...")
    try:
        result = generate_txt(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, str)
        assert "Test Document" in result
        # Should not have HTML tags (or minimal)
        assert result.count("<") < 5
        # Save sample output
        output_path = Path(__file__).parent / "test_output" / "test_output.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"✓ TXT generator: PASSED (saved to {output_path})")
        return True
    except Exception as e:
        print(f"✗ TXT generator: FAILED - {e}")
        return False


def test_markdown():
    """Test MARKDOWN generator."""
    print("Testing MARKDOWN generator...")
    try:
        result = generate_markdown(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, str)
        assert "Test Document" in result
        assert "#" in result
        print("✓ MARKDOWN generator: PASSED")
        return True
    except Exception as e:
        print(f"✗ MARKDOWN generator: FAILED - {e}")
        return False


def test_csv():
    """Test CSV generator."""
    print("Testing CSV generator...")
    try:
        result = generate_csv(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, str)
        assert "," in result
        assert "Name" in result or "Age" in result
        # Save sample output
        output_path = Path(__file__).parent / "test_output" / "test_output.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"✓ CSV generator: PASSED (saved to {output_path})")
        return True
    except Exception as e:
        print(f"✗ CSV generator: FAILED - {e}")
        return False


def test_pdf():
    """Test PDF generator."""
    if not PDF_AVAILABLE:
        print("Testing PDF generator...")
        print("⊘ PDF generator: SKIPPED (system dependencies not available)")
        return None  # Skip, don't count as pass/fail

    print("Testing PDF generator...")
    try:
        result = generate_pdf(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")
        print("✓ PDF generator: PASSED")
        return True
    except Exception as e:
        print(f"✗ PDF generator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_docx():
    """Test DOCX generator."""
    if not DOCX_AVAILABLE:
        print("Testing DOCX generator...")
        print("⊘ DOCX generator: SKIPPED (not available)")
        return None  # Skip, don't count as pass/fail

    print("Testing DOCX generator...")
    try:
        result = generate_docx(SAMPLE_MARKDOWN, title="Test Document")
        assert isinstance(result, bytes)
        assert result.startswith(b"PK")  # DOCX is a ZIP file
        # Save sample output
        output_path = Path(__file__).parent / "test_output" / "test_output.docx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result)
        print(f"✓ DOCX generator: PASSED (saved to {output_path})")
        return True
    except Exception as e:
        print(f"✗ DOCX generator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all generator tests."""
    print("=" * 60)
    print("Testing Generators")
    print("=" * 60)
    print()

    results = []
    results.append(("HTML", test_html()))
    results.append(("TXT", test_txt()))
    results.append(("MARKDOWN", test_markdown()))
    results.append(("CSV", test_csv()))
    results.append(("PDF", test_pdf()))
    results.append(("DOCX", test_docx()))

    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    # Count only non-None results (skipped tests return None)
    test_results = [(name, result) for name, result in results if result is not None]
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    skipped = len(results) - total

    for name, result in results:
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
        print(f"{name:12} {status}")

    print()
    if skipped > 0:
        print(f"Total: {passed}/{total} passed ({skipped} skipped)")
    else:
        print(f"Total: {passed}/{total} passed")

    if passed == total:
        print("✓ All generators working correctly!")
        return 0
    else:
        print("✗ Some generators failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
