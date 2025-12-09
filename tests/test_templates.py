"""Regression tests for template system."""
from pathlib import Path

import pytest

from chat_a_doc import server


@pytest.mark.asyncio
async def test_list_templates(allowed_root_env, create_valid_docx_template):
    """Test list-templates tool functionality."""
    # Create templates directory with test templates
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a valid DOCX template file for testing
    test_template = templates_dir / "test_template.docx"
    create_valid_docx_template(test_template)

    result = await server.handle_call_tool(
        "list-templates",
        {"format": "docx"}
    )

    assert len(result) > 0
    result_text = result[0].text

    # Verify template list response
    assert "templates" in result_text.lower() or "template" in result_text.lower()
    assert "Template path mapping" in result_text or "mapping" in result_text.lower()


@pytest.mark.asyncio
async def test_list_templates_no_templates(allowed_root_env):
    """Test list-templates when no templates exist."""
    # Ensure templates directory doesn't exist or is empty
    templates_dir = Path(allowed_root_env) / "templates"
    if templates_dir.exists():
        for file in templates_dir.glob("*.docx"):
            file.unlink()

    result = await server.handle_call_tool(
        "list-templates",
        {"format": "docx"}
    )

    assert len(result) > 0
    result_text = result[0].text

    # Should indicate no templates found
    assert "no" in result_text.lower() or "not found" in result_text.lower()


@pytest.mark.asyncio
async def test_docx_with_template(allowed_root_env, sample_markdown_simple, sample_title, create_valid_docx_template):
    """Test DOCX conversion with template (reference_doc)."""
    # Create a test template
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    test_template = templates_dir / "test_template.docx"
    # Create a valid DOCX template using python-docx
    create_valid_docx_template(test_template)

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "docx",
            "title": sample_title,
            "reference_doc": str(test_template),
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.docx"))
    assert len(output_files) > 0

    output_file = output_files[0]

    # Verify DOCX file was created
    assert output_file.exists()
    docx_content = output_file.read_bytes()
    assert docx_content.startswith(b"PK"), "File should be a valid DOCX"


@pytest.mark.asyncio
async def test_list_templates_pdf(allowed_root_env):
    """Test list-templates for PDF format (CSS templates)."""
    # Create templates directory with CSS templates
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create CSS template files
    css_template1 = templates_dir / "corporate.css"
    css_template1.write_text("body { font-family: Arial; }", encoding="utf-8")

    css_template2 = templates_dir / "modern.css"
    css_template2.write_text("body { font-family: 'Segoe UI'; }", encoding="utf-8")

    result = await server.handle_call_tool(
        "list-templates",
        {"format": "pdf"}
    )

    assert len(result) > 0
    result_text = result[0].text

    # Verify template list response contains CSS templates
    assert "pdf" in result_text.lower() or "template" in result_text.lower()
    assert "Template path mapping" in result_text or "mapping" in result_text.lower()
    assert "corporate.css" in result_text or "modern.css" in result_text


@pytest.mark.asyncio
async def test_list_templates_pdf_no_templates(allowed_root_env):
    """Test list-templates for PDF when no CSS templates exist."""
    # Ensure templates directory doesn't have CSS files
    templates_dir = Path(allowed_root_env) / "templates"
    if templates_dir.exists():
        for file in templates_dir.glob("*.css"):
            file.unlink()

    result = await server.handle_call_tool(
        "list-templates",
        {"format": "pdf"}
    )

    assert len(result) > 0
    result_text = result[0].text

    # Should indicate no templates found with PDF-specific message
    assert "no" in result_text.lower() or "not found" in result_text.lower()
    assert "default pdf styling" in result_text.lower() or "default styling" in result_text.lower()
    # Should NOT mention reference_doc (that's DOCX-specific)
    assert "reference_doc" not in result_text.lower()


@pytest.mark.asyncio
async def test_list_templates_docx_unchanged(allowed_root_env, create_valid_docx_template):
    """Regression test: Ensure DOCX template listing still works after PDF support."""
    # Create templates directory with DOCX template
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a DOCX template
    test_template = templates_dir / "test_template.docx"
    create_valid_docx_template(test_template)

    # Also create a CSS file to ensure it doesn't interfere
    css_template = templates_dir / "test.css"
    css_template.write_text("body { color: red; }", encoding="utf-8")

    result = await server.handle_call_tool(
        "list-templates",
        {"format": "docx"}
    )

    assert len(result) > 0
    result_text = result[0].text

    # Should only show DOCX templates, not CSS
    assert "test_template.docx" in result_text
    assert "test.css" not in result_text
    assert "Template path mapping" in result_text or "mapping" in result_text.lower()
