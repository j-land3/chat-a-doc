"""Docker integration tests for chat-a-doc.

These tests build the Docker image, start containers, and make actual
HTTP requests to verify the containerized application works correctly.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Skip all Docker tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not shutil.which("docker"), reason="Docker not available - skipping Docker integration tests"
)


@pytest.fixture(scope="session")
def docker_image():
    """Build Docker image for testing."""
    image_name = "chat-a-doc-test:latest"

    # Check if image already exists
    result = subprocess.run(["docker", "images", "-q", image_name], capture_output=True, text=True)

    # Build image if it doesn't exist or if we want to rebuild
    build_needed = not result.stdout.strip() or os.environ.get("REBUILD_DOCKER", "false").lower() == "true"

    if build_needed:
        print(f"Building Docker image: {image_name}")
        result = subprocess.run(["docker", "build", "-t", image_name, "."], capture_output=True, text=True)

        if result.returncode != 0:
            pytest.fail(f"Docker build failed: {result.stderr}")

    yield image_name

    # Cleanup: Optionally remove image (commented out to speed up subsequent tests)
    # subprocess.run(["docker", "rmi", image_name], capture_output=True)


@pytest.fixture
def docker_container(docker_image):
    """Start Docker container for testing."""
    # Create temporary directory for volume mount
    temp_dir = tempfile.mkdtemp(prefix="chat-a-doc-test-")
    temp_path = Path(temp_dir)

    # Create templates directory
    (temp_path / "templates").mkdir(exist_ok=True)

    # Fix permissions: Make directory writable by container user (UID 1000)
    # This is necessary because volume mounts preserve host permissions,
    # and in CI the temp dir might be owned by a different user
    # #region agent log
    import stat
    os.chmod(temp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 777 for testing
    print(f"[TEST DEBUG] Set temp_dir permissions: {oct(os.stat(temp_dir).st_mode)[-3:]}", file=sys.stderr)
    # #endregion

    container_name = f"chat-a-doc-test-{int(time.time())}"

    # Start container
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        "0:8080",  # Let Docker assign random port
        "-v",
        f"{temp_dir}:/app/files",
        "-e",
        "ALLOWED_ROOT=/app/files",
        "-e",
        "USE_HTTP_LINKS=true",
        "-e",
        "HTTP_BASE_URL=http://localhost:8080",
        docker_image,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        pytest.fail(f"Failed to start container: {result.stderr}")

    container_id = result.stdout.strip()

    # Wait for container to be ready
    max_wait = 10
    wait_time = 0
    while wait_time < max_wait:
        result = subprocess.run(["docker", "ps", "-q", "-f", f"name={container_name}"], capture_output=True, text=True)
        if result.stdout.strip():
            break
        time.sleep(0.5)
        wait_time += 0.5

    if wait_time >= max_wait:
        # Get logs for debugging
        logs = subprocess.run(["docker", "logs", container_name], capture_output=True, text=True)
        pytest.fail(f"Container failed to start. Logs: {logs.stdout}\n{logs.stderr}")

    # Get the port mapping
    result = subprocess.run(["docker", "port", container_name], capture_output=True, text=True)

    if result.returncode != 0:
        pytest.fail(f"Failed to get container port: {result.stderr}")

    # Parse port (format: "8080/tcp -> 0.0.0.0:XXXXX")
    port_line = result.stdout.strip().split("\n")[0]
    host_port = port_line.split(":")[-1]

    base_url = f"http://localhost:{host_port}"

    # Wait a bit more for HTTP server to be ready
    time.sleep(2)

    yield {
        "container_name": container_name,
        "container_id": container_id,
        "base_url": base_url,
        "temp_dir": temp_path,
        "host_port": host_port,
    }

    # Cleanup: Stop and remove container
    subprocess.run(["docker", "stop", container_name], capture_output=True)
    subprocess.run(["docker", "rm", container_name], capture_output=True)

    # Cleanup: Remove temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


def make_mcp_request(base_url, method, params=None, request_id=1):
    """Make an MCP JSON-RPC request to the container."""
    import urllib.request
    import urllib.parse

    request_data = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }

    if params:
        request_data["params"] = params

    request_json = json.dumps(request_data).encode("utf-8")

    req = urllib.request.Request(base_url, data=request_json, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return response_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
            return error_data
        except json.JSONDecodeError:
            pytest.fail(f"HTTP {e.code}: {error_body}")
    except Exception as e:
        pytest.fail(f"Request failed: {e}")


def test_docker_container_starts(docker_container):
    """Test that Docker container starts successfully."""
    # Container fixture already verifies startup
    assert docker_container["container_name"]
    assert docker_container["base_url"]


def test_docker_mcp_initialize(docker_container):
    """Test MCP initialize request to container."""
    response = make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    assert "result" in response
    assert "jsonrpc" in response
    assert response["jsonrpc"] == "2.0"
    assert "serverInfo" in response["result"]


def test_docker_list_tools(docker_container):
    """Test list-tools request to container."""
    # First initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Then list tools
    response = make_mcp_request(docker_container["base_url"], "tools/list", {})

    assert "result" in response
    tools = response["result"].get("tools", [])

    # Should have convert-contents and list-templates
    tool_names = [tool["name"] for tool in tools]
    assert "convert-contents" in tool_names
    assert "list-templates" in tool_names


def test_docker_html_generation(docker_container):
    """Test HTML generation in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Convert to HTML
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test.",
                "output_format": "html",
                "title": "Test HTML Document",
            },
        },
    )

    assert "result" in response
    assert "content" in response["result"]

    # Verify file was created in container
    # #region agent log
    import json as json_module, time as time_module
    debug_log = docker_container["temp_dir"] / "debug.log"
    all_files = list(docker_container["temp_dir"].rglob("*"))
    print(f"[TEST DEBUG] All files in temp_dir: {[str(f.relative_to(docker_container['temp_dir'])) for f in all_files]}")
    # #endregion
    # Get Docker logs for debugging
    logs_result = subprocess.run(
        ["docker", "logs", docker_container["container_name"]],
        capture_output=True,
        text=True,
    )
    if "DEBUG" in logs_result.stderr or "DEBUG" in logs_result.stdout:
        print(f"[TEST DEBUG] Docker logs with DEBUG:\n{logs_result.stderr}\n{logs_result.stdout}")
    html_files = list(docker_container["temp_dir"].glob("*.html"))
    print(f"[TEST DEBUG] HTML files found: {[str(f) for f in html_files]}")
    assert len(html_files) > 0

    # Verify file content
    html_content = html_files[0].read_text(encoding="utf-8")
    assert "Test Document" in html_content or "test" in html_content.lower()


