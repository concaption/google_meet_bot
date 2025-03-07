FROM python:3.11-slim

# Install required packages, Chrome, and FFmpeg
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    ffmpeg \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY *.py /app/
COPY README.md /app/

# Create directories for recordings and screenshots
RUN mkdir -p recordings screenshots

# Set environment variable to run Chrome in headless mode
ENV DISPLAY=:99

# Default command runs with arguments from docker run command
ENTRYPOINT ["python", "google_meet_guest.py"]
CMD ["--help"]
