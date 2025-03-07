#!/bin/bash

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Google Meet Guest Joiner Setup${NC}"
echo "-------------------"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo -e "${YELLOW}Detected Python version: ${PYTHON_VERSION}${NC}"

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 7 ]; then
    echo -e "${RED}Python 3.7 or higher is required. Please update your Python installation.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment. Please install venv package.${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

# Install requirements
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies.${NC}"
    exit 1
fi

# Check FFmpeg installation for recording functionality
echo -e "${YELLOW}Checking FFmpeg installation...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    echo -e "${GREEN}FFmpeg is installed: ${FFMPEG_VERSION}${NC}"
else
    echo -e "${YELLOW}FFmpeg not found. Recording functionality will not work.${NC}"
    echo -e "${YELLOW}To install FFmpeg:${NC}"
    echo "  - Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  - macOS: brew install ffmpeg"
    echo "  - Windows: Download from https://ffmpeg.org/download.html"
fi

# Create directories for recording and screenshots
echo -e "${YELLOW}Creating directories for recordings and screenshots...${NC}"
mkdir -p recordings screenshots

echo -e "\n${GREEN}Setup Complete!${NC}"
echo -e "To join a Google Meet:"
echo -e "  1. ${YELLOW}source venv/bin/activate${NC}"
echo -e "  2. ${YELLOW}python google_meet_guest.py <meeting_url> \"Your Name\"${NC}"
echo -e "\nTo record a meeting:"
echo -e "  ${YELLOW}python google_meet_guest.py <meeting_url> \"Your Name\" --record${NC}"
echo -e "\nTo detect available audio devices:"
echo -e "  ${YELLOW}python detect_audio_devices.py${NC}"
