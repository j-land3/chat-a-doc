"""Template management utilities for listing and organizing document templates.

This module provides functions to discover, list, and format templates
for use in document generation (DOCX and PDF templates).
"""

import os
import string


def get_letter_label(idx: int) -> str:
    """Generate letter labels: A-Z, then AA, AB, AC, etc. (Excel-style).

    Args:
        idx: Zero-based index of the template.

    Returns:
        str: Letter label (A-Z for 0-25, AA-ZZ for 26-701, AAA-ZZZ for 702+, etc.)

    """
    if idx < 26:
        return string.ascii_uppercase[idx]
    elif idx < 26 + 26 * 26:  # 26-701: two-letter combinations (AA-ZZ)
        # For indices 26-701, use two-letter combinations
        adjusted_idx = idx - 26
        first_letter_idx = adjusted_idx // 26
        second_letter_idx = adjusted_idx % 26
        return string.ascii_uppercase[first_letter_idx] + string.ascii_uppercase[second_letter_idx]
    else:  # 702+: three-letter combinations (AAA-ZZZ)
        # For indices >= 702, use three-letter combinations
        adjusted_idx = idx - 26 - 26 * 26
        first_letter_idx = adjusted_idx // (26 * 26)
        second_letter_idx = (adjusted_idx // 26) % 26
        third_letter_idx = adjusted_idx % 26
        if first_letter_idx < 26:
            return (
                string.ascii_uppercase[first_letter_idx]
                + string.ascii_uppercase[second_letter_idx]
                + string.ascii_uppercase[third_letter_idx]
            )
        else:
            # Fallback: use numeric suffix for very large numbers (>18,278 templates)
            return f"T{idx + 1}"


def discover_templates(templates_dir: str, format_type: str = "docx") -> list[dict[str, str]]:
    """Discover templates in the templates directory.

    Args:
        templates_dir: Path to the templates directory.
        format_type: File extension to filter by (default: "docx").
                     For PDF templates, use "css" to find CSS files.

    Returns:
        list[dict[str, str]]: List of template dictionaries with 'name' and 'path' keys.

    """
    templates = []
    if os.path.exists(templates_dir):
        for filename in sorted(os.listdir(templates_dir)):  # Sort for consistent ordering
            if filename.endswith(f".{format_type}"):
                full_path = os.path.join(templates_dir, filename)
                # Only include files (not directories)
                if os.path.isfile(full_path):
                    templates.append({"name": filename, "path": full_path})
    return templates


def format_templates_list(templates: list[dict[str, str]]) -> tuple[str, dict[str, str]]:
    """Format templates into a lettered list and create a path mapping.

    Args:
        templates: List of template dictionaries with 'name' and 'path' keys.

    Returns:
        tuple[str, dict[str, str]]: A tuple of (formatted_list, template_mapping) where:
            - formatted_list: A newline-separated string of lettered template names
            - template_mapping: A dictionary mapping letters to full template paths

    """
    template_lines = []
    template_mapping = {}

    for idx, template in enumerate(templates):
        letter = get_letter_label(idx)
        template_lines.append(f"{letter}. {template['name']}")
        template_mapping[letter] = template["path"]

    formatted_list = "\n".join(template_lines)
    return formatted_list, template_mapping


def list_templates(
    allowed_root: str | None = None,
    format_type: str = "docx",
) -> tuple[list[dict[str, str]], str]:
    """List available templates for a given format.

    Args:
        allowed_root: The allowed root directory. If None, retrieved from ALLOWED_ROOT env var.
        format_type: The format type to list templates for (default: "docx").
                     For PDF templates, use "css" to find CSS files.

    Returns:
        tuple[list[dict[str, str]], str]: A tuple of (templates, templates_dir) where:
            - templates: List of template dictionaries with 'name' and 'path' keys
            - templates_dir: The path to the templates directory

    """
    if allowed_root is None:
        allowed_root = os.environ.get("ALLOWED_ROOT", "/app/files")

    templates_dir = os.path.join(allowed_root, "templates")

    # Map format_type to file extension for discovery
    # For PDF, we look for CSS files
    if format_type == "pdf":
        file_extension = "css"
    else:
        file_extension = format_type

    templates = discover_templates(templates_dir, file_extension)

    return templates, templates_dir
