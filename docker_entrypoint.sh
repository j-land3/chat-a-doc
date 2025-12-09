#!/bin/bash
# Entrypoint script that runs the HTTP server
# The HTTP server bridges HTTP requests to the stdio-based MCP server

# Run the HTTP server (which will handle HTTP requests and bridge to MCP server)
exec python3 -m chat_a_doc.http_server
