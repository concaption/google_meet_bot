.PHONY: setup install run join record detect-audio clean help

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
