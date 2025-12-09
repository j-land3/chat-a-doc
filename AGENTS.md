# AGENTS.md

## Core Principles
<!-- These 6 principles guide all decisions. When uncertain, default to these. -->
- **Separation of Concerns**: Single responsibility per module. Clear boundaries.
- **Explicit over Implicit**: No hidden behavior. Clear interfaces and contracts.
- **Design for Change**: Modular designs that evolve independently.
- **Fail Safely**: Default deny. Graceful degradation. Defense in depth.
- **Measure What Matters**: Decisions based on data, not assumptions.
- **Developer Experience First**: Code optimized for human AND AI readability.

**Architecture Default**: Layered Architecture (Presentation → Business Logic → Data Access)
**When uncertain**: Choose the simpler option. Escalate to human if principles conflict.

---

## Project Overview

chat-a-doc (formerly doc-gen) is an MCP (Model Context Protocol) server that enables AI agents to generate documents in multiple formats (PDF, DOCX, HTML, TXT, CSV, MARKDOWN) directly from chat conversations. It runs as a Docker container and provides secure, sandboxed document generation capabilities.

**Tech Stack**: Python 3.11, MCP Protocol, Docker
**Status**: Phase 4 Complete - Previous implementation removed, using lightweight generators

**Current State**: Modular generator architecture (simple functions approach). All 6 formats implemented using lightweight Python libraries (markdown, html2text, weasyprint, python-docx).

**Python Version**: Python 3.11 (pinned via `.python-version` file). Python 3.14+ is not supported due to pydantic-core compatibility.

---

## Setup Commands
```bash
# Install Python 3.11 (if not already installed)
uv python install 3.11

# Pin Python version for this project (creates .python-version file)
uv python pin 3.11

# Install dependencies (using uv)
uv sync

# Install pre-commit hooks (run once)
uv run pre-commit install

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Build Docker image
docker build -t chat-a-doc .

# Run container locally
docker run -d --name chat-a-doc -p 8080:8080 -v /path/to/output:/app/files -e ALLOWED_ROOT=/app/files chat-a-doc
```

---

## Code Style
- **File naming**: snake_case (`user_service.py`, `markdown_to_html.py`)
  - Exception: Uppercase for special files (`README.md`, `AGENTS.md`, `LICENSE`, etc.)
- **Functions**: verb + noun (`get_user_by_id`, `validate_input`)
- **Variables**: descriptive nouns (`user_count`, `is_active`)
- **Formatting**: Ruff enforced. Run `uv run ruff format .` before committing.
- **Line length**: 120 characters (configured in pyproject.toml)

**Python Conventions:**
- Use type hints for all function parameters and return values
- Use docstrings for all public functions and classes
- Follow PEP 8 style guide (enforced by ruff)

---

## Testing
- Run `uv run pytest` before every commit
- All tests must pass before merge
- Add tests for new functionality
- Test organization: `tests/` directory mirroring source structure

**Coverage target**: 80%+ for business logic

**Current Status**: Test infrastructure established. Regression tests validate generator implementations.

---

## Workflow
- **Branching**: Trunk-based. Feature branches for changes >200 lines.
- **Commits**: Small, focused. Format: `type: description` (feat:, fix:, refactor:)
- **Before committing**: Pre-commit hooks run automatically (linting, formatting)
  - Install hooks: `uv run pre-commit install`
  - Run manually: `uv run pre-commit run --all-files`
  - Skip hooks (not recommended): `git commit --no-verify`

**Refactoring Phases:**
- Phase 0: Principles Foundation ✓
- Phase 1: Assessment & Foundation ✓
- Phase 2: Architecture Design ✓
- Phase 3: Incremental Replacement ✓
- Phase 4: Cleanup & Optimization ✓ (Complete)

---

## Escalation
Pause and consult human when:
- Architectural decisions not covered by Core Principles
- Security implications are unclear
- Multiple valid approaches with significant trade-offs
- Library choices require evaluation (wait for appropriate phase)
- Something feels wrong but you can't articulate why

---

## References
- [System Design & Architecture](../dev-design/01_system_design_architecture.md)
- [Development & Quality](../dev-design/02_development_quality.md) - See "File and Directory Naming Conventions" section for naming standards
- [Collaboration & Knowledge](../dev-design/03_collaboration_knowledge.md)
- [Refactoring Plan](./docs/refactoring_plan.md) - Overall refactoring strategy
- [Principles Validation Checklist](./docs/principles_validation_checklist.md) - Quality gates
- [Decision Log](./docs/decision_log.md) - Process decisions
