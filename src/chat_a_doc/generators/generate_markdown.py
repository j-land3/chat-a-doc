"""Markdown generator (pass-through).

Returns markdown content as-is, with optional normalization.
"""


def generate_markdown(markdown_content: str, **options) -> str:
    r"""Generate markdown from markdown content (pass-through).

    This is a pass-through function that returns the markdown content as-is.
    Optionally normalizes line endings for consistency.

    Args:
        markdown_content: Markdown content as string
        **options: Additional options
            - normalize_line_endings: If True, normalize line endings to \n (default: False)

    Returns:
        Markdown string (same as input, optionally normalized)

    Raises:
        ValueError: If markdown content is invalid (basic validation)

    """
    if not isinstance(markdown_content, str):
        raise ValueError("markdown_content must be a string")

    # Optional: normalize line endings
    normalize = options.get("normalize_line_endings", False)
    if normalize:
        # Normalize to Unix line endings
        content = markdown_content.replace("\r\n", "\n").replace("\r", "\n")
    else:
        content = markdown_content

    return content
