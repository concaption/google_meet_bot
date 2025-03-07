#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Process arguments
DEBUG_FLAG=""
RECORD_FLAG=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --debug) DEBUG_FLAG="--debug"; shift ;;
        --record) RECORD_FLAG="--record"; shift ;;
        *) break ;;
    esac
done

# Check if we have URL and name
if [ "$#" -lt 2 ]; then
    echo "Usage: ./run.sh [--debug] [--record] <meeting_url> \"Your Name\" [duration]"
    exit 1
fi

URL="$1"
NAME="$2"
DURATION=${3:-60} # Default to 60 minutes if not specified

echo "Joining meeting: $URL"
echo "Display name: $NAME"
echo "Duration: $DURATION minutes"
if [ ! -z "$DEBUG_FLAG" ]; then echo "Debug mode enabled"; fi
if [ ! -z "$RECORD_FLAG" ]; then echo "Recording enabled"; fi

# Run the script
python google_meet_guest.py "$URL" "$NAME" $DEBUG_FLAG $RECORD_FLAG --duration "$DURATION"
