"""Document format generators.

This module provides simple functions to generate documents in various formats
from markdown content. Each generator is a standalone function following the
simple functions approach (no abstract base classes).

All generators accept markdown_content as the first parameter and return either
str (for text formats) or bytes (for binary formats).
"""

# Import generators that don't require system dependencies
from chat_a_doc.generators.generate_csv import generate_csv
from chat_a_doc.generators.generate_html import generate_html
from chat_a_doc.generators.generate_markdown import generate_markdown
from chat_a_doc.generators.generate_txt import generate_txt

# Import generators that may require system dependencies (lazy import)
# These are imported on-demand to avoid import errors if system deps are missing
__all__ = [
    "generate_csv",
    "generate_html",
    "generate_markdown",
    "generate_txt",
    "generate_docx",  # Available via lazy import
    "generate_pdf",  # Available via lazy import
]


def __getattr__(name: str):
    """Lazy import for generators that may require system dependencies."""
    if name == "generate_docx":
        from chat_a_doc.generators.generate_docx import generate_docx

        return generate_docx
    elif name == "generate_pdf":
        from chat_a_doc.generators.generate_pdf import generate_pdf

        return generate_pdf
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