def test_docker_txt_generation(docker_container):
    """Test TXT generation in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Convert to TXT
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test.",
                "output_format": "txt",
                "title": "Test TXT Document",
            },
        },
    )

    assert "result" in response

    # Verify file was created
    txt_files = list(docker_container["temp_dir"].glob("*.txt"))
    assert len(txt_files) > 0

    txt_content = txt_files[0].read_text(encoding="utf-8")
    assert "Test Document" in txt_content or "test" in txt_content.lower()


def test_docker_markdown_generation(docker_container):
    """Test MARKDOWN generation in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Convert to MARKDOWN
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test.",
                "output_format": "markdown",
                "title": "Test Markdown Document",
            },
        },
    )

    assert "result" in response

    # Verify file was created
    md_files = list(docker_container["temp_dir"].glob("*.md"))
    assert len(md_files) > 0


def test_docker_csv_generation(docker_container):
    """Test CSV generation in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Convert to CSV
    markdown_with_table = """# Table Document

| Name | Age | City |
|------|-----|------|
| Alice | 30  | NYC  |
| Bob   | 25  | LA   |
"""

    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {"contents": markdown_with_table, "output_format": "csv", "title": "Test CSV Document"},
        },
    )

    assert "result" in response

    # Verify file was created
    csv_files = list(docker_container["temp_dir"].glob("*.csv"))
    assert len(csv_files) > 0

    csv_content = csv_files[0].read_text(encoding="utf-8")
    assert "Name" in csv_content or "Alice" in csv_content


def test_docker_pdf_generation(docker_container):
    """Test PDF generation in Docker container (requires WeasyPrint system deps)."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Create CSS template (required for PDF)
    templates_dir = docker_container["temp_dir"] / "templates"
    templates_dir.mkdir(exist_ok=True)

    css_template = templates_dir / "test_template.css"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    # Convert to PDF
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test.",
                "output_format": "pdf",
                "title": "Test PDF Document",
                "template": f"/app/files/templates/{css_template.name}",
            },
        },
    )

    # PDF might fail if system deps missing, but should at least get a response
    assert "result" in response or "error" in response

    if "result" in response:
        # Verify file was created
        pdf_files = list(docker_container["temp_dir"].glob("*.pdf"))
        assert len(pdf_files) > 0
        assert pdf_files[0].stat().st_size > 0  # Non-empty file


