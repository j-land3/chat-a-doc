# ADR-002: Library Selection for Universal Converter Replacement

## Status
Accepted

## Context

As part of replacing the universal converter with lightweight, purpose-built generators (see [ADR-001](./adr-001-replace-universal-converter.md)), we need to select specific Python libraries for each format conversion. The goal is to reduce Docker image size from ~3.1GB (universal converter + TeX Live) to ~51MB while maintaining functionality and quality.

**Requirements:**
- Lightweight: Small footprint, minimal dependencies
- Python-native: Pure Python or well-maintained Python bindings
- Active Maintenance: Recent updates, active community
- Feature Support: Covers required conversion features
- Docker-friendly: Works well in containerized environments
- License Compatibility: Compatible with project license

**Format Requirements:**
- HTML: Convert markdown to HTML with table and code block support
- TXT: Convert markdown to plain text (strip formatting)
- PDF: Convert markdown to PDF via HTML pipeline
- DOCX: Convert markdown to DOCX with template support (critical feature)
- CSV: Extract tables from markdown (already implemented, needs markdown parser)
- MARKDOWN: Pass-through (already implemented)

## Decision

Select the following libraries for format conversion:

### HTML Converter: python-markdown

**Library:** `markdown` (python-markdown) version 3.5+

**Rationale:**
- Most mature and widely adopted Python markdown library (3.5k+ GitHub stars)
- Extensive extension ecosystem (tables, code highlighting, footnotes, etc.)
- Actively maintained with regular updates (2024)
- Well-documented with large community support
- Used by major Python documentation tools (MkDocs, Pelican, Flask-FlatPages)
- Pure Python, minimal dependencies (~200KB)
- MIT License

**Performance:** Moderate (3-4x slower than mistune) but fast enough for typical documents (<100ms for typical docs)

**Alternatives Considered:**
- **mistune:** Faster but smaller community, less extension support
- **markdown-it-py:** More dependencies, smaller community

### TXT Converter: markdown → HTML → html2text Pipeline

**Libraries:** `markdown` (python-markdown) + `html2text`

**Rationale:**
- Reuses python-markdown dependency (already needed for HTML)
- html2text is purpose-built for HTML-to-text conversion
- Excellent text quality (preserves structure, handles links, lists)
- Small dependency footprint (~50KB for html2text)
- Simple implementation: two function calls
- Well-maintained and actively developed

**Alternatives Considered:**
- **BeautifulSoup:** Larger dependency (~300KB+), requires custom parsing logic
- **Custom text renderer:** More complex, higher maintenance burden

### PDF Converter: WeasyPrint

**Library:** `weasyprint` version 60+

**Rationale:**
- Perfect fit for markdown → HTML → PDF pipeline
- Full CSS support (CSS 2.1, partial CSS 3) for document styling
- High-quality, print-ready PDF output
- Actively maintained (2024 updates)
- Pure Python (no external binaries, only system libraries)
- BSD-3-Clause License
- Used in production by many Python applications

**System Dependencies:** libpango, cairo, gdk-pixbuf (~50MB in Docker)

**Performance:** Moderate (good for typical documents, <2 seconds target)

**Alternatives Considered:**
- **ReportLab:** Pure Python but requires manual layout, doesn't fit HTML pipeline
- **xhtml2pdf (pisa):** Limited CSS support, less active maintenance
- **pdfkit (wkhtmltopdf):** Requires external binary, maintenance concerns

### DOCX Converter: python-docx

**Library:** `python-docx` version 1.1+

**Rationale:**
- **Best template support:** Can open existing DOCX templates and copy styles (critical requirement)
- Pure Python (no external binaries)
- Actively maintained (2024 updates, 3.5k+ GitHub stars)
- Well-documented with comprehensive examples
- Full programmatic control over DOCX generation
- MIT License

**Trade-offs:**
- Requires manual markdown parsing and DOCX structure building (more implementation work)
- Learning curve for API

**Alternatives Considered:**
- **markdown2docx:** Simpler wrapper but limited template support
- **Previous Python wrapper:** Defeats purpose of refactoring (external binary, large footprint)

### CSV Converter: Built-in csv Module

**Library:** Built-in Python `csv` module (no new dependency)

**Rationale:**
- Already implemented and working
- Formula injection protection already in place
- No dependencies needed
- Will need markdown table parsing (using python-markdown table extension)

**Status:** Keep existing implementation, replace previous JSON AST with python-markdown AST

### MARKDOWN Converter: Pass-through

**Library:** None (built-in pass-through)

**Rationale:**
- Simple pass-through implementation
- No dependencies needed
- Optional normalization can be added later if needed

## Consequences

### Positive
- **Docker Image Size:** Reduced from ~3.1GB to ~51MB (~98% reduction)
- **Dependencies:** All Python-native (except WeasyPrint system libs)
- **Maintainability:** Well-maintained libraries with active communities
- **Template Support:** python-docx provides excellent template handling
- **Pipeline Efficiency:** HTML pipeline (markdown → HTML → PDF/TXT) reuses components

### Challenges
- **Implementation Complexity:** DOCX converter requires manual markdown parsing and DOCX building
- **System Dependencies:** WeasyPrint requires system libraries (~50MB in Docker)
- **Learning Curve:** python-docx API requires learning for DOCX generation

### Mitigation
- Use python-markdown's extension system for markdown parsing (reusable across generators)
- Document WeasyPrint system dependencies in Dockerfile with inline comments
- Create helper functions for common DOCX operations (paragraphs, headings, lists)

## Dependencies Summary

```toml
# Core markdown processing
markdown = "^3.5"           # For HTML conversion
html2text = "^2024"         # For TXT conversion

# PDF generation
weasyprint = "^60"          # For PDF conversion (requires system deps)

# DOCX generation
python-docx = "^1.1"        # For DOCX conversion

# CSV - built-in csv module (no new dependency)
# Markdown - pass-through (no dependency)
```

**Docker System Dependencies (for WeasyPrint):**
- libpango-1.0-0
- libcairo2
- libgdk-pixbuf2.0-0
- (and their dependencies, ~50MB total)

## Related Decisions

- [ADR-001](./adr-001-replace-universal-converter.md) - Decision to replace universal converter
- [Decision Log](../decision_log.md) - Process decisions including library selection rationale
- [Generator Architecture](../converter_architecture.md) - Architecture using these libraries

## Notes

All library selections were made after in-depth research comparing alternatives. Each library was evaluated on:
- Performance benchmarks
- Maintenance status and community size
- Feature support for our use cases
- Docker footprint impact
- License compatibility
- Documentation quality

The selections prioritize:
1. **Template support** (critical for DOCX)
2. **Pipeline efficiency** (reusing HTML conversion)
3. **Maintainability** (active communities, good documentation)
4. **Docker size** (significant reduction from previous implementation)
