"""Regression tests for security features."""
from pathlib import Path

import pytest

from chat_a_doc import server


@pytest.mark.asyncio
async def test_allowed_root_validation(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that paths outside ALLOWED_ROOT are rejected."""
    # Try to access a path outside ALLOWED_ROOT
    outside_path = "/tmp/outside_file.html"

    with pytest.raises(ValueError) as exc_info:
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "html",
                "title": sample_title,
                "output_file": outside_path,
            }
        )

    assert "outside allowed directory" in str(exc_info.value).lower() or "allowed_root" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_path_traversal_prevention(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that path traversal attacks are prevented."""
    # Try path traversal
    traversal_path = str(Path(allowed_root_env) / "../../etc/passwd.html")

    with pytest.raises(ValueError) as exc_info:
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "html",
                "title": sample_title,
                "output_file": traversal_path,
            }
        )

    # Should be rejected
    assert "outside allowed directory" in str(exc_info.value).lower() or "allowed_root" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_sibling_directory_attack_prevention(allowed_root_env, sample_markdown_simple, sample_title):
    """Test that sibling directory attacks are prevented (e.g., /app/files_sibling)."""
    from chat_a_doc.security.path_validator import validate_path

    allowed_root = allowed_root_env

    # Test sibling directory attack (should be rejected)
    # If allowed_root is /app/files, /app/files_sibling should be rejected
    sibling_path = str(Path(allowed_root).parent / f"{Path(allowed_root).name}_sibling" / "secret.txt")

    with pytest.raises(ValueError) as exc_info:
        validate_path(sibling_path, "test_path", allowed_root)

    # Should be rejected
    assert "outside allowed directory" in str(exc_info.value).lower() or "allowed_root" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_csv_formula_injection_protection(allowed_root_env, sample_title):
    """Test CSV formula injection protection.

    Validates that formula injection protection works with the current
    python-markdown based CSV conversion implementation.
    """
    # Content with potentially dangerous formulas
    dangerous_content = """# Test

| Formula | Value |
|---------|-------|
| =SUM(A1:A10) | 100 |
| +2+2 | 4 |
| -5 | -5 |
| @SUM | 10 |
"""

    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": dangerous_content,
            "output_format": "csv",
            "title": sample_title,
        }
    )

    assert len(result) > 0

    # Find the output file
    output_files = list(Path(allowed_root_env).glob("*.csv"))
    assert len(output_files) > 0

    output_file = output_files[0]
    csv_content = output_file.read_text(encoding="utf-8")

    # Check that dangerous cells are protected
    import csv as csv_module
    from io import StringIO

    # Parse CSV properly to handle quoted cells
    reader = csv_module.reader(StringIO(csv_content))
    rows = list(reader)

    if len(rows) > 1:  # Has header and data
        for row in rows[1:]:  # Skip header
            for cell in row:
                # Check BEFORE stripping - we need to verify the tab prefix is present
                # Protected cells will start with tab, so they won't start with =, +, -, @
                # If a cell starts with a dangerous character (after checking for tab), it's NOT protected
                if cell and cell.startswith("\t") and len(cell) > 1:
                    # Cell starts with tab - verify it's protecting a dangerous character
                    assert cell[1] in ('=', '+', '-', '@'), \
                        f"Cell '{cell}' starts with tab but doesn't protect a dangerous character"
                elif cell and cell[0] in ('=', '+', '-', '@'):
                    # This cell should have been protected - it should start with tab
                    assert False, \
                        f"Cell '{cell}' should be protected from formula injection with tab prefix. " \
                        f"Expected '\\t{cell[0]}...' but got '{cell}'"


@pytest.mark.asyncio
async def test_input_validation_missing_title(allowed_root_env, sample_markdown_simple):
    """Test that title parameter is required."""
    with pytest.raises(ValueError) as exc_info:
        await server.handle_call_tool(
            "convert-contents",
            {
                "contents": sample_markdown_simple,
                "output_format": "html",
                # title missing
            }
        )

    assert "title" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_input_validation_missing_contents(allowed_root_env, sample_title):
    """Test that contents or input_file is required."""
    with pytest.raises(ValueError) as exc_info:
        await server.handle_call_tool(
            "convert-contents",
            {
                "output_format": "html",
                "title": sample_title,
                # contents missing
            }
        )

    assert "contents" in str(exc_info.value).lower() or "input_file" in str(exc_info.value).lower()