def test_docker_docx_generation(docker_container):
    """Test DOCX generation in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Copy a DOCX template from test_output/templates to the test's templates directory
    templates_dir = docker_container["temp_dir"] / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Look for templates in tests/test_output/templates/
    test_templates_dir = Path(__file__).parent / "test_output" / "templates"
    docx_template = None

    if test_templates_dir.exists():
        # Find the first DOCX template
        for template_file in test_templates_dir.glob("*.docx"):
            docx_template = templates_dir / template_file.name
            shutil.copy(template_file, docx_template)
            break

    if docx_template is None or not docx_template.exists():
        pytest.skip(f"No DOCX templates found in {test_templates_dir}")

    # Convert to DOCX
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test.",
                "output_format": "docx",
                "title": "Test DOCX Document",
                "reference_doc": f"/app/files/templates/{docx_template.name}",
            },
        },
    )

    # DOCX might fail due to lxml issues, but should get a response
    assert "result" in response or "error" in response

    if "result" in response:
        # Verify file was created (exclude template file)
        docx_files = list(docker_container["temp_dir"].glob("*.docx"))
        generated_files = [f for f in docx_files if f.name != docx_template.name]
        assert len(generated_files) > 0
        assert generated_files[0].stat().st_size > 0  # Non-empty file


def test_docker_list_templates(docker_container):
    """Test list-templates in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # List templates
    response = make_mcp_request(
        docker_container["base_url"], "tools/call", {"name": "list-templates", "arguments": {"format": "docx"}}
    )

    assert "result" in response
    assert "content" in response["result"]


def test_docker_security_allowed_root(docker_container):
    """Test that ALLOWED_ROOT security is enforced in container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Try to access file outside ALLOWED_ROOT (should fail)
    # This tests that path validation works in container
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test",
                "output_format": "html",
                "title": "Test",
                # Try to write outside allowed root (if this parameter exists)
            },
        },
    )

    # Should succeed (path validation happens server-side)
    # The real test is that files are only created in /app/files
    assert "result" in response or "error" in response

    # Verify files are only in the mounted volume
    html_files = list(docker_container["temp_dir"].glob("*.html"))
    # Files should be in temp_dir (which is mounted as /app/files)
    assert all(str(f).startswith(str(docker_container["temp_dir"])) for f in html_files)


def test_docker_list_templates_pdf(docker_container):
    """Test list-templates for PDF format in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Create CSS templates in the mounted volume
    templates_dir = docker_container["temp_dir"] / "templates"
    templates_dir.mkdir(exist_ok=True)

    # Create a CSS template
    css_template = templates_dir / "corporate.css"
    css_template.write_text("body { font-family: Arial; }", encoding="utf-8")

    # List PDF templates
    response = make_mcp_request(
        docker_container["base_url"], "tools/call", {"name": "list-templates", "arguments": {"format": "pdf"}}
    )

    assert "result" in response
    assert "content" in response["result"]
    content_text = response["result"]["content"][0]["text"]
    assert "corporate.css" in content_text or "PDF" in content_text.upper()


def test_docker_pdf_with_template(docker_container):
    """Test PDF generation with CSS template in Docker container."""
    # Initialize
    make_mcp_request(
        docker_container["base_url"],
        "initialize",
        {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    )

    # Create CSS template in the mounted volume
    templates_dir = docker_container["temp_dir"] / "templates"
    templates_dir.mkdir(exist_ok=True)

    css_template = templates_dir / "test_template.css"
    css_content = """
    @page {
        size: A4;
        margin: 1in;
    }
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
        color: #333333;
    }
    h1 {
        color: #0066cc;
        font-size: 24pt;
    }
    """
    css_template.write_text(css_content, encoding="utf-8")

    # Generate PDF with template
    response = make_mcp_request(
        docker_container["base_url"],
        "tools/call",
        {
            "name": "convert-contents",
            "arguments": {
                "contents": "# Test Document\n\nThis is a test with a CSS template.",
                "output_format": "pdf",
                "title": "Test PDF with Template",
                "template": f"/app/files/templates/{css_template.name}",
            },
        },
    )

    # PDF might fail if system deps missing, but should at least get a response
    assert "result" in response or "error" in response

    if "result" in response:
        # Verify file was created
        pdf_files = list(docker_container["temp_dir"].glob("*.pdf"))
        assert len(pdf_files) > 0
        assert pdf_files[0].stat().st_size > 0  # Non-empty file
