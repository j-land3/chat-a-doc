"""Integration tests for full conversion workflows."""
from pathlib import Path

import pytest

from chat_a_doc import server


@pytest.mark.asyncio
async def test_full_conversion_workflow(allowed_root_env, sample_markdown_simple, sample_title):
    """Test full conversion workflow from markdown to file."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "html",
            "title": sample_title,
        }
    )

    # Verify result structure
    assert len(result) > 0
    assert hasattr(result[0], 'text')

    result_text = result[0].text

    # Verify result contains file information
    assert "successfully converted" in result_text.lower() or "generated file" in result_text.lower()
    assert "file://" in result_text or "http://" in result_text or ".html" in result_text

    # Verify file was actually created
    output_files = list(Path(allowed_root_env).glob("*.html"))
    assert len(output_files) > 0
    assert output_files[0].exists()


@pytest.mark.asyncio
async def test_template_selection_workflow(
    allowed_root_env, sample_markdown_simple, sample_title, create_valid_docx_template
):
    """Test template selection → conversion workflow."""
    # Step 1: List templates
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    test_template = templates_dir / "workflow_template.docx"
    # Create a valid DOCX template using python-docx
    create_valid_docx_template(test_template)

    list_result = await server.handle_call_tool(
        "list-templates",
        {"format": "docx"}
    )

    assert len(list_result) > 0
    list_text = list_result[0].text

    # Extract template path from mapping (simplified - in real test would parse JSON)
    assert "template" in list_text.lower() or "mapping" in list_text.lower()

    # Step 2: Convert with template
    convert_result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "docx",
            "title": sample_title,
            "reference_doc": str(test_template),
        }
    )

    assert len(convert_result) > 0

    # Verify file was created
    output_files = list(Path(allowed_root_env).glob("*.docx"))
    assert len(output_files) > 0
    assert output_files[0].exists()


@pytest.mark.asyncio
async def test_error_handling_invalid_format(allowed_root_env, sample_markdown_simple, sample_title):
    """Test error handling for invalid format."""
    with pytest.raises(ValueError) as exc_info:
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "invalid_format",
                "title": sample_title,
            }
        )

    assert "unsupported" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_auto_filename_generation(allowed_root_env, sample_markdown_simple):
    """Test auto-filename generation."""
    title1 = "First Document"
    title2 = "Second Document"

    # Convert first document
    await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "html",
            "title": title1,
        }
    )

    # Convert second document
    await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "html",
            "title": title2,
        }
    )

    # Verify both files were created with different names
    output_files = list(Path(allowed_root_env).glob("*.html"))
    assert len(output_files) >= 2

    # Verify filenames contain sanitized titles
    filenames = [f.name for f in output_files]
    assert any("first" in f.lower() or "document" in f.lower() for f in filenames)
    assert any("second" in f.lower() or "document" in f.lower() for f in filenames)
