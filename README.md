# Google Meet Guest Joiner - Simplified Implementation

This directory contains a simplified, standalone implementation for joining Google Meet sessions as a guest. The implementation incorporates all the fixes and improvements developed throughout the project.

## Features

- Single-file, easy-to-understand implementation
- Focused solely on guest joining functionality
- Multiple fallback strategies for handling UI variations
- Optional meeting recording capability using FFmpeg
- Captures screenshots for debugging
- Requires no configuration files

## Requirements

- Python 3.7+
- Selenium
- webdriver-manager (optional but recommended)
- Chrome browser installed
- FFmpeg (optional, required for recording)

## Installation

Install required Python packages:

```bash
pip install selenium webdriver-manager
```

If you want to use the recording feature, you'll also need to install FFmpeg:

### Windows
1. Download from [FFmpeg.org](https://ffmpeg.org/download.html) or install via [Chocolatey](https://chocolatey.org/): `choco install ffmpeg`
2. Add FFmpeg to your PATH environment variable

### macOS
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

## Usage

To use the simplified Google Meet guest joiner:

```bash
python google_meet_guest.py <meet_url> "<your_display_name>" [options]
```

### Examples

Join a meeting with URL:
```bash
python google_meet_guest.py https://meet.google.com/abc-def-ghi "John Doe"
```

Join a meeting with just the code:
```bash
python google_meet_guest.py abc-def-ghi "John Doe"
```

Join with visible browser (debug mode):
```bash
python google_meet_guest.py abc-def-ghi "John Doe" --debug
```

Join and record the meeting:
```bash
python google_meet_guest.py abc-def-ghi "John Doe" --record
```

### Command-line Options

- `--duration N` - Stay in the meeting for N minutes (default: 60)
- `--debug` - Run in debug mode (browser window is visible)
- `--record` - Record the meeting (requires FFmpeg)
- `--recording-dir DIR` - Directory to save recordings (default: ./recordings)

## How It Works

The script works in these steps:

1. Initialize Chrome browser with anti-detection features
2. Navigate to the Google Meet URL
3. Find and fill the name input field using multiple strategies
4. Turn off microphone and camera
5. Click the "Ask to join" button
6. Start recording the meeting (if enabled)
7. Stay in the meeting for the specified duration
8. Stop recording and leave the meeting cleanly

## Recording Features

The meeting recording functionality uses FFmpeg to capture both screen and audio:

### Required Setup for Audio Recording

To properly record system audio during meetings, additional setup may be required:

#### Windows
1. **Enable Stereo Mix**: 
   - Right-click sound icon in taskbar -> Sound settings
   - Go to Input -> Enable Stereo Mix
   - If Stereo Mix is not available, try these alternatives:
     - Install a virtual audio device like [VB-Cable](https://vb-audio.com/Cable/)
     - Use a software mixer like [Voicemeeter](https://vb-audio.com/Voicemeeter/)

#### macOS
1. **Install audio routing software**:
   - [BlackHole](https://github.com/ExistentialAudio/BlackHole) (recommended)
   - [Soundflower](https://github.com/mattingalls/Soundflower) (alternative)
   - [Loopback](https://rogueamoeba.com/loopback/) (paid option)

#### Linux
1. **Setup PulseAudio loopback**:
   - Use `pavucontrol` to direct audio to a monitor source
   - Or use `pactl load-module module-loopback`

### Detecting Available Audio Devices

Run the included helper script to list available audio devices on your system:

```bash
python detect_audio_devices.py
```

### Troubleshooting Recording Issues

If recording starts but stops immediately:

1. Check if any audio devices are available:
   - Run `detect_audio_devices.py` to list devices
   - Ensure an audio loopback device is set up

2. Try recording without audio:
   - The script will automatically fall back to video-only recording if audio fails
   - Recording errors will be shown in the log

3. Verify FFmpeg is working:
   - Run `ffmpeg -version` to check installation
   - Try a simple test recording: `ffmpeg -f gdigrab -i desktop -c:v libx264 test.mp4`

## Audio Extraction

By default, when you use the recording feature, the script will:
1. Record the meeting as an MP4 video file
2. Automatically extract the audio to a separate MP3 file

If you want to manually extract audio from an existing recording:

```bash
# Extract audio from the latest recording
make extract-audio
```

You can also extract audio from any video using FFmpeg directly:

```bash
ffmpeg -i "recordings/your-recording.mp4" -vn -acodec libmp3lame -q:a 4 "recordings/your-recording.mp3"
```

## Recording Implementation

The meeting recording functionality:

- Uses FFmpeg for efficient video/audio capture with minimal CPU usage
- Records both screen and audio
- Automatically detects system configuration
- Saves recordings with timestamped filenames
- Handles graceful start and stop of recording process

## Screenshots and Recordings

- Screenshots are saved to `./screenshots/` directory
- Recordings are saved to `./recordings/` (or specified directory)

## Screenshots

The script saves screenshots at important steps to the `./screenshots` directory to help with debugging:

- `01-initial-page.png` - The initial Google Meet page
- `01a-name-filled-js.png` - After filling name with JavaScript
- `01b-name-filled-selenium.png` - After filling name with Selenium
- `01c-name-filled-xpath.png` - After filling name with XPath
- `02-before-join-click.png` - Before clicking join button
- `02a-join-clicked-js.png` - After clicking join button with JavaScript
- `02b-join-clicked-selenium.png` - After clicking join button with Selenium
- `02c-join-clicked-xpath.png` - After clicking join button with XPath
- `03-after-join.png` - After joining the meeting
- Various error screenshots if problems occur

## Differences from Main Implementation

This simplified implementation:
- Combines all functionality in one file for easier understanding
- Focuses exclusively on guest joining (no login required)
- Has more extensive debugging features
- Is designed to be standalone (doesn't rely on other modules)

## Recent Improvements

- Added specific targeting for the Google Meet "Ask to join" button using exact class names and structure
- Enhanced JavaScript button detection to locate buttons by nested span elements
- Added more precise XPath queries to handle the current Google Meet UI structure
