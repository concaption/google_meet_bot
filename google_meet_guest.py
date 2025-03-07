"""
Minimal Google Meet Guest Integration

This module provides a simplified, standalone implementation for joining
Google Meet sessions as a guest, incorporating all the fixes for reliable operation.
"""
import logging
import time
import os
import argparse
import sys
import threading
from pathlib import Path
from typing import Optional
import re
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import selenium - provide helpful error if not found
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        logger.warning("webdriver_manager not found. Will attempt to use system ChromeDriver.")
except ImportError:
    logger.error("Selenium package not found. Please install it with: pip install selenium")
    sys.exit(1)

# Try to import the meeting recorder
try:
    # First try importing from the same directory
    from meeting_recorder import MeetingRecorder
except ImportError:
    try:
        # Try importing from the current file's directory
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from meeting_recorder import MeetingRecorder
    except ImportError:
        logger.warning("Meeting recorder not found in path. Recording will be disabled.")
        MeetingRecorder = None


def extract_meeting_id(url):
    """Extract meeting ID from Google Meet URL."""
    # Looking for patterns like https://meet.google.com/abc-def-ghi or simply abc-def-ghi
    pattern = r'(?:https?://)?(?:meet\.google\.com/)?([a-z0-9\-]+)(?:\?.*)?'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return "unknown"

