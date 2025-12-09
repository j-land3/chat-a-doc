"""Regression tests for PDF format conversion."""

from pathlib import Path

import pytest

from chat_a_doc import server
from tests.test_helpers import save_baseline_output


@pytest.mark.asyncio
async def test_pdf_simple(allowed_root_env, sample_markdown_simple, sample_title):
    """Test PDF conversion with simple markdown."""
    # Create templates directory with CSS template (required)
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a CSS template
    css_template = templates_dir / "test_template.css"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "pdf",
            "title": sample_title,
            "template": str(css_template),
        },
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.pdf"))
    assert len(output_files) > 0

    output_file = output_files[0]

    # Verify PDF file exists and has content
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Verify PDF header (PDF files start with %PDF)
    pdf_content = output_file.read_bytes()
    assert pdf_content.startswith(b"%PDF"), "File should be a valid PDF"

    # Save as baseline
    save_baseline_output(output_file, pdf_content, "pdf")


@pytest.mark.asyncio
async def test_pdf_complex(allowed_root_env, sample_markdown_complex, sample_title):
    """Test PDF conversion with complex markdown."""
    # Create templates directory with CSS template (required)
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a CSS template
    css_template = templates_dir / "test_template.css"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_complex,
            "output_format": "pdf",
            "title": "Complex Test Document",
            "template": str(css_template),
        },
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.pdf"))
    assert len(output_files) > 0

    output_file = output_files[0]

    # Verify PDF file
    assert output_file.exists()
    pdf_content = output_file.read_bytes()
    assert pdf_content.startswith(b"%PDF"), "File should be a valid PDF"
    assert len(pdf_content) > 1000  # Complex document should be larger

    # Save as baseline
    save_baseline_output(output_file, pdf_content, "pdf")


@pytest.mark.asyncio
async def test_pdf_with_template(allowed_root_env, sample_markdown_simple, sample_title):
    """Test PDF conversion with CSS template."""
    # Create templates directory with CSS template
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a CSS template
    css_template = templates_dir / "test_template.css"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
        color: #333333;
    }
    h1 {
        color: #0066cc;
        font-size: 24pt;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "pdf",
            "title": sample_title,
            "template": str(css_template),
        },
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.pdf"))
    assert len(output_files) > 0

    output_file = output_files[0]

    # Verify PDF file was created
    assert output_file.exists()
    pdf_content = output_file.read_bytes()
    assert pdf_content.startswith(b"%PDF"), "File should be a valid PDF"
    assert output_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_pdf_template_missing_file(allowed_root_env, sample_markdown_simple, sample_title):
    """Test PDF conversion with non-existent template file."""
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    non_existent_template = templates_dir / "nonexistent.css"

    with pytest.raises(ValueError, match="Template file not found"):
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "pdf",
                "title": sample_title,
                "template": str(non_existent_template),
            },
        )


@pytest.mark.asyncio
async def test_pdf_template_wrong_extension(allowed_root_env, sample_markdown_simple, sample_title):
    """Test PDF conversion with template file that has wrong extension."""
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a file with wrong extension
    wrong_template = templates_dir / "template.txt"
    wrong_template.write_text("body { color: red; }", encoding="utf-8")

    with pytest.raises(ValueError, match="Template file must be a CSS file"):
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "pdf",
                "title": sample_title,
                "template": str(wrong_template),
            },
        )


@pytest.mark.asyncio
async def test_pdf_template_case_insensitive_extension(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that CSS template extension check is case-insensitive."""
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a CSS template with uppercase extension
    css_template = templates_dir / "template.CSS"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    # Should accept uppercase .CSS extension
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_simple,
            "output_format": "pdf",
            "title": sample_title,
            "template": str(css_template),
        },
    )

    assert len(result) > 0
    output_files = list(Path(allowed_root_env).glob("*.pdf"))
    assert len(output_files) > 0
    assert output_files[0].exists()


@pytest.mark.asyncio
async def test_pdf_template_required(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that template parameter is required for PDF format."""
    # Try to generate PDF without template (should fail)
    with pytest.raises(ValueError, match="template parameter is REQUIRED for pdf"):
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "pdf",
                "title": sample_title,
            },
        )


@pytest.mark.asyncio
async def test_pdf_template_wrong_format(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that template parameter is only accepted for PDF format."""
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    css_template = templates_dir / "test.css"
    css_template.write_text("body { color: red; }", encoding="utf-8")

    # Try to use template with HTML format (should fail)
    with pytest.raises(ValueError, match="template parameter is only supported for pdf"):
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "html",
                "title": sample_title,
                "template": str(css_template),
            },
        )
