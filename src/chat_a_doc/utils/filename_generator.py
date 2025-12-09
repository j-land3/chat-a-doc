"""Filename generation utilities for auto-generating output filenames.

This module provides functions to generate safe, unique filenames based on
document titles and output formats.
"""

import os
import re


def sanitize_title(title: str, max_length: int = 50) -> str:
    """Sanitize a document title for use in filenames.

    Args:
        title: The document title to sanitize.
        max_length: Maximum length for the sanitized title (default: 50).

    Returns:
        str: A sanitized title safe for filesystem use. Returns "document" if
            sanitization results in an empty string.

    """
    # Remove special characters
    sanitized = re.sub(r"[^a-zA-Z0-9\s-]", "", title)
    # Replace spaces and dashes with underscores
    sanitized = re.sub(r"[\s-]+", "_", sanitized)
    # Lowercase and trim underscores
    sanitized = sanitized.lower().strip("_")
    # Handle empty result (e.g., title was only special characters)
    if not sanitized:
        sanitized = "document"
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def normalize_file_extension(output_format: str) -> str:
    """Normalize output format to a standard file extension.

    Args:
        output_format: The output format (e.g., 'markdown', 'txt', 'html').

    Returns:
        str: The normalized file extension (e.g., 'md', 'txt', 'html').

    """
    if output_format in ("markdown", "md"):
        return "md"
    elif output_format in ("txt", "text"):
        return "txt"
    else:
        return output_format


def generate_filename(
    title: str,
    output_format: str,
    output_dir: str,
    max_sequence: int = 99,
) -> str:
    """Generate a unique filename based on title and output format.

    The function creates a filename by:
    1. Sanitizing the title
    2. Normalizing the file extension
    3. Finding the next available sequence number (00-99)

    Args:
        title: Document title (will be sanitized).
        output_format: Output format (e.g., 'html', 'pdf', 'docx').
        output_dir: Directory where the file will be saved.
        max_sequence: Maximum sequence number to try (default: 99).

    Returns:
        str: Full path to the generated filename.

    Raises:
        OSError: If the output directory cannot be created.

    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Sanitize title and normalize extension
    sanitized_title = sanitize_title(title)
    file_extension = normalize_file_extension(output_format)

    # Find next available sequence number
    base_filename = sanitized_title
    for sequence in range(max_sequence + 1):
        sequence_str = f"{sequence:02d}"  # Format as 00, 01, 02, etc.
        candidate_filename = f"{base_filename}_{sequence_str}.{file_extension}"
        candidate_path = os.path.join(output_dir, candidate_filename)

        if not os.path.exists(candidate_path):
            return candidate_path

    # If we've exhausted all sequence numbers, wrap around to 00
    # (This is very unlikely but handles edge cases)
    sequence_str = "00"
    default_filename = f"{base_filename}_{sequence_str}.{file_extension}"
    return os.path.join(output_dir, default_filename)
