"""
Audio Device Detection Helper

Lists available audio devices that could be used for recording.
"""
import subprocess
import platform
import sys
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_ffmpeg_installed():
    """Check if FFmpeg is available on the system."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False
        )
        return True
    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
        return False

def list_windows_audio_devices():
    """List audio input devices available on Windows."""
    print("\n=== Windows Audio Devices ===")
    
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
        in_audio_section = False
        
        for line in output.split('\n'):
            # Print all device-related output for reference
            if "DirectShow" in line or "Alternative name" in line:
                print(line)
            
            if "DirectShow audio devices" in line:
                capture_audio = True
                in_audio_section = True
            elif "DirectShow video devices" in line:
                capture_audio = False
            
            if capture_audio and "Alternative name" in line:
                try:
                    device_name = line.split('"')[1]
                    audio_devices.append(device_name)
                except:
                    pass
        
        if audio_devices:
            print("\nDetected audio devices:")
            for i, device in enumerate(audio_devices):
                print(f"  {i+1}. {device}")
            
            print("\nRecommended devices for system audio capture:")
            found_recommended = False
            for device in audio_devices:
                # Check for common system audio capture device names
                if any(name.lower() in device.lower() for name in [
                    "stereo mix", "wave out", "what u hear", "audio output", "virtual audio", 
                    "cable output", "voicemeeter", "audio render"
                ]):
                    print(f"  * {device} - Use with: audio=\"{device}\"")
                    found_recommended = True
            
            if not found_recommended:
                print("  * No standard system audio capture devices found")
                print("  * You may need to enable 'Stereo Mix' in your sound settings")
                print("  * Or install virtual audio cable software")
        
        if not in_audio_section:
            print("No audio devices section found in FFmpeg output.")
    
    except Exception as e:
        print(f"Error detecting audio devices: {e}")

def list_macos_audio_devices():
    """List audio input devices available on macOS."""
    print("\n=== macOS Audio Devices ===")
    
    try:
        # List available devices using FFmpeg's avfoundation
        command = ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Output from FFmpeg will be in stderr
        output = result.stderr
        print(output)
        
        print("\nUsage for recording with FFmpeg:")
        print("  - For screen: -f avfoundation -i 1 ...")
        print("  - For screen with audio: -f avfoundation -i 1:0 ...")
        print("  - Replace numbers with device indices from the list above")
        print("\nOn macOS, you may need to install a virtual audio device like BlackHole")
        print("for capturing system audio: https://github.com/ExistentialAudio/BlackHole")
    
    except Exception as e:
        print(f"Error detecting macOS audio devices: {e}")

def list_linux_audio_devices():
    """List audio input devices available on Linux."""
    print("\n=== Linux Audio Devices ===")
    
    # Try PulseAudio
    try:
        print("Checking PulseAudio sources...")
        command = ["pactl", "list", "sources"]
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(result.stdout)
            
            # Find monitor sources which are good for system audio
            print("\nPotential system audio capture devices:")
            for line in result.stdout.split('\n'):
                if "monitor" in line.lower() and "name:" in line.lower():
                    device = line.split("name:")[1].strip()
                    print(f"  * {device} - Use with FFmpeg: -f pulse -i {device}")
        else:
            print("PulseAudio not available or error listing sources")
    
    except Exception as e:
        print(f"Error checking PulseAudio: {e}")
    
    # Try ALSA devices
    try:
        print("\nChecking ALSA devices...")
        command = ["arecord", "-L"]
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            print(result.stdout)
            print("\nUsage for recording with FFmpeg:")
            print("  * Use -f alsa -i <device> when using ALSA devices")
        else:
            print("ALSA tools not available or error listing devices")
    
    except Exception:
        print("Error checking ALSA devices")

def main():
    parser = argparse.ArgumentParser(description="Detect available audio devices for recording")
    parser.add_argument("--platform", help="Force detection for specific platform (windows, macos, linux)")
    
    args = parser.parse_args()
    
    if not check_ffmpeg_installed():
        return 1
    
    print("Detecting audio devices for FFmpeg recording...")
    
    target_platform = args.platform.lower() if args.platform else platform.system().lower()
    
    if target_platform in ["windows", "win32"]:
        list_windows_audio_devices()
    elif target_platform in ["macos", "darwin"]:
        list_macos_audio_devices()
    elif target_platform in ["linux"]:
        list_linux_audio_devices()
    else:
        print(f"Unsupported platform: {target_platform}")
        return 1
    
    print("\nTIP: If you need to capture system audio:")
    print("- Windows: Enable 'Stereo Mix' in sound settings or use software like VB-Cable")
    print("- macOS: Install BlackHole or similar audio routing software")
    print("- Linux: Use PulseAudio monitor sources or pavucontrol to set up audio routing")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
