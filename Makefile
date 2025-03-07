.PHONY: setup install run join record detect-audio clean help docker-build docker-run docker-help

# Default target
help:
	@echo "Google Meet Guest Joiner - Makefile"
	@echo "-------------------"
	@echo "Available commands:"
	@echo "  make setup        - Set up environment and install dependencies"
	@echo "  make install      - Install dependencies only"
	@echo "  make join URL=X NAME=Y - Join a Google Meet as guest"
	@echo "  make record URL=X NAME=Y - Record a Google Meet session"
	@echo "  make detect-audio - Detect available audio devices for recording"
	@echo "  make clean        - Remove temp files and __pycache__"
	@echo "  make docker-build - Build the Docker image"
	@echo "  make docker-run   - Run the bot using Docker"
	@echo "  make docker-help  - Show Docker usage"

# Setup environment
setup:
	@echo "Setting up environment..."
	python -m venv venv
	@echo "Installing dependencies..."
	$(MAKE) install
	@echo "Creating directories..."
	mkdir -p recordings screenshots

# Install dependencies
install:
	$(PYTHON) -m pip install -r requirements.txt

# Join a Google Meet
join:
ifndef URL
	@echo "URL is required. Usage: make join URL=https://meet.google.com/xyz NAME='Your Name' DURATION=60"
else
ifndef NAME
	@echo "NAME is required. Usage: make join URL=https://meet.google.com/xyz NAME='Your Name' DURATION=60"
else
	$(PYTHON) google_meet_guest.py $(URL) "$(NAME)" $(if $(DURATION),--duration $(DURATION)) $(if $(DEBUG),--debug)
endif
endif

# Record a meeting
record:
ifndef URL
	@echo "URL is required. Usage: make record URL=https://meet.google.com/xyz NAME='Your Name'"
else
ifndef NAME
	@echo "NAME is required. Usage: make record URL=https://meet.google.com/xyz NAME='Your Name'"
else
	$(PYTHON) google_meet_guest.py $(URL) "$(NAME)" --record $(if $(DEBUG),--debug) $(if $(DURATION),--duration $(DURATION))
endif
endif

# Detect audio devices
detect-audio:
	$(PYTHON) detect_audio_devices.py

# Clean up
clean:
	rm -rf __pycache__
	find . -name "*.pyc" -delete

# Docker commands
docker-build:
	docker build -t google-meet-bot .

docker-run:
ifndef URL
	@echo "URL is required. Usage: make docker-run URL=https://meet.google.com/xyz NAME='Your Name'"
else
ifndef NAME
	@echo "NAME is required. Usage: make docker-run URL=https://meet.google.com/xyz NAME='Your Name'"
else
	docker run --rm \
		-v "$(shell pwd)/recordings:/app/recordings" \
		-v "$(shell pwd)/screenshots:/app/screenshots" \
		google-meet-bot $(URL) "$(NAME)" $(if $(RECORD),--record) $(if $(DEBUG),--debug) $(if $(DURATION),--duration $(DURATION))
endif
endif

docker-help:
	@echo "Docker Usage:"
	@echo "  1. Build the image:   make docker-build"
	@echo "  2. Run the bot:       make docker-run URL=https://meet.google.com/xyz NAME='Your Name'"
	@echo "  Options:"
	@echo "    RECORD=1           Enable recording"
	@echo "    DEBUG=1            Enable debug mode"
	@echo "    DURATION=minutes   Set meeting duration (default: 60)"

# Determine which python command to use
PYTHON=python
ifeq ($(OS),Windows_NT)
    VENV_PYTHON=venv\Scripts\python.exe
else
    VENV_PYTHON=venv/bin/python
endif

# Use the venv Python if it exists
ifneq ($(wildcard $(VENV_PYTHON)),)
    PYTHON=$(VENV_PYTHON)
endif
