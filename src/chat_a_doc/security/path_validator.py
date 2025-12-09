"""Path validation module for ensuring paths are within allowed directories.

This module provides security functions to validate that file paths are within
the ALLOWED_ROOT directory, preventing path traversal attacks.
"""

import os


def get_allowed_root() -> str:
    """Get and validate the ALLOWED_ROOT environment variable.

    Returns:
        str: The absolute, real path of the allowed root directory.

    Raises:
        ValueError: If ALLOWED_ROOT is not set or is invalid.

    """
    allowed_root = os.environ.get("ALLOWED_ROOT")
    if not allowed_root:
        raise ValueError(
            "ALLOWED_ROOT environment variable is required for security. "
            "Set it to the directory where files should be stored (e.g., /app/files). "
            "It must match the container path in your Docker volume mount."
        )

    return os.path.realpath(allowed_root)


def validate_path(path: str | None, path_name: str, allowed_root: str | None = None) -> None:
    """Validate that a path is within ALLOWED_ROOT.

    Args:
        path: The path to validate. If None or empty, validation is skipped.
        path_name: A descriptive name for the path (used in error messages).
        allowed_root: The allowed root directory. If None, retrieved from environment.

    Raises:
        ValueError: If the path is outside the allowed directory.

    """
    if not path:
        return

    if allowed_root is None:
        allowed_root = get_allowed_root()

    abs_path = os.path.realpath(os.path.abspath(path))
    # Security: Ensure path is either the allowed_root itself or a subdirectory/file within it
    # Using startswith() alone is vulnerable to sibling directory attacks (e.g., /app/files_sibling)
    # Must check for exact match or prefix with directory separator
    if abs_path != allowed_root and not abs_path.startswith(allowed_root + os.sep):
        raise ValueError(f"{path_name} path '{path}' is outside allowed directory '{allowed_root}'")


def validate_paths(
    input_file: str | None = None,
    output_file: str | None = None,
    reference_doc: str | None = None,
    template: str | None = None,
    defaults_file: str | None = None,
    filters: list[str] | None = None,
    allowed_root: str | None = None,
) -> None:
    """Validate multiple file paths are within ALLOWED_ROOT.

    Args:
        input_file: Optional input file path to validate.
        output_file: Optional output file path to validate.
        reference_doc: Reference document path to validate (required for DOCX generation).
        template: Template path to validate (required for PDF generation, CSS templates).
        defaults_file: Optional defaults file path to validate.
        filters: Optional list of filter paths to validate.
        allowed_root: The allowed root directory. If None, retrieved from environment.

    Raises:
        ValueError: If any path is outside the allowed directory.

    """
    if allowed_root is None:
        allowed_root = get_allowed_root()

    if input_file:
        validate_path(input_file, "input_file", allowed_root)
    if output_file:
        validate_path(output_file, "output_file", allowed_root)
    if reference_doc:
        validate_path(reference_doc, "reference_doc", allowed_root)
    if template:
        validate_path(template, "template", allowed_root)
    if defaults_file:
        validate_path(defaults_file, "defaults_file", allowed_root)
    if filters:
        for idx, filter_path in enumerate(filters):
            validate_path(filter_path, f"filter[{idx}]", allowed_root)
