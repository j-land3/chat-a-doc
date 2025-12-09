# Test Suite

This test suite validates the chat-a-doc document generation functionality, including unit tests, integration tests, and Docker container tests.

## Prerequisites

### For Unit/Integration Tests
- Python 3.11
- Dependencies installed via `uv sync`
- **Note:** PDF tests require WeasyPrint system dependencies (available in Docker, may fail locally)
- **Note:** DOCX tests may fail locally due to lxml compatibility issues (works in Docker)

### For Docker Integration Tests
- Docker installed and running
- Docker daemon accessible (for building images and running containers)

## Quick Start

### Standard Testing (Local Development)
For most development work, use the standard pytest commands:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_formats/test_html.py

# Run excluding Docker tests (faster)
uv run pytest --ignore=tests/test_docker_integration.py
```

### Container Testing (End-to-End Validation)
For testing the complete containerized application with timing logs and HTTP server:

```bash
# Build and run test container (from project root)
./build-test.sh

# Test the HTTP API directly
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# View container logs
docker logs chat-a-doc-test

# Stop the container
docker stop chat-a-doc-test
```

## Build Test Script (`build-test.sh`)

The `build-test.sh` script automates container testing for development and debugging:

### Features
- **Automatic cleanup**: Stops and removes old test containers
- **Test configuration**: Uses `tests/test_output` as the files volume
- **HTTP links enabled**: Sets `USE_HTTP_LINKS=true` and proper `HTTP_BASE_URL`
- **Port 8080**: Maps to host port 8080 for easy testing
- **Error checking**: Verifies container starts successfully
- **User feedback**: Shows status and access URLs

### Usage
```bash
# From project root directory
./build-test.sh
```

### What it does
1. Stops/removes existing `chat-a-doc-test` container
2. Builds new container image (`chat-a-doc-test`)
3. Starts container with test configuration:
   - Volume: `./tests/test_output:/app/files`
   - Port: `8080:8080`
   - Environment: `ALLOWED_ROOT=/app/files`, `USE_HTTP_LINKS=true`, `HTTP_BASE_URL=http://localhost:8080`
4. Verifies container is running
5. Shows access URLs and management commands

### Container Management
```bash
# View logs
docker logs chat-a-doc-test

# Follow logs in real-time
docker logs -f chat-a-doc-test

# Stop container
docker stop chat-a-doc-test

# Remove container
docker rm chat-a-doc-test
```

### Testing with Container
```bash
# Test HTTP API directly
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test document generation
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"convert-contents","arguments":{"contents":"Test content","output_format":"docx","title":"Test Document","reference_doc":"/app/files/templates/journal.docx"}}}'
```

## Test Structure

```
tests/
├── README.md                # This file - testing documentation
├── __init__.py
├── conftest.py              # Pytest fixtures and test utilities
├── build-test.sh            # Container build and test script
├── test_data/               # Test markdown files and expected outputs
│   ├── simple.md
│   ├── complex.md
│   ├── tables.md
│   ├── edge_cases.md
│   └── baselines/           # Captured baseline outputs (created during first run)
│       ├── html/
│       ├── txt/
│       ├── pdf/
│       ├── docx/
│       ├── csv/
│       └── markdown/
├── test_formats/            # Format-specific tests
│   ├── test_html.py
│   ├── test_txt.py
│   ├── test_pdf.py
│   ├── test_docx.py
│   ├── test_csv.py
│   └── test_markdown.py
├── test_templates.py        # Template system tests
├── test_security.py         # Security validation tests
├── test_integration.py      # End-to-end workflow tests
├── test_docker_integration.py  # Docker container integration tests
├── test_output/             # Runtime test outputs and templates
│   └── templates/           # Test templates directory
└── test_helpers.py          # Helper functions for tests
```

## Running Tests

### Pre-commit Hooks
```bash
# Install pre-commit hooks (runs automatically before commits)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files src/chat_a_doc/server.py
```

### Test Commands

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_formats/test_html.py

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_formats/test_html.py::test_html_simple

# Run only Docker integration tests (requires Docker)
uv run pytest tests/test_docker_integration.py

# Run tests excluding Docker tests (faster, no Docker required)
uv run pytest -m "not docker"  # If we add docker marker, or:
uv run pytest --ignore=tests/test_docker_integration.py

# Run tests that don't require system dependencies
uv run pytest tests/test_security.py tests/test_templates.py::test_list_templates
```

## Test Coverage

### Format Conversion Tests
- HTML: Simple and complex markdown → HTML (uses python-markdown)
- TXT: Simple and complex markdown → Plain text (uses python-markdown + html2text)
- PDF: Simple and complex markdown → PDF (uses WeasyPrint - may fail locally without system deps)
- DOCX: Simple and complex markdown → DOCX (uses python-docx - may fail locally due to lxml)
- CSV: Table extraction and formula injection protection
- MARKDOWN: Pass-through conversion

### Template System Tests
- List templates functionality
- Template application (reference_doc) - may fail locally due to lxml
- Multiple template handling

### Security Tests
- ALLOWED_ROOT path validation
- Path traversal prevention
- CSV formula injection protection
- Input validation

### Integration Tests
- Full conversion workflow
- Template selection → conversion workflow (may fail locally due to lxml)
- Error handling
- Auto-filename generation

### Docker Integration Tests (Require Docker)
- Container startup and initialization
- MCP protocol over HTTP in container
- All 6 format generations in container environment
- Template listing in container
- Security validation in container (ALLOWED_ROOT enforcement)
- File generation and volume mounting

## Baseline Outputs

Baseline outputs from previous test runs are stored in `test_data/baselines/`. These can be used for comparison during development.

## Test Results

### Expected Test Results (Local)
- **18+ tests passing**: Most format tests, security tests, integration tests
- **4 tests may fail**: PDF (needs WeasyPrint system deps), DOCX (lxml compatibility)
- **2 tests skipped**: Some CSV formula injection tests (require specific conditions)

### Docker Integration Tests
- **All Docker tests skipped** if Docker is not available
- **All Docker tests should pass** if Docker is running and image builds successfully
- Docker tests verify the complete containerized application works end-to-end

## Notes

- Tests use temporary directories for output files
- ALLOWED_ROOT is set to temp directory for each test
- Baseline outputs are saved automatically on first successful run
- CSV formula injection protection adds tab character prefix to dangerous cells (=, +, -, @)
- Docker integration tests build a test image (`chat-a-doc-test:latest`) and start containers for each test
- Docker tests use temporary directories mounted as volumes
- Set `REBUILD_DOCKER=true` environment variable to force Docker image rebuild
