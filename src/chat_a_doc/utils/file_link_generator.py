"""File link generation utilities for creating accessible file links.

This module provides functions to generate file links in various formats
(HTTP, file://) based on configuration and environment variables.
"""

import os


def generate_file_link(
    output_file: str,
    allowed_root: str,
    link_root: str | None = None,
    use_http_links: bool | None = None,
    http_base_url: str | None = None,
) -> tuple[str, str]:
    """Generate a file link and display path for a generated file.

    The function supports multiple link formats:
    - HTTP links: When HTTP server is available (USE_HTTP_LINKS=true)
    - file:// links: When LINK_ROOT is configured for path mapping
    - Internal file:// links: Fallback when no mapping is configured

    Args:
        output_file: Full path to the generated file.
        allowed_root: The allowed root directory (for path mapping).
        link_root: External root path for file:// link mapping (from LINK_ROOT env var).
        use_http_links: Whether to use HTTP links (from USE_HTTP_LINKS env var).
        http_base_url: Base URL for HTTP links (from HTTP_BASE_URL env var).

    Returns:
        tuple[str, str]: A tuple of (file_link, file_path) where:
            - file_link: The full link (HTTP or file://)
            - file_path: The display path (without file:// prefix)

    """
    # Get configuration from environment if not provided
    if link_root is None:
        link_root = os.environ.get("LINK_ROOT", "")
    if use_http_links is None:
        # Auto-detect: if HTTP_PORT is set, we're likely running HTTP server mode
        # Users can override with USE_HTTP_LINKS env var if needed
        http_port = os.environ.get("HTTP_PORT")
        explicit_setting = os.environ.get("USE_HTTP_LINKS", "").lower()
        if explicit_setting in ("true", "false"):
            use_http_links = explicit_setting == "true"
        elif http_port:
            # HTTP server mode detected, default to HTTP links
            use_http_links = True
        else:
            # Stdio mode or no HTTP server, default to file:// links
            use_http_links = False
    if http_base_url is None:
        # Default to localhost with HTTP_PORT if set, otherwise use default port 8080
        http_port = os.environ.get("HTTP_PORT", "8080")
        http_base_url = os.environ.get("HTTP_BASE_URL", f"http://localhost:{http_port}")

    if use_http_links:
        # Use HTTP link for clickable links in MSTY
        filename = os.path.basename(output_file)
        file_link = f"{http_base_url}/files/{filename}"
        file_path = file_link
    elif link_root:
        # Convert internal path to external path for the link
        internal_path_abs = os.path.realpath(output_file)
        internal_root_abs = os.path.realpath(allowed_root)
        # Security: Ensure path is either the allowed_root itself or a subdirectory/file within it
        # Using startswith() alone is vulnerable to sibling directory attacks (e.g., /app/files_sibling)
        # Must check for exact match or prefix with directory separator
        if internal_path_abs == internal_root_abs or internal_path_abs.startswith(internal_root_abs + os.sep):
            relative_path = os.path.relpath(internal_path_abs, internal_root_abs)
            external_path = os.path.join(link_root, relative_path).replace("\\", "/")
            file_link = f"file://{external_path}"
        else:
            # Fallback to internal path if outside root
            file_link = f"file://{output_file}"
        # Extract path for display
        file_path = file_link.replace("file://", "")
    else:
        # No link mapping configured, use internal path
        file_link = f"file://{output_file}"
        file_path = file_link.replace("file://", "")

    return file_link, file_path
