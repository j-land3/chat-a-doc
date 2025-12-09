"""Pytest configuration and fixtures for chat-a-doc tests."""
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import server module
from chat_a_doc import server


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def allowed_root_env(temp_output_dir, monkeypatch):
    """Set ALLOWED_ROOT environment variable to temp directory."""
    monkeypatch.setenv("ALLOWED_ROOT", temp_output_dir)
    return temp_output_dir


@pytest.fixture
def sample_markdown_simple():
    """Return simple markdown content for testing."""
    return """# Simple Document

This is a simple markdown document with basic text.

It has multiple paragraphs.
"""


@pytest.fixture
def sample_markdown_complex():
    """Complex markdown content with various features."""
    return """# Complex Document

This document has **bold** and *italic* text.

## Section 1

- Item 1
- Item 2
- Item 3

### Subsection

1. Numbered item
2. Another numbered item

## Code Example

```python
def hello():
    print("Hello, World!")
```

## Link

Visit [Example](https://example.com) for more information.
"""


@pytest.fixture
def sample_markdown_tables():
    """Markdown content with tables for CSV testing."""
    return """# Table Document

## Comparison Table

| Feature | Option A | Option B |
|---------|----------|----------|
| Price   | $10      | $20      |
| Quality | High     | Medium   |
| Speed   | Fast     | Slow     |

## Another Table

| Name | Age | City |
|------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
"""


@pytest.fixture
def sample_markdown_edge_cases():
    """Markdown content with edge cases."""
    return """# Edge Cases

Empty line above.

## Special Characters

Text with special chars: !@#$%^&*()

## Empty Sections

## Very Long Line

This is a very long line that might cause issues with some converters
and needs to be tested to ensure proper handling of long lines without breaks.

## Unicode

Café, résumé, naïve, 中文, 日本語
"""


@pytest.fixture
def sample_title():
    """Sample document title for testing."""
    return "Test Document Title"


@pytest.fixture
def mcp_server():
    """Get the MCP server instance."""
    return server.server


@pytest.fixture
def create_valid_docx_template():
    """Create a valid DOCX template file for testing.

    Returns a function that creates a valid DOCX file at the specified path.
    """
    def _create_template(template_path: Path) -> Path:
        """Create a valid DOCX template at the given path.

        Args:
            template_path: Path where the DOCX template should be created

        Returns:
            Path to the created template file

        """
        try:
            from docx import Document

            # Create a minimal valid DOCX document
            doc = Document()
            # Add a paragraph to ensure the document has content
            doc.add_paragraph("Template Content")
            # Save to the specified path
            doc.save(str(template_path))
            return template_path
        except ImportError:
            # Fallback: If python-docx is not available, skip the test
            pytest.skip("python-docx not available for creating test templates")

    return _create_template


@pytest.fixture
def setup_reference_templates(allowed_root_env):
    """Copy reference templates from test_data/templates/ to runtime location.

    This fixture mirrors the user's ALLOWED_ROOT/templates/ structure by
    copying version-controlled templates from test_data/templates/ to the
    test's allowed_root_env/templates/ directory.

    Usage:
        def test_something(allowed_root_env, setup_reference_templates):
            # Templates from test_data/templates/ are now available
            # at {allowed_root_env}/templates/
    """
    source_templates_dir = Path(__file__).parent / "test_data" / "templates"
    runtime_templates_dir = Path(allowed_root_env) / "templates"

    # Create templates directory in runtime location
    runtime_templates_dir.mkdir(parents=True, exist_ok=True)

    # Copy reference templates if they exist
    if source_templates_dir.exists():
        for template_file in source_templates_dir.glob("*.docx"):
            shutil.copy(template_file, runtime_templates_dir / template_file.name)

    return runtime_templates_dir
