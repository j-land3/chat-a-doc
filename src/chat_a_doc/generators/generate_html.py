"""HTML generator from markdown content.

Uses python-markdown library to convert markdown to HTML.
"""

import markdown


def generate_html(markdown_content: str, **options) -> str:
    """Generate HTML from markdown content.

    Args:
        markdown_content: Markdown content as string
        **options: Additional options (currently unused, reserved for future use)

    Returns:
        HTML string

    Raises:
        ValueError: If markdown processing fails

    """
    try:
        # Configure markdown extensions
        # - tables: Support markdown tables
        # - fenced_code: Support fenced code blocks (```)
        # - nl2br: Convert newlines to <br> tags
        extensions = ["tables", "fenced_code", "nl2br"]

        # Convert markdown to HTML
        html = markdown.markdown(
            markdown_content,
            extensions=extensions,
        )

        return html
    except Exception as e:
        raise ValueError(f"Failed to generate HTML from markdown: {e}") from e
