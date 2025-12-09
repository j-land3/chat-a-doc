# Secure Dockerfile for chat-a-doc
FROM python:3.11-slim-bookworm

# Install system dependencies
# WeasyPrint dependencies for PDF generation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (default UID 1000, can be overridden at runtime with --user)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy source
COPY src/ /app/src/
COPY pyproject.toml /app/

# Copy entrypoint script
COPY docker_entrypoint.sh /app/docker_entrypoint.sh
RUN chmod +x /app/docker_entrypoint.sh && \
    chown appuser:appuser /app/docker_entrypoint.sh

# Create a minimal README if pyproject.toml references it (for build)
RUN echo "# chat-a-doc" > /app/README.md || true

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir pyyaml "mcp>=1.2.1" \
    "markdown>=3.5" "html2text>=2024.2.26" "weasyprint>=60" "python-docx>=1.1"

# Create restricted files directory
RUN mkdir -p /app/files && \
    chmod 700 /app/files && \
    chown -R appuser:appuser /app

# Set environment variables
ENV ALLOWED_ROOT=/app/files
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/usr/local/lib/python3.11/site-packages
ENV PATH="/usr/bin:${PATH}"
ENV HTTP_PORT=8080

# Switch to non-root user
USER appuser

# Expose HTTP endpoint for MCP server
EXPOSE 8080

# Container runs HTTP server that bridges to stdio MCP server
WORKDIR /app
ENTRYPOINT ["/app/docker_entrypoint.sh"]
