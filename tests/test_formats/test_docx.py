"""Regression tests for DOCX format conversion."""
from pathlib import Path

import pytest

from chat_a_doc import server
from tests.test_helpers import save_baseline_output


@pytest.mark.asyncio
async def test_docx_simple(allowed_root_env, sample_markdown_simple, sample_title, create_valid_docx_template):
    """Test DOCX conversion with simple markdown."""
    # Create a test template
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    test_template = templates_dir / "test_template.docx"
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

    # Verify DOCX file exists and has content
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Verify DOCX file signature (DOCX is a ZIP file, starts with PK)
    docx_content = output_file.read_bytes()
    assert docx_content.startswith(b"PK"), "File should be a valid DOCX (ZIP format)"

    # Save as baseline
    save_baseline_output(output_file, docx_content, "docx")


@pytest.mark.asyncio
async def test_docx_complex(allowed_root_env, sample_markdown_complex, sample_title, create_valid_docx_template):
    """Test DOCX conversion with complex markdown."""
    # Create a test template
    templates_dir = Path(allowed_root_env) / "templates"
    templates_dir.mkdir(exist_ok=True)

    test_template = templates_dir / "test_template.docx"
    create_valid_docx_template(test_template)

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_complex,
            "output_format": "docx",
            "title": "Complex Test Document",
            "reference_doc": str(test_template),
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.docx"))
    assert len(output_files) > 0

    output_file = output_files[0]

    # Verify DOCX file
    assert output_file.exists()
    docx_content = output_file.read_bytes()
    assert docx_content.startswith(b"PK"), "File should be a valid DOCX"
    assert len(docx_content) > 5000  # Complex document should be larger

    # Save as baseline
    save_baseline_output(output_file, docx_content, "docx")
