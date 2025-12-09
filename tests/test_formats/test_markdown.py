"""Regression tests for MARKDOWN format conversion."""
from pathlib import Path

import pytest

from chat_a_doc import server
from tests.test_helpers import save_baseline_output


@pytest.mark.asyncio
async def test_markdown_simple(allowed_root_env, sample_markdown_simple, sample_title):
    """Test MARKDOWN conversion with simple markdown (pass-through)."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "markdown",
            "title": sample_title,
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.md"))
    assert len(output_files) > 0

    output_file = output_files[0]
    md_content = output_file.read_text(encoding="utf-8")

    # Verify markdown content (should be similar to input)
    assert "Simple Document" in md_content
    assert "#" in md_content  # Should have headers

    # Save as baseline
    save_baseline_output(output_file, md_content, "markdown")


@pytest.mark.asyncio
async def test_markdown_complex(allowed_root_env, sample_markdown_complex, sample_title):
    """Test MARKDOWN conversion with complex markdown."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_complex,
            "output_format": "markdown",
            "title": "Complex Test Document",
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.md"))
    assert len(output_files) > 0

    output_file = output_files[0]
    md_content = output_file.read_text(encoding="utf-8")

    # Verify markdown content
    assert "Complex Document" in md_content
    assert "**" in md_content or "*" in md_content  # Should have formatting
    assert "```" in md_content or "def hello" in md_content  # Code blocks

    # Save as baseline
    save_baseline_output(output_file, md_content, "markdown")
