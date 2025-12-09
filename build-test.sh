#!/bin/bash

# Build and run chat-a-doc test container
# This script builds the container and runs it with test configuration

set -e

# Configuration
CONTAINER_NAME="chat-a-doc-test"
IMAGE_NAME="chat-a-doc-test"
HOST_PORT=8080
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_OUTPUT_DIR="${PROJECT_ROOT}/tests/test_output"
ALLOWED_ROOT="/app/files"

echo "=== Chat-A-Doc Test Container Builder ==="
echo "Project root: $PROJECT_ROOT"
echo "Test output dir: $TEST_OUTPUT_DIR"
echo "Container name: $CONTAINER_NAME"
echo "Host port: $HOST_PORT"
echo

# Check if test output directory exists
if [ ! -d "$TEST_OUTPUT_DIR" ]; then
    echo "ERROR: Test output directory not found: $TEST_OUTPUT_DIR"
    echo "Please run tests first to create the directory structure."
    exit 1
fi

# Stop and remove existing container if it exists
echo "Stopping and removing existing test container (if any)..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Build the container
echo "Building container image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" .

# Run the container with test configuration
echo "Starting test container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:8080" \
    -v "$TEST_OUTPUT_DIR:$ALLOWED_ROOT" \
    -e ALLOWED_ROOT="$ALLOWED_ROOT" \
    -e USE_HTTP_LINKS=true \
    -e HTTP_BASE_URL="http://localhost:$HOST_PORT" \
    "$IMAGE_NAME"

# Wait for container to start
echo "Waiting for container to start..."
sleep 2

# Verify container is running
if ! docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Container failed to start"
    docker logs "$CONTAINER_NAME" 2>&1 | head -20
    exit 1
fi

echo
echo "✅ Test container '$CONTAINER_NAME' is running successfully!"
echo "📍 Access URL: http://localhost:$HOST_PORT"
echo "📁 Files directory: $TEST_OUTPUT_DIR"
echo "🔗 HTTP links enabled: http://localhost:$HOST_PORT/files/"
echo
echo "To stop the container: docker stop $CONTAINER_NAME"
echo "To view logs: docker logs $CONTAINER_NAME"
echo "To follow logs: docker logs -f $CONTAINER_NAME"
