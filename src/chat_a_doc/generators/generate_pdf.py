"""PDF generator from markdown content.

Uses python-markdown to convert markdown to HTML, then WeasyPrint
to convert HTML to PDF.
"""

import markdown
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def generate_pdf(markdown_content: str, **options) -> bytes:
    """Generate PDF from markdown content.

    Args:
        markdown_content: Markdown content as string
        **options: Additional options
            - title: Document title (for metadata)
            - margin: Page margins in CSS format (default: "1in")
            - template_path: Required path to CSS template file

    Returns:
        PDF bytes

    Raises:
        ValueError: If PDF generation fails

    """
    try:
        # Step 1: Convert markdown to HTML
        extensions = ["tables", "fenced_code", "nl2br"]
        html_content = markdown.markdown(markdown_content, extensions=extensions)

        # Step 2: Wrap in HTML document structure
        title = options.get("title", "Document")
        template_path = options.get("template_path")

        if not template_path:
            raise ValueError("template_path is required for PDF generation")

        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
{html_content}
</body>
</html>
"""

        # Step 3: Convert HTML to PDF using WeasyPrint
        font_config = FontConfiguration()
        html_doc = HTML(string=full_html)

        # Load CSS template from file
        css_doc = CSS(filename=template_path, font_config=font_config)

        # Generate PDF
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc], font_config=font_config)

        return pdf_bytes

    except Exception as e:
        raise ValueError(f"Failed to generate PDF from markdown: {e}") from e
