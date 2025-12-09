"""Regression tests for TXT format conversion."""
from pathlib import Path

import pytest

from chat_a_doc import server
from tests.test_helpers import save_baseline_output


@pytest.mark.asyncio
async def test_txt_simple(allowed_root_env, sample_markdown_simple, sample_title):
    """Test TXT conversion with simple markdown."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "txt",
            "title": sample_title,
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.txt"))
    assert len(output_files) > 0

    output_file = output_files[0]
    txt_content = output_file.read_text(encoding="utf-8")

    # Verify TXT content (should be plain text, no HTML)
    assert "Simple Document" in txt_content
    assert "<" not in txt_content or txt_content.count("<") < 3  # Minimal HTML tags allowed

    # Save as baseline
    save_baseline_output(output_file, txt_content, "txt")


@pytest.mark.asyncio
async def test_txt_complex(allowed_root_env, sample_markdown_complex, sample_title):
    """Test TXT conversion with complex markdown."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_complex,
            "output_format": "txt",
            "title": "Complex Test Document",
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.txt"))
    assert len(output_files) > 0

    output_file = output_files[0]
    txt_content = output_file.read_text(encoding="utf-8")

    # Verify TXT content
    assert "Complex Document" in txt_content
    # Should contain text content but minimal formatting
    assert "bold" in txt_content.lower() or "italic" in txt_content.lower()

    # Save as baseline
    save_baseline_output(output_file, txt_content, "txt")
