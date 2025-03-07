#!/bin/bash

# Error handling
set -e

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Build the Docker image if not already built
echo "Building Docker image..."
docker build -t google-meet-bot .

# Parse flags and arguments
DEBUG_FLAG=""
RECORD_FLAG=""
DURATION="60"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --debug) DEBUG_FLAG="--debug"; shift ;;
        --record) RECORD_FLAG="--record"; shift ;;
        --duration) DURATION="$2"; shift 2 ;;
        *) break ;;
    esac
done

# Check if we have meeting URL and name
if [ "$#" -lt 2 ]; then
    echo "Usage: ./docker-run.sh [--debug] [--record] [--duration minutes] <meeting_url> \"Your Name\""
    exit 1
fi

URL="$1"
NAME="$2"

echo "Starting Google Meet bot in Docker container..."
echo "Meeting URL: $URL"
echo "Display name: $NAME"
echo "Duration: $DURATION minutes"

# Run the container with appropriate volumes and command
docker run --rm \
    -v "$(pwd)/recordings:/app/recordings" \
    -v "$(pwd)/screenshots:/app/screenshots" \
    google-meet-bot "$URL" "$NAME" \
    $DEBUG_FLAG $RECORD_FLAG --duration "$DURATION"

echo "Docker container has finished execution."
