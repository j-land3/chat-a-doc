"""TXT generator from markdown content.

Uses python-markdown to convert markdown to HTML, then html2text to convert
HTML to plain text.
"""

import html2text
import markdown


def generate_txt(markdown_content: str, **options) -> str:
    """Generate plain text from markdown content.

    Args:
        markdown_content: Markdown content as string
        **options: Additional options (currently unused, reserved for future use)

    Returns:
        Plain text string

    Raises:
        ValueError: If markdown or text conversion fails

    """
    try:
        # Step 1: Convert markdown to HTML
        extensions = ["tables", "fenced_code", "nl2br"]
        html = markdown.markdown(markdown_content, extensions=extensions)

        # Step 2: Convert HTML to plain text
        h = html2text.HTML2Text()
        h.ignore_links = False  # Keep links in text
        h.ignore_images = True  # Remove images (just show alt text if available)
        h.body_width = 0  # Don't wrap lines
        text = h.handle(html)

        return text
    except Exception as e:
        raise ValueError(f"Failed to generate TXT from markdown: {e}") from e