class GoogleMeetGuestBot:
    """Simple bot for joining Google Meet as a guest with recording capabilities."""
    
    def __init__(self, display_name="Guest", debug=False, record_meeting=False, recording_output_dir="./recordings"):
        """Initialize the bot with display name and debug mode."""
        self.display_name = display_name
        self.debug = debug
        self.driver = None
        self.wait = None
        self.wait_timeout = 30  # seconds
        
        # Recording settings
        self.record_meeting = record_meeting
        self.recorder = None
        self.meeting_id = None  # Will be set when joining a meeting
        if record_meeting and MeetingRecorder:
            try:
                self.recorder = MeetingRecorder(
                    output_dir=recording_output_dir,
                    prefix=f"meet_"
                )
                logger.info(f"Recording will be saved to: {recording_output_dir}")
            except Exception as e:
                logger.error(f"Failed to initialize meeting recorder: {e}")
                self.record_meeting = False
        
        logger.info(f"Bot initialized: name={display_name}, debug={debug}, recording={record_meeting}")
    
    def initialize_browser(self):
        """Set up the Chrome browser with appropriate options."""
        try:
            options = webdriver.ChromeOptions()
            
            # Configure headless mode based on debug setting
            if not self.debug:
                logger.info("Running in headless mode")
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
            else:
                logger.info("Running in debug mode with visible browser")
                options.add_argument("--start-maximized")
            
            # Essential options for Google Meet
            options.add_argument("--use-fake-ui-for-media-stream")
            options.add_argument("--use-fake-device-for-media-stream")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Set a recent user agent to avoid detection
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Try to initialize Chrome with multiple fallback strategies
            try:
                # Method 1: Try direct initialization
                logger.info("Attempting to initialize Chrome directly")
                self.driver = webdriver.Chrome(options=options)
            except Exception as e1:
                logger.warning(f"Direct Chrome initialization failed: {str(e1)}")
                
                # Method 2: Try using webdriver-manager
                try:
                    logger.info("Trying with webdriver-manager")
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                except Exception as e2:
                    logger.error(f"Failed to initialize Chrome: {str(e2)}")
                    return False
            
            # Apply anti-detection measures
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            # Set up wait timeout
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            logger.info("Chrome browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Browser initialization failed: {str(e)}")
            return False
    
    def join_meeting(self, meet_url):
        """Join a Google Meet session as a guest with the configured display name."""
        try:
            # Extract meeting ID from URL
            self.meeting_id = extract_meeting_id(meet_url)
            logger.info(f"Meeting ID: {self.meeting_id}")
            
            # Update recorder with the meeting ID
            if self.recorder:
                self.recorder.meeting_id = self.meeting_id
            
            if not self.driver:
                if not self.initialize_browser():
                    logger.error("Failed to initialize browser, cannot join meeting")
                    return False
            
            # Fix URL format if needed
            if "meet.google.com" not in meet_url:
                if re.match(r'^[a-z0-9-]+$', meet_url):
                    meet_url = f"https://meet.google.com/{meet_url}"
                    logger.info(f"Updated URL to: {meet_url}")
            
            # Navigate to the meeting
            logger.info(f"Navigating to meeting: {meet_url}")
            self.driver.get(meet_url)
            time.sleep(3)  # Wait for page to load
            
            # Save screenshot of initial page
            self._save_screenshot("01-initial-page.png")
            
            # Step 1: Fill in the name field
            logger.info("Looking for the name input field")
            name_filled = self._fill_name_field()
            
            if not name_filled:
                logger.error("Could not fill in name field")
                self._save_screenshot("error-name-field.png")
                return False
            
            # Step 2: Turn off microphone and camera before joining
            logger.info("Turning off microphone and camera")
            self._turn_off_mic_and_camera()
            self._save_screenshot("01d-after-mic-camera-toggle.png")
            
            # Step 3: Click the "Ask to join" button
            logger.info("Looking for 'Ask to join' button")
            self._save_screenshot("02-before-join-click.png")
            
            # Try multiple approaches to click the join button
            join_success = self._click_join_button()
            
            if not join_success:
                logger.error("Failed to click join button")
                self._save_screenshot("error-join-button.png")
                return False
            
            # Wait to confirm we're in the meeting
            logger.info("Join button clicked, waiting to confirm entry...")
            time.sleep(5)
            self._save_screenshot("03-after-join.png")
            
            # Check if we're actually in the meeting by looking for meeting details
            in_meeting = self._verify_in_meeting()
            if not in_meeting:
                logger.warning("Could not verify that we're in the meeting - proceeding anyway")
            else:
                logger.info("Successfully confirmed we're in the meeting")
            
            logger.info("Successfully joined Google Meet session")
            
            # Start recording if enabled
            if self.record_meeting and self.recorder:
                logger.info("Starting meeting recording")
                if self.recorder.start_recording():
                    logger.info("Recording started successfully")
                    
                    # Take screenshot after recording starts
                    time.sleep(2)
                    self._save_screenshot("04-recording-started.png")
                    
                    # Set up periodic recording verification
                    self._setup_recording_check()
                else:
                    logger.warning("Failed to start recording, continuing without it")
            
            # Start a thread to monitor for meeting end
            self._setup_meeting_monitor()
            
            return True
            
        except Exception as e:
            logger.error(f"Error joining meeting: {str(e)}")
            if self.driver:
                self._save_screenshot("error-exception.png")
            return False
    
    def stay_in_meeting(self, duration_minutes):
        """Stay in the meeting for the specified duration."""
        if not self.driver:
            logger.error("Browser not initialized, cannot stay in meeting")
            return
        
        # Calculate end time to allow early exit
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        logger.info(f"Staying in meeting for {duration_minutes} minutes (until {end_time.strftime('%H:%M:%S')})")
        
        try:
            # Use shorter sleep intervals to check if we're still in the meeting
            while datetime.now() < end_time:
                # Check if we're still in the meeting every 15 seconds
                time.sleep(15)
                
                # Check if we're still in a Google Meet URL
                if self.driver and self.driver.current_url:
                    current_url = self.driver.current_url
                    if "meet.google.com" not in current_url:
                        logger.info("No longer on Google Meet URL - meeting may have ended")
                        return
                    
                    # Try to check if we're in a "meeting ended" state
                    try:
                        page_source = self.driver.page_source.lower()
                        if any(x in page_source for x in ["meeting ended", "you left the meeting", "call has ended"]):
                            logger.info("Detected meeting end message - leaving meeting")
                            return
                    except Exception:
                        pass
                else:
                    # Driver or URL not accessible - meeting might be over
                    logger.warning("Cannot access driver or URL - meeting may have ended")
                    return
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt, leaving meeting early")
        finally:
            logger.info("Meeting duration completed or meeting ended")
    
    def leave_meeting(self):
        """Leave the Google Meet session and stop recording."""
        # Stop recording first if it's active
        if self.record_meeting and self.recorder:
            logger.info("Stopping meeting recording")
            if self.recorder.stop_recording():
                video_path = self.recorder.get_recording_path()
                audio_path = self.recorder.get_audio_path()
                
                if video_path:
                    logger.info(f"Recording saved to: {video_path}")
                    
                if audio_path:
                    logger.info(f"Audio extracted to: {audio_path}")
            else:
                logger.warning("Issue stopping the recording")
        
        # Then leave the meeting
        if not self.driver:
            return
        
        try:
            logger.info("Attempting to leave meeting")
            
            # Look for leave/end call button using various strategies
            leave_button_selectors = [
                "button[aria-label*='leave' i]", 
                "button[jsname='CQylAd']",
                "button:contains('Leave')"
            ]
            
            for selector in leave_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            logger.info("Clicked leave button")
                            time.sleep(2)
                            return
                except Exception:
                    continue
            
            # Try with XPath as backup
            try:
                xpath = "//button[contains(., 'Leave') or contains(., 'leave')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        logger.info("Clicked leave button using XPath")
                        time.sleep(2)
                        return
            except Exception:
                pass
            
            logger.warning("Could not find leave button, will close browser directly")
            
        except Exception as e:
            logger.error(f"Error while leaving meeting: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _save_screenshot(self, filename):
        """Save a screenshot for debugging purposes."""
        if not self.driver:
            return
        
        try:
            # Create screenshots directory if it doesn't exist
            screenshots_dir = Path("./screenshots")
            screenshots_dir.mkdir(exist_ok=True)
            
            screenshot_path = screenshots_dir / filename
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"Saved screenshot: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to save screenshot: {str(e)}")
    
    def _fill_name_field(self):
        """Find and fill in the name input field."""
        # Approach 1: Use JavaScript to find and fill name field
        try:
            # Escape single quotes in the display name for JavaScript
            display_name_js = self.display_name.replace("'", "\\'")
            
            js_code = f"""
                const inputs = document.querySelectorAll('input');
                for (const input of inputs) {{
                    if ((input.placeholder && input.placeholder.toLowerCase().includes('name')) || 
                        (input.getAttribute('aria-label') && input.getAttribute('aria-label').toLowerCase().includes('name')) ||
                        (input.id === 'c11')) {{
                        
                        // Clear and set the name
                        input.value = '{display_name_js}';
                        
                        // Trigger events to ensure UI updates
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        console.log('Name input filled with JS');
                        return true;
                    }}
                }}
                return false;
            """
            
            result = self.driver.execute_script(js_code)
            if result:
                logger.info("Name field filled using JavaScript")
                time.sleep(1)
                self._save_screenshot("01a-name-filled-js.png")
                return True
        except Exception as e:
            logger.warning(f"JavaScript name fill failed: {str(e)}")
        
        # Approach 2: Use Selenium selectors
        name_selectors = [
            "input[placeholder='Your name']",
            "input[aria-label='Your name']",
            "#c11",
            "input.qdOxv-fmcmS-wGMbrd",
            "input[type='text']"
        ]
        
        for selector in name_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.clear()
                        element.send_keys(self.display_name)
                        logger.info(f"Name field filled using selector: {selector}")
                        time.sleep(1)
                        self._save_screenshot("01b-name-filled-selenium.png")
                        return True
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")
        
        # Approach 3: Use XPath as last resort
        xpath_patterns = [
            "//input[@placeholder='Your name']",
            "//input[contains(@placeholder, 'name')]",
            "//input[@aria-label='Your name']",
            "//input[contains(@aria-label, 'name')]",
            "//input[@type='text']"
        ]
        
        for xpath in xpath_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed():
                        element.clear()
                        element.send_keys(self.display_name)
                        logger.info(f"Name field filled using XPath: {xpath}")
                        time.sleep(1)
                        self._save_screenshot("01c-name-filled-xpath.png")
                        return True
            except Exception:
                continue
        
        # If we got here, we couldn't find the name field
        return False
    
    def _click_join_button(self):
        """Find and click the 'Ask to join' or 'Join now' button."""
        # Get info about available buttons for debugging
        self._log_buttons_info()
        
        # Approach 1: Target the specific Ask to join button structure from the Google Meet UI
        try:
            js_code = """
                // Target the exact button structure from Google Meet
                const askToJoinBtn = document.querySelector('button.UywwFc-LgbsSe[jsname="Qx7uuf"], button.UywwFc-LgbsSe.tusd3.IyLmn');
                if (askToJoinBtn) {
                    console.log('Found Ask to join button with exact class structure');
                    askToJoinBtn.click();
                    return true;
                }
                
                // Look for span containing the text "Ask to join"
                const spans = document.querySelectorAll('span.UywwFc-vQzf8d');
                for (const span of spans) {
                    if (span.innerText && span.innerText.trim() === 'Ask to join') {
                        const button = span.closest('button');
                        if (button) {
                            console.log('Found Ask to join button via span text');
                            button.click();
                            return true;
                        }
                    }
                }
                
                // Fallback to previous methods
                // ...existing JavaScript button find code...
                return false;
            """
            
            result = self.driver.execute_script(js_code)
            if result:
                logger.info("Ask to join button clicked using exact class targeting")
                time.sleep(2)
                self._save_screenshot("02a-join-clicked-exact-class.png")
                return True
        except Exception as e:
            logger.warning(f"Exact class targeting failed: {str(e)}")
        
        # Try specific XPath based on the provided HTML structure
        try:
            xpath = "//button[contains(@class, 'UywwFc-LgbsSe') and .//span[contains(@class, 'UywwFc-vQzf8d') and text()='Ask to join']]"
            elements = self.driver.find_elements(By.XPATH, xpath)
            
            if elements:
                for element in elements:
                    if element.is_displayed() and not element.get_attribute("disabled"):
                        # Try different click methods
                        try:
                            element.click()
                            logger.info("Ask to join button clicked using exact XPath")
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info("Ask to join button clicked using JavaScript executor")
                            except Exception as e:
                                logger.warning(f"Button click failed: {str(e)}")
                                continue
                        
                        time.sleep(2)
                        self._save_screenshot("02a-join-clicked-exact-xpath.png")
                        return True
        except Exception as e:
            logger.warning(f"Exact XPath targeting failed: {str(e)}")
        
        # Continue with the other approaches if the specific targeting fails
        # Approach 2: Try clicking using CSS selectors
        join_selectors = [
            "button.UywwFc-LgbsSe",
            "button[jsname='Qx7uuf']",
            "button:contains('Ask to join')",
            "button:contains('Join now')"
        ]
        
        for selector in join_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and not element.get_attribute("disabled"):
                        element.click()
                        logger.info(f"Join button clicked using selector: {selector}")
                        time.sleep(2)
                        self._save_screenshot("02b-join-clicked-selenium.png")
                        return True
            except Exception:
                continue
        
        # Approach 3: Try XPath selectors
        xpath_patterns = [
            "//button[contains(., 'Ask to join')]",
            "//button[contains(., 'ask to join')]",
            "//button[contains(., 'Join now')]",
            "//button[contains(., 'join now')]",
            "//button//span[contains(., 'Ask to join')]/parent::button",
            "//button//span[contains(., 'Join now')]/parent::button"
        ]
        
        for xpath in xpath_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed() and not element.get_attribute("disabled"):
                        # Try multiple click methods
                        try:
                            # Method 1: Standard click
                            element.click()
                            logger.info(f"Join button clicked using XPath (standard): {xpath}")
                        except Exception:
                            try:
                                # Method 2: JavaScript click
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"Join button clicked using XPath (JS): {xpath}")
                            except Exception:
                                # Method 3: Actions click
                                ActionChains(self.driver).move_to_element(element).click().perform()
                                logger.info(f"Join button clicked using XPath (Actions): {xpath}")
                        
                        time.sleep(2)
                        self._save_screenshot("02c-join-clicked-xpath.png")
                        return True
            except Exception:
                continue
        
        # All approaches failed
        return False
    
    def _log_buttons_info(self):
        """Log information about available buttons for debugging."""
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"Found {len(buttons)} buttons on page")
            
            for i, button in enumerate(buttons):
                try:
                    if button.is_displayed():
                        text = button.text.strip() if button.text else "No text"
                        class_attr = button.get_attribute("class")
                        jsname = button.get_attribute("jsname")
                        disabled = button.get_attribute("disabled")
                        logger.info(f"Button {i}: '{text}' (class: {class_attr}, jsname: {jsname}, disabled: {disabled})")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error logging button info: {str(e)}")
    
    def _verify_in_meeting(self):
        """Verify that we've successfully joined the meeting."""
        try:
            # Method 1: Check for meeting details elements
            meeting_details_indicators = [
                # Check for "Meeting details" text
                "//div[contains(text(), 'Meeting details')]",
                # Check for the close button in meeting details panel
                "//button[@aria-label='Close']",
                # Check for "Joining info" text
                "//div[contains(text(), 'Joining info')]",
                # Check for meet.google.com URL in the details
                "//div[contains(text(), 'meet.google.com')]",
                # Check for "Copy joining info" button
                "//span[contains(text(), 'Copy joining info')]"
            ]
            
            for xpath in meeting_details_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"Found meeting indicator: {xpath}")
                            return True
                except Exception:
                    continue
            
            # Method 2: Check for common meeting UI elements
            ui_indicators = [
                # People panel button
                "//button[contains(@aria-label, 'participants')]", 
                # Chat panel button
                "//button[contains(@aria-label, 'chat')]",
                # Bottom toolbar
                "//div[@role='complementary']",
                # Microphone/camera controls
                "//button[contains(@aria-label, 'microphone') or contains(@aria-label, 'camera')]"
            ]
            
            for xpath in ui_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"Found meeting UI element: {xpath}")
                            return True
                except Exception:
                    continue
            
            # Method 3: Look for meeting code in URL
            current_url = self.driver.current_url
            if "meet.google.com" in current_url and len(current_url.split("/")) > 3:
                logger.info(f"Currently in a Google Meet URL: {current_url}")
                return True
                
            logger.warning("Could not verify that we're in the meeting - no meeting indicators found")
            return False
            
        except Exception as e:
            logger.warning(f"Error while verifying if in meeting: {str(e)}")
            return False
    
    def _setup_recording_check(self):
        """Setup periodic recording check to ensure recording is working."""
        def check_recording():
            """Periodically check if recording is still working."""
            check_interval = 30  # seconds
            total_checks = 20    # Check for 10 minutes (30s * 20 = 600s = 10min)
            
            for i in range(total_checks):
                time.sleep(check_interval)
                
                # Skip if we're not recording anymore
                if not hasattr(self, 'recorder') or not self.recorder or not self.recorder.recording:
                    logger.warning("Recording appears to have stopped")
                    break
                
                # Verify recording is still active
                if hasattr(self.recorder, 'recording_process'):
                    if self.recorder.recording_process.poll() is not None:
                        logger.error("Recording process has terminated unexpectedly")
                        break
                        
                    # Verify recording file exists and is growing
                    recording_path = self.recorder.get_recording_path()
                    if recording_path and recording_path.exists():
                        file_size = recording_path.stat().st_size
                        logger.info(f"Recording file size: {file_size / (1024*1024):.2f} MB")
                        
                        # Take additional screenshot to show recording is active
                        if i == 2:  # After ~1 minute
                            self._save_screenshot("05-recording-in-progress.png")
                    else:
                        logger.warning("Recording file does not exist")
        
        # Start verification thread
        verification_thread = threading.Thread(target=check_recording, daemon=True)
        verification_thread.start()
        logger.info("Started recording verification thread")
    
    def _setup_meeting_monitor(self):
        """Setup a thread to monitor for meeting end."""
        def monitor_meeting():
            """Check for meeting end conditions periodically."""
            check_interval = 10  # seconds
            
            while True:
                time.sleep(check_interval)
                
                # Skip if driver is not available
                if not self.driver:
                    logger.warning("Driver not available, stopping meeting monitor")
                    break
                
                try:
                    # Check if we've left the Google Meet URL
                    current_url = self.driver.current_url
                    if "meet.google.com" not in current_url:
                        logger.info("No longer on Google Meet URL - meeting ended")
                        break
                    
                    # Check for common phrases indicating meeting has ended
                    page_source = self.driver.page_source.lower()
                    if any(x in page_source for x in ["meeting ended", "you left the meeting", "call has ended"]):
                        logger.info("Detected meeting end message - meeting ended")
                        break
                        
                except Exception as e:
                    logger.warning(f"Error in meeting monitor: {str(e)}")
                    break
        
        # Start monitor thread
        monitoring_thread = threading.Thread(target=monitor_meeting, daemon=True)
        monitoring_thread.start()
        logger.info("Started meeting monitoring thread")
    
    def _turn_off_mic_and_camera(self):
        """Turn off microphone and camera before joining the meeting."""
        try:
            logger.info("Attempting to turn off microphone and camera")
            
            # Method 1: Using the data attributes in the HTML structure
            try:
                # Find and turn off microphone using the specific attributes in the HTML
                mic_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div[data-tooltip='Turn off microphone (ctrl + d)'], [aria-label='Turn off microphone']"
                )
                
                for button in mic_buttons:
                    if button.is_displayed():
                        # Check if already muted
                        is_muted = button.get_attribute("data-is-muted")
                        if is_muted != "true":  # Only click if not already muted
                            logger.info("Clicking microphone button")
                            button.click()
                            time.sleep(1)
                            logger.info("Microphone turned off")
                            break
                
                # Find and turn off camera using the specific attributes in the HTML
                camera_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div[data-tooltip='Turn off camera (ctrl + e)'], [aria-label='Turn off camera']"
                )
                
                for button in camera_buttons:
                    if button.is_displayed():
                        # Check if already muted
                        is_muted = button.get_attribute("data-is-muted")
                        if is_muted != "true":  # Only click if not already muted
                            logger.info("Clicking camera button")
                            button.click()
                            time.sleep(1)
                            logger.info("Camera turned off")
                            break
            except Exception as e:
                logger.warning(f"Could not turn off mic/camera using data attributes: {str(e)}")
            
            # Method 2: Using JavaScript to find and click the buttons
            try:
                js_code = """
                    // Find and click microphone button
                    const micButtons = document.querySelectorAll('[data-tooltip="Turn off microphone (ctrl + d)"], [aria-label="Turn off microphone"]');
                    let micClicked = false;
                    
                    for (const button of micButtons) {
                        if (button.offsetParent !== null) {  // Check if visible
                            const isMuted = button.getAttribute("data-is-muted");
                            if (isMuted !== "true") {
                                button.click();
                                micClicked = true;
                                break;
                            }
                        }
                    }
                    
                    // Find and click camera button
                    const camButtons = document.querySelectorAll('[data-tooltip="Turn off camera (ctrl + e)"], [aria-label="Turn off camera"]');
                    let camClicked = false;
                    
                    for (const button of camButtons) {
                        if (button.offsetParent !== null) {  // Check if visible
                            const isMuted = button.getAttribute("data-is-muted");
                            if (isMuted !== "true") {
                                button.click();
                                camClicked = true;
                                break;
                            }
                        }
                    }
                    
                    return {micClicked, camClicked};
                """
                
                result = self.driver.execute_script(js_code)
                if result.get('micClicked'):
                    logger.info("Microphone turned off using JavaScript")
                if result.get('camClicked'):
                    logger.info("Camera turned off using JavaScript")
                
            except Exception as e:
                logger.warning(f"JavaScript approach to turn off mic/camera failed: {str(e)}")
            
            # Take a screenshot after attempting to turn off mic and camera
            self._save_screenshot("01d-after-mic-camera-toggle.png")
            
        except Exception as e:
            logger.error(f"Error turning off mic and camera: {str(e)}")
            # Continue with the meeting join process even if this fails


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Google Meet Guest Joiner")
    parser.add_argument("url", help="Google Meet URL or code")
    parser.add_argument("name", help="Your display name in the meeting")
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration to stay in the meeting in minutes (default: 60)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode with visible browser"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record the meeting (requires FFmpeg)"
    )
    parser.add_argument(
        "--recording-dir", 
        type=str,
        default="./recordings",
        help="Directory to save recordings (default: ./recordings)"
    )
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Create recordings directory if it doesn't exist
    if args.record:
        recordings_dir = Path(args.recording_dir)
        recordings_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Recordings will be saved to: {recordings_dir}")
    
    # Initialize the bot with recording options if specified
    bot = GoogleMeetGuestBot(
        display_name=args.name, 
        debug=args.debug,
        record_meeting=args.record,
        recording_output_dir=args.recording_dir
    )
    
    try:
        # Join the meeting
        if not bot.join_meeting(args.url):
            logger.error("Failed to join meeting")
            return 1
        
        # Stay in the meeting for the specified duration
        bot.stay_in_meeting(args.duration)
        
        # Leave the meeting
        bot.leave_meeting()
        
        logger.info("Meeting session completed successfully")
        return 0
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        bot.leave_meeting()
        return 0
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())