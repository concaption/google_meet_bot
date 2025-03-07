"""
Meeting Recorder Module

Provides functionality to record screen and audio during meetings.
Uses FFmpeg for efficient video/audio capture.
"""
import os
import subprocess
import platform
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class MeetingRecorder:
    """Records screen and audio during meetings."""
    
    def __init__(self, output_dir: str = "./recordings", prefix: str = "meeting", meeting_id: str = None):
        """Initialize the recorder.
        
        Args:
            output_dir: Directory to save recordings
            prefix: Prefix for recording filenames
            meeting_id: Meeting ID to include in the filename
        """
        self.output_dir = Path(output_dir)
        self.prefix = prefix
        self.meeting_id = meeting_id if meeting_id else "unknown"
        self.recording = False
        self.recording_process = None
        self.current_recording_path = None
        self.current_audio_path = None
        self.start_time = None
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if FFmpeg is installed
        self._check_ffmpeg_installed()
    
    def _check_ffmpeg_installed(self) -> bool:
        """Check if FFmpeg is available on the system."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False
            )
            logger.info("FFmpeg is installed and accessible")
            return True
        except FileNotFoundError:
            logger.warning(
                "FFmpeg not found. Recording will be disabled. "
                "Please install FFmpeg (https://ffmpeg.org/download.html) "
                "and make sure it's in your PATH."
            )
            return False
    
    def _get_screen_resolution(self) -> Tuple[int, int]:
        """Get the screen resolution for recording."""
        try:
            if platform.system() == "Windows":
                from win32api import GetSystemMetrics
                width = GetSystemMetrics(0)
                height = GetSystemMetrics(1)
                return width, height
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"], 
                    capture_output=True, 
                    text=True
                )
                output = result.stdout
                resolution_line = [line for line in output.split('\n') if "Resolution" in line][0]
                resolution = resolution_line.split(':')[1].strip()
                width, height = map(int, resolution.split(' x '))
                return width, height
            elif platform.system() == "Linux":
                result = subprocess.run(
                    ["xrandr"], 
                    capture_output=True, 
                    text=True
                )
                output = result.stdout
                current_line = [line for line in output.split('\n') if "*" in line][0]
                resolution = current_line.split()[0]
                width, height = map(int, resolution.split('x'))
                return width, height
            else:
                # Default resolution if detection fails
                return 1920, 1080
        except Exception as e:
            logger.warning(f"Failed to detect screen resolution: {e}")
            return 1920, 1080  # Default fallback resolution
    
    def _get_audio_source(self) -> Optional[str]:
        """Get the appropriate audio source based on the platform."""
        system = platform.system()
        
        if system == "Windows":
            # First try to detect available audio devices
            try:
                # List available DirectShow devices
                command = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                # Check output for available audio devices
                output = result.stderr
                audio_devices = []
                capture_audio = False
                
                for line in output.split('\n'):
                    if "DirectShow audio devices" in line:
                        capture_audio = True
                    elif "DirectShow video devices" in line or not line:
                        capture_audio = False
                    
                    if capture_audio and "Alternative name" in line:
                        device_name = line.split('"')[1]
                        audio_devices.append(device_name)
                
                if audio_devices:
                    logger.info(f"Found audio devices: {audio_devices}")
                    
                    # Look for common audio devices used for system sound capture
                    for device in audio_devices:
                        # Check for common system audio capture device names
                        if any(name.lower() in device.lower() for name in [
                            "stereo mix", "wave out", "audio output", "virtual audio", 
                            "cable output", "voicemeeter", "audio render"
                        ]):
                            logger.info(f"Selected audio device: {device}")
                            return f"audio={device}"
                    
                    # If no ideal device found, try the first audio device
                    if audio_devices:
                        logger.info(f"Using first available audio device: {audio_devices[0]}")
                        return f"audio={audio_devices[0]}"
                
                logger.warning("No suitable audio input devices found, recording without audio")
                return None
                
            except Exception as e:
                logger.warning(f"Error detecting audio devices: {e}")
                logger.warning("Falling back to recording without audio")
                return None
        
        elif system == "Darwin":  # macOS
            # macOS approach - use default audio device
            return "0"  # Default audio input on macOS
        
        elif system == "Linux":
            try:
                # Try to detect PulseAudio devices
                command = ["pactl", "list", "sources"]
                result = subprocess.run(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True, 
                    check=False
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if "monitor" in line.lower() and "name:" in line.lower():
                            device = line.split("name:")[1].strip()
                            logger.info(f"Found PulseAudio monitor device: {device}")
                            return device
                
                # Fallback to default
                return "default"
                
            except Exception:
                logger.warning("Error detecting PulseAudio devices, using default")
                return "default"
        
        else:
            logger.warning(f"Unsupported platform for audio capture: {system}")
            return None
    
    def _get_ffmpeg_command(self) -> list:
        """Build the FFmpeg command for recording."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Include meeting ID in the filename
        filename = f"{self.prefix}_{self.meeting_id}_{timestamp}.mp4"
        self.current_recording_path = self.output_dir / filename
        
        # Also set the path for audio extraction
        self.current_audio_path = self.output_dir / f"{self.prefix}_{self.meeting_id}_{timestamp}.mp3"
        
        width, height = self._get_screen_resolution()
        audio_source = self._get_audio_source()
        
        system = platform.system()
        
        if system == "Windows":
            # GDI grabber for Windows
            command = [
                "ffmpeg",
                "-f", "gdigrab",
                "-framerate", "15",  # Lower framerate for less CPU usage
                "-video_size", f"{width}x{height}",
                "-i", "desktop",
            ]
            
            # Add audio if we have a source
            if (audio_source):
                command.extend([
                    "-f", "dshow",
                    "-i", audio_source,
                ])

        elif system == "Darwin":  # macOS
            # AVFoundation grabber for macOS
            command = [
                "ffmpeg",
                "-f", "avfoundation",
                "-framerate", "15",
                "-video_size", f"{width}x{height}",
                "-i", "1:0",  # "1" is screen, "0" is system audio
            ]
            
        elif system == "Linux":
            # X11grab for Linux
            command = [
                "ffmpeg",
                "-f", "x11grab",
                "-framerate", "15",
                "-video_size", f"{width}x{height}",
                "-i", ":0.0",
            ]
            
            # Add audio if we have a source
            if audio_source:
                command.extend([
                    "-f", "pulse",
                    "-i", audio_source,
                ])
            
        else:
            logger.error(f"Unsupported platform for recording: {system}")
            return []
        
        # Common output options for any platform
        command.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",  # Fast encoding for minimal CPU usage
            "-crf", "28",  # Compression quality (higher = smaller file)
            "-pix_fmt", "yuv420p",  # Compatible pixel format
            "-c:a", "aac",
            "-b:a", "128k",  # Audio bitrate
            str(self.current_recording_path)
        ])
        
        return command
    
    def start_recording(self) -> bool:
        """Start recording the meeting."""
        if self.recording:
            logger.warning("Recording is already in progress")
            return False
        
        try:
            command = self._get_ffmpeg_command()
            if not command:
                logger.error("Failed to create FFmpeg command")
                return False
            
            logger.info("Starting recording with command: %s", command)
            
            # First, try with audio
            try:
                # Start the FFmpeg process
                self.recording_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True
                )
                
                # Wait a short time to check for immediate failures
                time.sleep(1)
                
                # Verify that recording started successfully
                if self.recording_process.poll() is not None:
                    exit_code = self.recording_process.poll()
                    stderr_output = self.recording_process.stderr.read() if self.recording_process.stderr else "No error output"
                    logger.error(f"Recording process failed with audio: {stderr_output}")
                    
                    # If there's an audio error, try again without audio
                    if "audio" in stderr_output.lower() and "error" in stderr_output.lower():
                        logger.warning("Audio capture failed, trying again without audio...")
                        
                        # Create command without audio
                        video_only_command = [x for x in command]
                        # Remove any audio-related parameters - this is a simplistic approach
                        # but should remove the -f dshow and -i audio=... parameters
                        if "-f" in video_only_command and "dshow" in video_only_command:
                            idx = video_only_command.index("-f")
                            if idx + 2 < len(video_only_command) and "audio" in video_only_command[idx + 2]:
                                # Remove -f dshow -i audio=...
                                del video_only_command[idx:idx+3]
                        
                        logger.info(f"Trying video-only command: {video_only_command}")
                        
                        self.recording_process = subprocess.Popen(
                            video_only_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            text=True
                        )
                        
                        time.sleep(1)
                        if self.recording_process.poll() is not None:
                            exit_code = self.recording_process.poll()
                            stderr_output = self.recording_process.stderr.read() if self.recording_process.stderr else "No error output"
                            logger.error(f"Video-only recording also failed with code {exit_code}: {stderr_output}")
                            self.recording_process = None
                            return False
                    else:
                        # Not an audio error, so just fail
                        self.recording_process = None
                        return False
            except Exception as e:
                logger.error(f"Failed to start recording: {e}")
                if self.recording_process:
                    try:
                        self.recording_process.terminate()
                    except:
                        pass
                    self.recording_process = None
                return False
            
            # If we get here, one of the recording attempts worked
            self.recording = True
            self.start_time = datetime.now()
            logger.info("Recording started successfully at %s", self.start_time)
            logger.info("Recording to: %s", self.current_recording_path)
            
            # Start a verification thread to periodically check if process is still running
            self._start_verification_thread()
            
            return True
            
        except Exception as e:
            logger.error("Failed to start recording: %s", str(e))
            self.recording = False
            self.recording_process = None
            return False

    def _start_verification_thread(self):
        """Start a thread to verify recording is still working."""
        import threading
        
        def verify_recording():
            while self.recording and self.recording_process:
                # Check if process is still running
                if self.recording_process.poll() is not None:
                    exit_code = self.recording_process.poll()
                    stderr_output = self.recording_process.stderr.read() if self.recording_process.stderr else "No error output"
                    logger.error(f"Recording process terminated unexpectedly with code {exit_code}. Error: {stderr_output}")
                    self.recording = False
                    break
                
                # Log recording status every minute
                current_duration = datetime.now() - self.start_time
                logger.info(f"Recording in progress. Duration: {current_duration}")
                
                # Check if output file is growing (every 60 seconds)
                if self.current_recording_path.exists():
                    file_size = self.current_recording_path.stat().st_size
                    logger.info(f"Current recording file size: {file_size / (1024*1024):.2f} MB")
                else:
                    logger.warning("Recording file not created yet or missing")
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
        
        # Start verification thread
        verification_thread = threading.Thread(target=verify_recording, daemon=True)
        verification_thread.start()
        logger.info("Started recording verification thread")
    
    def stop_recording(self) -> bool:
        """Stop the current recording."""
        if not self.recording or not self.recording_process:
            logger.warning("No active recording to stop")
            return False
        
        try:
            logger.info("Stopping recording")
            
            # On Windows, we need to send 'q' to ffmpeg to stop gracefully
            if platform.system() == "Windows":
                try:
                    # Send 'q' to stdin to gracefully quit ffmpeg
                    self.recording_process.communicate(input='q', timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("FFmpeg process didn't respond to 'q' command, terminating...")
                    self.recording_process.terminate()
            else:
                # On Unix-like systems, SIGTERM should gracefully terminate ffmpeg
                self.recording_process.terminate()
            
            # Wait for the process to end
            try:
                self.recording_process.wait(timeout=10)
                logger.info("Recording process terminated cleanly")
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg process didn't terminate, forcing...")
                self.recording_process.kill()
            
            duration = datetime.now() - self.start_time
            logger.info("Recording completed. Duration: %s", duration)
            
            # Check if the recording file exists and has content
            if self.current_recording_path and self.current_recording_path.exists():
                file_size = self.current_recording_path.stat().st_size
                logger.info(f"Recording saved to: {self.current_recording_path} (Size: {file_size / (1024*1024):.2f} MB)")
                
                if file_size > 0:
                    # Extract audio to MP3
                    self._extract_audio_to_mp3()
                else:
                    logger.warning(f"Recording file is empty (0 bytes). Check FFmpeg configuration.")
            else:
                logger.warning("Recording file was not created")
            
            self.recording = False
            self.recording_process = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop recording: {str(e)}")
            return False
    
    def _extract_audio_to_mp3(self) -> bool:
        """Extract audio from video recording to a separate MP3 file."""
        try:
            if not self.current_recording_path or not self.current_recording_path.exists():
                logger.warning("No recording file found to extract audio from")
                return False
                
            logger.info(f"Extracting audio to MP3: {self.current_audio_path}")
            
            # Command to extract audio to MP3
            command = [
                "ffmpeg",
                "-i", str(self.current_recording_path),
                "-vn",  # No video
                "-acodec", "libmp3lame",
                "-q:a", "4",  # Quality setting (0-9, lower is better)
                "-y",  # Overwrite output file if it exists
                str(self.current_audio_path)
            ]
            
            logger.info(f"Running audio extraction command: {command}")
            
            # Run FFmpeg to extract audio
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            if process.returncode == 0:
                if self.current_audio_path.exists():
                    file_size = self.current_audio_path.stat().st_size
                    logger.info(f"Audio extracted to: {self.current_audio_path} (Size: {file_size / 1024:.2f} KB)")
                    return True
                else:
                    logger.warning("Audio extraction completed but file not found")
                    return False
            else:
                # More detailed error logging
                error_output = process.stderr.strip() if process.stderr else "Unknown error"
                logger.warning(f"Audio extraction failed with code {process.returncode}: {error_output}")
                
                # Try a more compatible approach
                logger.info("Trying alternative audio extraction method...")
                alt_command = [
                    "ffmpeg",
                    "-i", str(self.current_recording_path),
                    "-vn",  # No video
                    "-ar", "44100",  # Audio sample rate
                    "-ac", "2",  # Stereo
                    "-b:a", "192k",  # Bitrate
                    "-y",  # Overwrite output file if it exists
                    str(self.current_audio_path)
                ]
                
                logger.info(f"Running alternative extraction command: {alt_command}")
                
                alt_process = subprocess.run(
                    alt_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                
                if alt_process.returncode == 0 and self.current_audio_path.exists():
                    file_size = self.current_audio_path.stat().st_size
                    logger.info(f"Audio extracted with alternative method: {self.current_audio_path} (Size: {file_size / 1024:.2f} KB)")
                    return True
                else:
                    logger.error(f"All audio extraction attempts failed. Last error: {alt_process.stderr}")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}")
            return False
    
    def get_recording_path(self) -> Optional[Path]:
        """Return the path of the current or last recording."""
        return self.current_recording_path
        
    def get_audio_path(self) -> Optional[Path]:
        """Return the path of the extracted audio file."""
        return self.current_audio_path if self.current_audio_path and self.current_audio_path.exists() else None