"""Regression tests for HTML format conversion."""
import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from chat_a_doc import server
from tests.test_helpers import get_test_data_path, save_baseline_output


@pytest.mark.asyncio
async def test_html_simple(allowed_root_env, sample_markdown_simple, sample_title):
    """Test HTML conversion with simple markdown."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "html",
            "title": sample_title,
        }
    )

    # Extract file path from result
    assert len(result) > 0
    result_text = result[0].text
    assert "Generated File:" in result_text or "successfully converted" in result_text

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.html"))
    assert len(output_files) > 0

    output_file = output_files[0]
    html_content = output_file.read_text(encoding="utf-8")

    # Verify HTML content
    assert "<h1>" in html_content or "<h1" in html_content
    assert "Simple Document" in html_content

    # Save as baseline
    save_baseline_output(output_file, html_content, "html")


@pytest.mark.asyncio
async def test_html_complex(allowed_root_env, sample_markdown_complex, sample_title):
    """Test HTML conversion with complex markdown."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_complex,
            "output_format": "html",
            "title": "Complex Test Document",
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.html"))
    assert len(output_files) > 0

    output_file = output_files[0]
    html_content = output_file.read_text(encoding="utf-8")

    # Verify HTML contains expected elements
    assert "<h1>" in html_content or "<h1" in html_content
    assert "Complex Document" in html_content
    assert "<strong>" in html_content or "bold" in html_content.lower()
    assert "<ul>" in html_content or "<li>" in html_content  # Lists
    assert "<code>" in html_content or "def hello" in html_content  # Code blocks

    # Save as baseline
    save_baseline_output(output_file, html_content, "html")
