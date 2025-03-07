#!/usr/bin/env python
"""
Audio Extraction Utility

Extract audio from meeting recordings to MP3 format.
"""
import os
import sys
import subprocess
import argparse
import glob
import platform
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def find_latest_recording(directory="./recordings"):
    """Find the latest MP4 recording file."""
    path = Path(directory)
    if not path.exists():
        logger.error(f"Directory not found: {directory}")
        return None
        
    mp4_files = list(path.glob("*.mp4"))
    if not mp4_files:
        logger.warning(f"No MP4 files found in {directory}")
        return None
        
    # Get the most recently modified file
    latest_file = max(mp4_files, key=lambda p: p.stat().st_mtime)
    return latest_file

def extract_audio(video_file, output_file=None, quality=4):
    """Extract audio from video to MP3 format."""
    if not video_file.exists():
        logger.error(f"Video file not found: {video_file}")
        return False
        
    # If output file not specified, use same name but with .mp3 extension
    if not output_file:
        output_file = video_file.with_suffix(".mp3")
    
    logger.info(f"Extracting audio from: {video_file}")
    logger.info(f"Output file: {output_file}")
    
    # Try first extraction method
    command = [
        "ffmpeg",
        "-i", str(video_file),
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-q:a", str(quality),  # Quality setting (0-9, lower is better)
        "-y",  # Overwrite output file
        str(output_file)
    ]
    
    logger.info(f"Running command: {' '.join(command)}")
    
    try:
        # Use CREATE_NO_WINDOW on Windows to avoid command window popup
        creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            creationflags=creation_flags
        )
        
        if process.returncode == 0:
            if output_file.exists():
                file_size = output_file.stat().st_size
                logger.info(f"Audio extraction successful! Output size: {file_size / 1024:.2f} KB")
                return True
        
        # If first method failed, try alternative method
        logger.warning(f"First extraction attempt failed: {process.stderr}")
        logger.info("Trying alternative extraction method...")
        
        alt_command = [
            "ffmpeg",
            "-i", str(video_file),
            "-vn",  # No video
            "-ar", "44100",  # Audio sample rate
            "-ac", "2",  # Stereo
            "-b:a", "192k",  # Audio bitrate
            "-y",  # Overwrite output file
            str(output_file)
        ]
        
        logger.info(f"Running command: {' '.join(alt_command)}")
        
        alt_process = subprocess.run(
            alt_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            creationflags=creation_flags
        )
        
        if alt_process.returncode == 0 and output_file.exists():
            file_size = output_file.stat().st_size
            logger.info(f"Audio extraction successful with alternative method! Output size: {file_size / 1024:.2f} KB")
            return True
        else:
            logger.error(f"All extraction attempts failed: {alt_process.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Error during audio extraction: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Extract audio from video recordings")
    parser.add_argument("-i", "--input", help="Input video file path")
    parser.add_argument("-o", "--output", help="Output MP3 file path")
    parser.add_argument("-d", "--dir", default="./recordings", help="Directory to search for recordings")
    parser.add_argument("-q", "--quality", type=int, default=4, help="MP3 quality (0-9, lower is better)")
    parser.add_argument("-l", "--latest", action="store_true", help="Extract from the latest recording")
    
    args = parser.parse_args()
    
    if args.latest:
        video_file = find_latest_recording(args.dir)
        if not video_file:
            logger.error("No recordings found")
            return 1
    elif args.input:
        video_file = Path(args.input)
    else:
        parser.print_help()
        logger.error("Please specify either --input or --latest")
        return 1
    
    output_file = Path(args.output) if args.output else None
    
    success = extract_audio(video_file, output_file, args.quality)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
