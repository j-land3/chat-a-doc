"""CSV generator from markdown content.

Extracts tables from markdown and converts them to CSV format with
formula injection protection.
"""

import csv
import re
from io import StringIO

import markdown


def generate_csv(markdown_content: str, **options) -> str:
    """Generate CSV from markdown content.

    Extracts tables from markdown and converts them to CSV format.
    If no tables are found, attempts to parse structured text.
    Applies formula injection protection to all cells.

    Args:
        markdown_content: Markdown content as string
        **options: Additional options (currently unused, reserved for future use)

    Returns:
        CSV string

    Raises:
        ValueError: If no table data can be extracted or conversion fails

    """
    try:
        # Step 1: Convert markdown to HTML to extract tables
        extensions = ["tables", "fenced_code"]
        html = markdown.markdown(markdown_content, extensions=extensions)

        # Step 2: Extract tables from HTML
        table_data = extract_tables_from_html(html)

        if not table_data:
            # Step 3: Fallback to structured text parsing
            table_data = parse_structured_text(markdown_content)

        if not table_data or not any(table_data):
            raise ValueError("No table data found in input. CSV format requires structured data (tables).")

        # Step 4: Convert to CSV string with formula injection protection
        return convert_to_csv_string(table_data)

    except Exception as e:
        raise ValueError(f"Failed to generate CSV from markdown: {e}") from e


def extract_tables_from_html(html: str) -> list[list[str]] | None:
    """Extract table data from HTML.

    Parses HTML tables and extracts rows and cells.
    Returns the first table found, or None if no tables.

    Args:
        html: HTML string containing tables

    Returns:
        List of rows, where each row is a list of cell values, or None

    """
    # Simple regex-based HTML table parser
    # This handles basic HTML tables without requiring BeautifulSoup

    # Find all table elements
    table_pattern = r"<table[^>]*>(.*?)</table>"
    tables = re.findall(table_pattern, html, re.DOTALL | re.IGNORECASE)

    if not tables:
        return None

    # Use the first table
    table_html = tables[0]

    rows = []

    # Extract rows (handle both <tr> and <tbody><tr>)
    row_pattern = r"<tr[^>]*>(.*?)</tr>"
    row_matches = re.findall(row_pattern, table_html, re.DOTALL | re.IGNORECASE)

    for row_html in row_matches:
        # Extract cells (handle both <td> and <th>)
        cell_pattern = r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>"
        cell_matches = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)

        if cell_matches:
            # Clean HTML from cells (remove tags, decode entities)
            cells = [clean_html_cell(cell) for cell in cell_matches]
            rows.append(cells)

    return rows if rows else None


def clean_html_cell(html_cell: str) -> str:
    """Clean HTML content from a table cell.

    Removes HTML tags and decodes common HTML entities.

    Args:
        html_cell: HTML string containing cell content

    Returns:
        Plain text content

    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html_cell)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    # Clean up whitespace
    text = " ".join(text.split())

    return text.strip()


def parse_structured_text(content: str) -> list[list[str]] | None:
    """Parse structured text (key-value, delimited) to table format.

    This handles cases where content doesn't contain formal markdown tables
    but has structured data in other formats.

    Args:
        content: Text content to parse

    Returns:
        List of rows, where each row is a list of cell values, or None

    """
    lines = content.split("\n")
    rows = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip markdown table separators
        if re.match(r"^[\s\|:\-]+$", line):
            continue

        # Try various separators
        if ":" in line and line.count(":") == 1 and not line.startswith("http"):
            # Key-value pair
            key, value = line.split(":", 1)
            rows.append([key.strip(), value.strip()])
        elif "\t" in line:
            # Tab-separated
            cells = [cell.strip() for cell in line.split("\t")]
            if cells:
                rows.append(cells)
        elif "|" in line and line.count("|") > 1:
            # Pipe-separated (skip markdown table separators already handled above)
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if cells:
                rows.append(cells)
        elif "," in line and not line.startswith("="):
            # Comma-separated (be careful - might be part of text)
            # Only split if it looks like structured data
            if line.count(",") >= 2 or (line.count(",") == 1 and " " not in line.replace(",", "")):
                cells = [cell.strip() for cell in line.split(",")]
                if cells:
                    rows.append(cells)
        else:
            # Single column
            rows.append([line])

    return rows if rows else None


def convert_to_csv_string(rows: list[list[str]]) -> str:
    """Convert table rows to CSV string with formula injection protection.

    Args:
        rows: List of rows, where each row is a list of cell values

    Returns:
        CSV string with formula injection protection applied

    """
    # Characters that can trigger formula injection in Excel/Google Sheets
    dangerous_prefixes = ("=", "+", "-", "@")

    def sanitize_cell(cell_value: str) -> str:
        """Sanitize a cell value to prevent formula injection."""
        if not isinstance(cell_value, str):
            cell_value = str(cell_value)

        # Check if cell starts with a dangerous character
        if cell_value and cell_value[0] in dangerous_prefixes:
            # Prefix with tab character to prevent formula interpretation
            # Tab is invisible in most CSV viewers but prevents formula execution
            return "\t" + cell_value

        return cell_value

    # Sanitize all cells
    sanitized_rows = []
    for row in rows:
        sanitized_row = [sanitize_cell(cell) for cell in row]
        sanitized_rows.append(sanitized_row)

    # Write to CSV string
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(sanitized_rows)

    return output.getvalue()
