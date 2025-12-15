"""HTTP server that bridges HTTP requests to stdio-based MCP server."""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# Global dictionary to maintain MCP server processes per session
# Key: session_id (client IP), Value: dict with process info
_mcp_sessions = {}
_session_lock = threading.Lock()


def forward_stderr(process):
    """Forward stderr from subprocess to main process stderr (for docker logs)."""
    try:
        for line in iter(process.stderr.readline, ""):
            if line:
                sys.stderr.write(f"[MCP] {line}")
                sys.stderr.flush()
    except Exception:  # noqa: S110 (intentionally broad for cleanup)
        pass  # Process may have closed stderr


def get_or_create_session(session_id):
    """Get or create an MCP server process for a session."""
    with _session_lock:
        if session_id not in _mcp_sessions:
            # Spawn MCP server process (text mode for stdio)
            process = subprocess.Popen(  # noqa: S603 (sys.executable is trusted)
                [sys.executable, "-m", "chat_a_doc"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            # Start background thread to forward stderr to main process stderr
            stderr_thread = threading.Thread(target=forward_stderr, args=(process,), daemon=True)
            stderr_thread.start()
            _mcp_sessions[session_id] = {"process": process, "initialized": False}
        return _mcp_sessions[session_id]


class MCPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler that bridges requests to MCP stdio server."""

    def do_POST(self):  # noqa: N802 (required by BaseHTTPRequestHandler)
        """Handle POST requests by forwarding to MCP server via stdio."""
        request_start = time.time()
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length)

            # Parse request body (should be JSON-RPC)
            try:
                request_json = json.loads(request_body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError("Invalid JSON in request body") from e

            # Get session ID from client IP (simple session management)
            session_id = self.client_address[0]

            # Get or create MCP server session
            session = get_or_create_session(session_id)
            process = session["process"]

            # Check if process is still alive
            if process.poll() is not None:
                # Process died, create a new one
                with _session_lock:
                    if session_id in _mcp_sessions:
                        del _mcp_sessions[session_id]
                session = get_or_create_session(session_id)
                process = session["process"]

            # Check if this is a notification (no 'id' field)
            is_notification = "id" not in request_json
            is_initialize = request_json.get("method") == "initialize"

            # Send request to MCP server via stdin (newline-delimited JSON)
            send_start = time.time()
            request_line = json.dumps(request_json) + "\n"
            method = request_json.get("method", "")
            try:
                process.stdin.write(request_line)
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                # Process died, create a new one
                with _session_lock:
                    if session_id in _mcp_sessions:
                        del _mcp_sessions[session_id]
                session = get_or_create_session(session_id)
                process = session["process"]
                process.stdin.write(request_line)
                process.stdin.flush()

            # Mark as initialized after initialize request
            if is_initialize:
                session["initialized"] = True

            # For notifications, return empty success response
            if is_notification:
                response_body = json.dumps({"jsonrpc": "2.0", "result": None}).encode("utf-8")
            else:
                # Read response from stdout (newline-delimited JSON)
                # Use timeout mechanism to prevent indefinite blocking
                response_queue = queue.Queue()
                exception_queue = queue.Queue()

                def read_response():
                    try:
                        response_line = process.stdout.readline()
                        response_queue.put(response_line)
                    except Exception as e:
                        exception_queue.put(e)

                # Start reading in a separate thread
                read_thread = threading.Thread(target=read_response, daemon=True)
                read_thread.start()

                # Wait for response with timeout (60 seconds for tool calls, 10 for others)
                timeout = 60 if method == "tools/call" else 10
                read_start = time.time()
                read_thread.join(timeout=timeout)
                read_time = time.time() - read_start

                if read_thread.is_alive():
                    # Timeout - process might be hung
                    # Check if process is still alive
                    if process.poll() is None:
                        # Process is still running but not responding
                        raise RuntimeError(f"MCP server timeout after {timeout} seconds (method: {method})")
                    else:
                        # Process died
                        stderr_output = ""
                        try:
                            if process.stderr.readable():
                                stderr_output = process.stderr.read(1024)
                        except Exception:  # noqa: S110 (intentionally broad for cleanup)
                            pass
                        error_msg = (
                            f"MCP server process died during timeout "
                            f"(exit code: {process.returncode}): {stderr_output}"
                        )
                        raise RuntimeError(error_msg)

                if not exception_queue.empty():
                    raise exception_queue.get()

                if response_queue.empty():
                    # Check if process died
                    if process.poll() is not None:
                        stderr_output = ""
                        try:
                            if process.stderr.readable():
                                stderr_output = process.stderr.read(1024)
                        except Exception:  # noqa: S110 (intentionally broad for cleanup)
                            pass
                        error_msg = f"MCP server process died (exit code: {process.returncode}): {stderr_output}"
                        raise RuntimeError(error_msg)
                    raise RuntimeError("No response from MCP server")

                response_line = response_queue.get()
                if not response_line:
                    # Empty response - check if process died
                    if process.poll() is not None:
                        stderr_output = ""
                        try:
                            if process.stderr.readable():
                                stderr_output = process.stderr.read(1024)
                        except Exception:  # noqa: S110 (intentionally broad for cleanup)
                            pass
                        error_msg = f"MCP server process died (exit code: {process.returncode}): {stderr_output}"
                        raise RuntimeError(error_msg)
                    raise RuntimeError("Empty response from MCP server")

                # Parse response
                parse_start = time.time()
                try:
                    response_json = json.loads(response_line.strip())
                    response_body = json.dumps(response_json).encode("utf-8")
                except json.JSONDecodeError:
                    # If not valid JSON, return as-is
                    response_body = response_line.encode("utf-8")

            # Send HTTP response
            http_send_start = time.time()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(response_body)
            self.wfile.flush()

        except Exception as e:
            # Send error response
            request_id = None
            if "request_json" in locals():
                request_id = request_json.get("id")

            error_response = json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": f"Internal error: {str(e)}"}}
            ).encode("utf-8")

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response)

    def do_GET(self):  # noqa: N802 (required by BaseHTTPRequestHandler)
        """Handle GET requests for file serving."""
        try:
            # Only serve files from /files/ path
            if not self.path.startswith("/files/"):
                self.send_response(404)
                self.end_headers()
                return

            # Get the filename from the path
            filename = self.path[7:]  # Remove '/files/' prefix

            # Security: Only allow files within ALLOWED_ROOT
            allowed_root = os.environ.get("ALLOWED_ROOT", "/app/files")
            allowed_root = os.path.realpath(allowed_root)

            # Construct full file path
            file_path = os.path.join(allowed_root, filename)
            file_path = os.path.realpath(file_path)

            # Security check: ensure file is within ALLOWED_ROOT
            # Using startswith() alone is vulnerable to sibling directory attacks (e.g., /app/files_sibling)
            # Must check for exact match or prefix with directory separator
            if file_path != allowed_root and not file_path.startswith(allowed_root + os.sep):
                self.send_response(403)
                self.end_headers()
                return

            # Check if file exists
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return

            # Determine content type
            import mimetypes

            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = "application/octet-stream"

            # Determine if file should be downloaded (attachment) or displayed inline
            # Document formats (TXT, MARKDOWN, HTML, CSV, PDF, DOCX) should be downloaded
            # Only allow inline display for very specific types (e.g., images in future)
            file_ext = os.path.splitext(file_path)[1].lower()
            download_formats = {".txt", ".md", ".markdown", ".html", ".htm", ".csv", ".pdf", ".docx", ".doc"}

            if file_ext in download_formats:
                disposition = "attachment"  # Force download
            else:
                disposition = "inline"  # Display in browser (for images, etc.)

            # Read and serve file
            with open(file_path, "rb") as f:
                file_content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(file_content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            # Set Content-Disposition to force download for document formats
            self.send_header("Content-Disposition", f'{disposition}; filename="{os.path.basename(file_path)}"')
            self.end_headers()
            self.wfile.write(file_content)

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            print(f"Error serving file: {e}", file=sys.stderr)

    def do_OPTIONS(self):  # noqa: N802 (required by BaseHTTPRequestHandler)
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def log_message(self, format, *args):
        """Override to use stderr for logging."""
        sys.stderr.write(f"{self.address_string()} - {format % args}\n")


def run_server(port=8080):
    """Run the HTTP server on the specified port."""
    try:
        server_address = ("", port)
        httpd = HTTPServer(server_address, MCPHTTPHandler)

        print(f"chat-a-doc HTTP server listening on port {port}", file=sys.stderr)
        print(f"Connect via: http://localhost:{port}", file=sys.stderr)
        sys.stderr.flush()

        httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"ERROR: Port {port} is already in use", file=sys.stderr)
        else:
            print(f"ERROR: Failed to bind to port {port}: {e}", file=sys.stderr)
        sys.stderr.flush()
        raise
    except KeyboardInterrupt:
        print("\nShutting down HTTP server...", file=sys.stderr)
        sys.stderr.flush()
        httpd.shutdown()
    except Exception as e:
        print(f"ERROR: HTTP server crashed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise


def main():
    """Run the HTTP server."""
    try:
        # Ensure stdout/stderr are unbuffered for Docker
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)

        # Get port from environment variable, default to 8080
        port = int(os.environ.get("HTTP_PORT", "8080"))

        print(f"Starting chat-a-doc HTTP server on port {port}...", file=sys.stderr)
        print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}", file=sys.stderr)

        run_server(port)
    except Exception as e:
        print(f"Fatal error starting HTTP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
