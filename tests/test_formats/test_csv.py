"""Regression tests for CSV format conversion."""
from pathlib import Path

import pytest

from chat_a_doc import server
from tests.test_helpers import get_test_data_path, save_baseline_output


@pytest.mark.asyncio
async def test_csv_tables(allowed_root_env, sample_markdown_tables, sample_title):
    """Test CSV conversion with markdown tables."""
    result = await server.handle_call_tool(
        "convert-contents",
        {
            "contents": sample_markdown_tables,
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

    # Verify CSV content
    assert "," in csv_content  # Should have commas
    assert "Feature" in csv_content or "Name" in csv_content  # Should have headers
    assert "\n" in csv_content  # Should have multiple rows

    # Verify formula injection protection
    # The protection adds a tab character prefix to cells starting with =, +, -, @

    # Save as baseline
    save_baseline_output(output_file, csv_content, "csv")


@pytest.mark.asyncio
async def test_csv_formula_injection_protection(allowed_root_env, sample_title):
    """Test CSV formula injection protection.

    Validates that formula injection protection works with the current
    python-markdown based CSV conversion implementation.
    """
    # Create markdown with potentially dangerous CSV content
    dangerous_content = """# Test Document

| Formula | Value |
|---------|-------|
| =1+1    | 2     |
| +2+2    | 4     |
| -3      | -3    |
| @SUM    | 10    |
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

    # Verify formula injection protection
    # Cells starting with =, +, -, @ should be prefixed with tab character
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
                        f"Cell '{cell}' should be protected with tab prefix. " \
                        f"Expected '\\t{cell[0]}...' but got '{cell}'"

    # Save as baseline
    save_baseline_output(output_file, csv_content, "csv")
