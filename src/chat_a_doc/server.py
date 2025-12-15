"""chat-a-doc server module.

MCP server for generating documents in multiple formats (PDF, DOCX, HTML, TXT, CSV, MARKDOWN)
from markdown content. Uses lightweight, purpose-built generators.

**Current Flow:**
- convert-contents tool → generator function → output file

**Supported Formats:**
- HTML: python-markdown
- TXT: python-markdown + html2text
- MARKDOWN: pass-through
- CSV: python-markdown (table extraction)
- PDF: python-markdown + WeasyPrint
- DOCX: python-markdown + python-docx (with template support)
"""

import json
import os
import sys
import time
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Import generators (lazy import for PDF/DOCX to handle missing system deps gracefully)
from chat_a_doc.generators import (
    generate_csv,
    generate_html,
    generate_markdown,
    generate_txt,
)

# Import utility modules
from chat_a_doc.security.path_validator import get_allowed_root, validate_paths
from chat_a_doc.templates.template_manager import format_templates_list, list_templates
from chat_a_doc.utils.file_link_generator import generate_file_link
from chat_a_doc.utils.filename_generator import generate_filename

server = Server("chat-a-doc")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools.

    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="convert-contents",
            description=(
                "Converts content to document formats and saves files.\n\n"
                "Required parameters:\n"
                "- contents: Document content as string (or use input_file)\n"
                "- output_format: html, markdown, pdf, docx, txt, csv\n"
                "- title: 2-4 word descriptive title (used for filename generation)\n\n"
                "CRITICAL FOR DOCX AND PDF: Templates are REQUIRED for both formats. You MUST follow this workflow:\n"
                "1. Call 'list-templates' tool with format='docx' or format='pdf' to get ACTUAL templates\n"
                "   DO NOT use example template names - you MUST call the tool!\n"
                "2. The response includes a 'Template path mapping' JSON object with the REAL templates\n"
                "   Example format (NOT actual): "
                '{"A": "/app/files/templates/corporate.docx", "B": "/app/files/templates/default.docx"}\n'
                "3. Present the lettered list (A, B, C...) from the list-templates response to the user\n"
                '4. Get the user\'s letter choice (e.g., "A")\n'
                "5. Look up the full path from the mapping JSON using the letter key\n"
                "6. For DOCX: Use that exact path in the 'reference_doc' parameter\n"
                "   For PDF: Use that exact path in the 'template' parameter\n"
                "NEVER guess template names - ALWAYS call list-templates first!\n\n"
                "Format aliases: 'Word document'/'MS Word' → 'docx', "
                "'text'/'plain text' → 'txt', 'spreadsheet'/'CSV' → 'csv'\n\n"
                "Files auto-saved to /app/files with title-based filenames.\n\n"
                "IMPORTANT: Always include the file link from the tool response in your reply to the user."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "contents": {
                        "type": "string",
                        "description": "The content to be converted (required if input_file not provided)",
                    },
                    "input_file": {
                        "type": "string",
                        "description": (
                            "Complete path to input file including filename and extension (e.g., '/path/to/input.md')"
                        ),
                    },
                    "input_format": {
                        "type": "string",
                        "description": "Source format of the content (defaults to markdown)",
                        "default": "markdown",
                        "enum": [
                            "html",
                            "markdown",
                            "pdf",
                            "docx",
                            "txt",
                            "csv",
                        ],
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Desired output format (defaults to markdown)",
                        "default": "markdown",
                        "enum": [
                            "html",
                            "markdown",
                            "pdf",
                            "docx",
                            "txt",
                            "csv",
                        ],
                    },
                    "output_file": {
                        "type": "string",
                        "description": (
                            "Complete path where to save the output including filename and extension. "
                            "If not provided, a file will be automatically created in the default output directory "
                            "with a timestamped filename (e.g., /app/files/output_20241123_123456_abc12345.html)"
                        ),
                    },
                    "reference_doc": {
                        "type": "string",
                        "description": (
                            "REQUIRED for docx output: Full path to Word template file (.docx) for styling. "
                            "This must be the EXACT path from the 'Template path mapping' JSON "
                            "returned by the list-templates tool call with format='docx'. "
                            "Workflow: (1) Call list-templates with format='docx' to get ACTUAL templates, "
                            "(2) Get mapping JSON from the response, "
                            "(3) Present lettered list to user, (4) Get user's letter choice, "
                            "(5) Look up path from mapping using the letter as key, "
                            "(6) Use that EXACT path here. "
                            "Example format (NOT actual path): If mapping shows "
                            '{"A": "/app/files/templates/corporate.docx"} '
                            'and user chooses "A", use "/app/files/templates/corporate.docx" here. '
                            "Do not use the letter itself or guess paths - you MUST call list-templates first "
                            "and use the actual path from the response."
                        ),
                    },
                    "template": {
                        "type": "string",
                        "description": (
                            "REQUIRED for pdf output: Full path to CSS template file (.css) for styling. "
                            "This must be the EXACT path from the 'Template path mapping' JSON "
                            "returned by the list-templates tool call with format='pdf'. "
                            "Workflow: (1) Call list-templates with format='pdf' to get ACTUAL CSS templates, "
                            "(2) Get mapping JSON from the response, "
                            "(3) Present lettered list to user, (4) Get user's letter choice, "
                            "(5) Look up path from mapping using the letter as key, "
                            "(6) Use that EXACT path here. "
                            "Example format (NOT actual path): If mapping shows "
                            '{"A": "/app/files/templates/corporate.css"} '
                            'and user chooses "A", use "/app/files/templates/corporate.css" here. '
                            "Do not use the letter itself or guess paths - you MUST call list-templates first "
                            "and use the actual path from the response."
                        ),
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "DEPRECATED: Filter support has been removed. This parameter is accepted but ignored."
                        ),
                    },
                    "defaults_file": {
                        "type": "string",
                        "description": (
                            "DEPRECATED: Defaults file support has been removed. "
                            "This parameter is accepted but ignored."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "REQUIRED: Document title (2-4 words recommended). "
                            "This will be used to generate a meaningful filename. "
                            "The title will be sanitized for filesystem compatibility."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="list-templates",
            description=(
                "Lists templates in /app/files/templates/ with letters (A, B, C...). "
                "REQUIRED for both Word documents (docx) and PDF documents.\n\n"
                "The response includes:\n"
                "- A lettered list of templates (A. template1.docx, B. template2.docx, etc.)\n"
                "- A 'Template path mapping' JSON object mapping letters to full file paths\n\n"
                "Workflow (applies to both DOCX and PDF):\n"
                "1. Call this tool with format='docx' or format='pdf' when user requests that format\n"
                "2. Extract the lettered list and mapping JSON from the response\n"
                "3. Present the lettered list to user: "
                "'Which template would you like? A. template1.docx, B. template2.docx...'\n"
                "4. Wait for user's letter choice (e.g., 'A' or 'template1')\n"
                "5. Look up the full path from the mapping JSON using the letter as the key\n"
                "6. For DOCX: Use that exact path in the 'reference_doc' parameter of convert-contents\n"
                "   For PDF: Use that exact path in the 'template' parameter of convert-contents\n\n"
                "Do not skip this step - template selection is required for both DOCX and PDF."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "The output format to list templates for ('docx' or 'pdf')",
                        "default": "docx",
                        "enum": ["docx", "pdf"],
                    }
                },
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests.

    Tools can modify server state and notify clients of changes.
    """
    if name not in ["convert-contents", "list-templates"]:
        raise ValueError(f"Unknown tool: {name}")

    # Handle list-templates tool
    if name == "list-templates":
        format_type = arguments.get("format", "docx") if arguments else "docx"

        # Validate format_type
        if format_type not in ["docx", "pdf"]:
            raise ValueError(
                f"Unsupported format for list-templates: '{format_type}'. Supported formats: 'docx', 'pdf'"
            )

        templates, templates_dir = list_templates(format_type=format_type)

        if templates:
            formatted_list, template_mapping = format_templates_list(templates)

            # Create mapping JSON for the model to use
            mapping_json = json.dumps(template_mapping, indent=2)

            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Available {format_type.upper()} templates in {templates_dir}:\n\n"
                        f"{formatted_list}\n\n"
                        f"Please choose the letter next to the template you want to use.\n\n"
                        f"Template path mapping (for reference):\n{mapping_json}"
                    ),
                )
            ]
        else:
            # Format-specific messaging for empty templates
            if format_type == "pdf":
                message = (
                    f"No {format_type.upper()} templates found in {templates_dir}.\n"
                    f"The system will use default PDF styling if no template is specified."
                )
            else:
                message = (
                    f"No {format_type.upper()} templates found in {templates_dir}.\n"
                    f"The system will use the default template if no reference_doc is specified."
                )
            return [
                types.TextContent(
                    type="text",
                    text=message,
                )
            ]

    # Continue with convert-contents tool
    if not arguments:
        raise ValueError("Missing arguments")

    # Extract all possible arguments
    contents = arguments.get("contents")
    # Note: input_file and input_format are deprecated - always use markdown content
    # Keeping for backward compatibility during transition, but will be removed
    input_file = arguments.get("input_file")
    output_file = arguments.get("output_file")
    output_format = arguments.get("output_format", "markdown").lower()
    # input_format is deprecated (always markdown), but kept for API compatibility
    _ = arguments.get("input_format", "markdown")  # noqa: F841
    reference_doc = arguments.get("reference_doc")
    template = arguments.get("template")  # For PDF CSS templates
    filters = arguments.get("filters", [])  # Deprecated, filter support removed
    defaults_file = arguments.get("defaults_file")  # Deprecated, defaults file support removed
    title = arguments.get("title")

    # Validate required parameters
    if not title:
        raise ValueError("title parameter is required. Please provide a 2-4 word document title.")

    # Warn about deprecated parameters
    if input_file:
        print(
            "Warning: input_file parameter is deprecated. Always provide markdown content via 'contents' parameter.",
            file=sys.stderr,
        )
    if "filters" in arguments:
        print("Warning: filters parameter is deprecated. Filter support has been removed.", file=sys.stderr)
    if defaults_file:
        print(
            "Warning: defaults_file parameter is deprecated. Defaults file support has been removed.", file=sys.stderr
        )

    # Auto-generate output_file if not provided (do this before validation)
    if not output_file:
        # Get the default output directory
        default_allowed_root = os.environ.get("ALLOWED_ROOT", "/app/files")
        # #region agent log
        print(f"[DEBUG] ALLOWED_ROOT={default_allowed_root}, title={title}, format={output_format}", file=sys.stderr)
        try:
            log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "server.py:319",
                "message": "ALLOWED_ROOT env var",
                "data": {"ALLOWED_ROOT": default_allowed_root, "title": title, "output_format": output_format},
                "timestamp": int(time.time() * 1000),
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception:  # noqa: S110 (intentionally broad for debug logging)
            pass
        # #endregion
        output_file = generate_filename(
            title=title,
            output_format=output_format,
            output_dir=default_allowed_root,
        )
        # #region agent log
        print(f"[DEBUG] Generated output_file path: {output_file}", file=sys.stderr)
        try:
            log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "server.py:325",
                "message": "Generated output_file path",
                "data": {"output_file": output_file, "output_dir": default_allowed_root},
                "timestamp": int(time.time() * 1000),
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception:  # noqa: S110 (intentionally broad for debug logging)
            pass
        # #endregion

    # Security: Validate paths are within ALLOWED_ROOT (REQUIRED)
    # This MUST happen before any file operations to prevent path traversal attacks
    try:
        allowed_root = get_allowed_root()
        # #region agent log
        exists = os.path.exists(allowed_root)
        isdir = os.path.isdir(allowed_root) if exists else False
        print(
            f"[DEBUG] get_allowed_root() returned: {allowed_root}, exists: {exists}, isdir: {isdir}",
            file=sys.stderr,
        )
        # #endregion
    except Exception as e:
        # #region agent log
        print(f"[DEBUG] get_allowed_root() failed: {e}", file=sys.stderr)
        # #endregion
        raise

    # Validate all file paths BEFORE reading from them
    # Note: Even deprecated parameters (defaults_file, filters) must be validated
    # for security to prevent path traversal attacks
    validate_paths(
        input_file=input_file,
        output_file=output_file,
        reference_doc=reference_doc,
        template=template,
        defaults_file=defaults_file,
        filters=filters,
        allowed_root=allowed_root,
    )

    # Validate contents is provided (input_file is deprecated)
    # Now safe to read from input_file after validation
    if not contents:
        if input_file:
            # Read from file for backward compatibility (deprecated)
            with open(input_file, encoding="utf-8") as f:
                contents = f.read()
        else:
            raise ValueError("contents parameter is required. Always provide markdown content.")

    # Validate input parameters
    if not contents and not input_file:
        raise ValueError("Either 'contents' or 'input_file' must be provided")

    # Validate templates - both DOCX and PDF require templates
    if output_format == "docx":
        if not reference_doc:
            raise ValueError(
                "reference_doc parameter is REQUIRED for docx output format. "
                "Call list-templates with format='docx' to get available templates."
            )
        if not os.path.exists(reference_doc):
            raise ValueError(f"Reference document not found: {reference_doc}")

    if output_format == "pdf":
        if not template:
            raise ValueError(
                "template parameter is REQUIRED for pdf output format. "
                "Call list-templates with format='pdf' to get available CSS templates."
            )
        # Case-insensitive check for .css extension
        if not template.lower().endswith(".css"):
            raise ValueError(f"Template file must be a CSS file (.css): {template}")
        if not os.path.exists(template):
            raise ValueError(f"Template file not found: {template}")

    # Validate that wrong template parameters aren't used
    if reference_doc and output_format != "docx":
        raise ValueError("reference_doc parameter is only supported for docx output format")
    if template and output_format != "pdf":
        raise ValueError("template parameter is only supported for pdf output format")

    # Note: defaults_file is deprecated and ignored (warning shown earlier)
    # No validation is performed since the parameter is not used

    # Normalize output_format to handle aliases before validation
    # This ensures "text" is normalized to "txt" before checking supported_formats
    format_aliases = {
        "text": "txt",
        "md": "markdown",
    }
    normalized_format = format_aliases.get(output_format.lower(), output_format.lower())

    # Define supported formats (reduced set - only formats we generate)
    supported_formats = {"html", "markdown", "pdf", "docx", "txt", "csv"}

    # Validate normalized format
    if normalized_format not in supported_formats:
        formats_str = ", ".join(sorted(supported_formats))
        raise ValueError(f"Unsupported output format: '{output_format}'. Supported formats are: {formats_str}")

    # Use normalized format for routing
    output_format = normalized_format

    # Note: Filter and defaults file validation removed - these features are deprecated
    # Filters and defaults_file parameters are accepted but ignored (warnings shown earlier)

    try:
        # Use generators to convert markdown content to target format
        # All generators accept markdown_content and return either str or bytes

        # Route to appropriate generator based on normalized output_format
        if output_format == "html":
            result = generate_html(contents, title=title)
        elif output_format == "txt":
            result = generate_txt(contents, title=title)
        elif output_format == "markdown":
            result = generate_markdown(contents, title=title)
        elif output_format == "csv":
            result = generate_csv(contents, title=title)
        elif output_format == "pdf":
            # Lazy import for PDF (may fail if system deps missing)
            try:
                from chat_a_doc.generators.generate_pdf import generate_pdf as generate_pdf_func

                result = generate_pdf_func(contents, title=title, template_path=template)
            except (ImportError, OSError) as e:
                raise ValueError(
                    f"PDF generation requires system dependencies (WeasyPrint). "
                    f"Error: {e}. These will be available in Docker."
                ) from e
        elif output_format == "docx":
            # Lazy import for DOCX
            try:
                from chat_a_doc.generators.generate_docx import generate_docx as generate_docx_func

                result = generate_docx_func(contents, reference_doc=reference_doc, title=title)
            except (ImportError, OSError) as e:
                raise ValueError(f"DOCX generation failed: {e}") from e
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        # Write result to file (handle both str and bytes)
        # #region agent log
        result_size = len(result) if hasattr(result, "__len__") else "N/A"
        result_type = type(result).__name__
        print(f"[DEBUG] Writing file: {output_file}, type: {result_type}, size: {result_size}", file=sys.stderr)
        try:
            log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
            log_data = {
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B",
                "location": "server.py:446",
                "message": "Before file write",
                "data": {"output_file": output_file, "result_type": type(result).__name__, "result_len": result_size},
                "timestamp": int(time.time() * 1000),
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception:  # noqa: S110 (intentionally broad for debug logging)
            pass
        # #endregion
        if isinstance(result, str):
            output_file_path = Path(output_file)
            # #region agent log
            try:
                log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "server.py:448",
                    "message": "Creating parent dirs",
                    "data": {"parent": str(output_file_path.parent), "exists": output_file_path.parent.exists()},
                    "timestamp": int(time.time() * 1000),
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception:  # noqa: S110 (intentionally broad for debug logging)
                pass
            # #endregion
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(result, encoding="utf-8")
            # #region agent log
            file_exists = output_file_path.exists()
            file_size = output_file_path.stat().st_size if file_exists else 0
            print(
                f"[DEBUG] File written: {output_file_path}, exists: {file_exists}, size: {file_size}",
                file=sys.stderr,
            )
            if not file_exists:
                parent_exists = output_file_path.parent.exists()
                parent_writable = os.access(output_file_path.parent, os.W_OK)
                print(
                    f"[DEBUG] ERROR: File write claimed success but file doesn't exist! "
                    f"Path: {output_file_path}, parent exists: {parent_exists}, parent writable: {parent_writable}",
                    file=sys.stderr,
                )
            try:
                log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "server.py:450",
                    "message": "After file write (str)",
                    "data": {"output_file": str(output_file_path), "exists": file_exists, "size": file_size},
                    "timestamp": int(time.time() * 1000),
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception:  # noqa: S110 (intentionally broad for debug logging)
                pass
            # #endregion
            # Verify file was actually created
            if not file_exists:
                raise OSError(f"File write failed: {output_file_path} does not exist after write operation")
        else:
            # bytes (for PDF, DOCX)
            output_file_path = Path(output_file)
            # #region agent log
            try:
                log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "server.py:453",
                    "message": "Creating parent dirs (bytes)",
                    "data": {"parent": str(output_file_path.parent), "exists": output_file_path.parent.exists()},
                    "timestamp": int(time.time() * 1000),
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception:  # noqa: S110 (intentionally broad for debug logging)
                pass
            # #endregion
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_bytes(result)
            # #region agent log
            file_exists = output_file_path.exists()
            file_size = output_file_path.stat().st_size if file_exists else 0
            print(
                f"[DEBUG] File written (bytes): {output_file_path}, exists: {file_exists}, size: {file_size}",
                file=sys.stderr,
            )
            if not file_exists:
                print(
                    f"[DEBUG] ERROR: File write claimed success but file doesn't exist! Path: {output_file_path}",
                    file=sys.stderr,
                )
            try:
                log_path = os.path.join(os.environ.get("ALLOWED_ROOT", "/app/files"), "debug.log")
                log_data = {
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "server.py:455",
                    "message": "After file write (bytes)",
                    "data": {"output_file": str(output_file_path), "exists": file_exists, "size": file_size},
                    "timestamp": int(time.time() * 1000),
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception:  # noqa: S110 (intentionally broad for debug logging)
                pass
            # #endregion
            # Verify file was actually created
            if not file_exists:
                raise OSError(f"File write failed: {output_file_path} does not exist after write operation")

        # Create result message
        result_message = f"Content successfully converted and saved to: {output_file}"

        # output_file is always set now (either provided or auto-generated)
        notify_with_result = result_message

        # Generate file link
        file_link, file_path = generate_file_link(
            output_file=output_file,
            allowed_root=allowed_root,
        )

        # Determine if HTTP links are being used (check if link starts with http)
        use_http_links = file_link.startswith("http://") or file_link.startswith("https://")

        # Build message text
        open_instruction = (
            "Click the link above"
            if use_http_links
            else "Copy the path above and paste it into your file browser, "
            "or use the file:// link in a compatible application."
        )
        message_text = (
            f"{notify_with_result}\n\n"
            f"📄 **Generated File:**\n`{file_path}`\n\n"
            f"🔗 **File Link:** {file_link}\n\n"
            f"💡 **To open:** {open_instruction}"
        )

        return [
            types.TextContent(
                type="text",
                text=message_text,
            )
        ]

    except Exception as e:
        # Handle conversion errors
        error_prefix = "Error converting"
        error_details = str(e)

        # Provide helpful error messages for common issues
        if "system dependencies" in error_details.lower() or "weasyprint" in error_details.lower():
            error_prefix = "PDF generation error"
            # Don't duplicate the message if it already contains the explanation
            if "PDF generation requires system dependencies" not in error_details:
                error_details = f"PDF generation requires system dependencies. {error_details}"
        elif "docx" in error_details.lower() and "generation failed" in error_details.lower():
            error_prefix = "DOCX generation error"
        elif "Failed to generate" in error_details or "No structured data" in error_details:
            # Generator-specific error
            error_prefix = "Conversion error"

        error_msg = f"{error_prefix} contents to {output_format}: {error_details}"
        raise ValueError(error_msg) from e


async def main():
    """Run the chat-a-doc server using stdin/stdout streams."""
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="chat-a-doc",
                    server_version="0.8.1",  # Universal MCP compatibility & SDK upgrade
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        import sys

        print(f"Error in chat-a-doc server: {e}", file=sys.stderr)
        raise
