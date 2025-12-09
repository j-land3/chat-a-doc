"""chat_a_doc package initialization."""

import asyncio
import sys

from . import server


def main():
    """Run the chat-a-doc server."""
    try:
        # Ensure stdout/stderr are unbuffered for Docker
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
        asyncio.run(server.main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error starting chat-a-doc server: {e}", file=sys.stderr)
        sys.exit(1)


# Optionally expose other important items at package level
__all__ = ["main", "server"]
