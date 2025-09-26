import asyncio
import base64
import logging
import os
import tempfile
import uuid
import random
import time
import requests
import json
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeleniumPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.driver = None
        self.max_slides = max_slides
        self.timeout = timeout
        self._shutdown_requested = False
        
    def launch_browser_sync(self):
        """Launch browser with Selenium"""
        try:
            logger.info("Launching Selenium browser...")

            # Chrome options for stealth
            chrome_options = Options()
            
            # Basic options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # Stealth options
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--hide-scrollbars')
            chrome_options.add_argument('--mute-audio')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--no-pings')
            chrome_options.add_argument('--password-store=basic')
            chrome_options.add_argument('--use-mock-keychain')
            chrome_options.add_argument('--disable-component-extensions-with-background-pages')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--exclude-switches=enable-automation')
            chrome_options.add_argument('--disable-extensions-except')
            chrome_options.add_argument('--disable-plugins-discovery')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--safebrowsing-disable-auto-update')
            
            # User agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Headless mode for Render.com
            if os.getenv('RENDER', False):
                chrome_options.add_argument('--headless')
            
            # Additional stealth options
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set window size
            self.driver.set_window_size(1920, 1080)
            
            logger.info("Selenium browser launched successfully")
            return True

        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate with Selenium approach"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Try different URL formats
            urls_to_try = [
                url,
                url + '?presentation=true',
                url + '?embed=true',
                url + '?view=presentation',
                url.replace('/v/', '/present/') if '/v/' in url else url
            ]
            
            for i, test_url in enumerate(urls_to_try):
                try:
                    logger.info(f"Trying URL {i+1}: {test_url}")
                    
                    # Navigate to URL
                    self.driver.get(test_url)
                    
                    # Wait for page to load
                    logger.info("Waiting for page to load...")
                    time.sleep(20)
                    
                    # Check content
                    content_check = self.driver.execute_script('''() => {
                        const bodyText = document.body.innerText.trim();
                        const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                        const iframes = document.querySelectorAll('iframe');
                        
                        return {
                            textLength: bodyText.length,
                            loadingElements: loadingElements.length,
                            iframes: iframes.length,
                            hasSlideNumbers: bodyText.match(/\\d+\\s*\\/\\s*\\d+/),
                            title: document.title,
                            url: window.location.href
                        };
                    }''')
                    
                    logger.info(f"Content check for URL {i+1}: {content_check}")
                    
                    # If we have good content, break
                    if content_check['textLength'] > 100 and content_check['loadingElements'] < 2:
                        logger.info(f"URL {i+1} successful - content loaded")
                        return True
                    
                    # Try to trigger presentation loading
                    logger.info("Attempting to trigger presentation...")
                    
                    # Try multiple trigger methods
                    try:
                        # Click on body
                        body = self.driver.find_element(By.TAG_NAME, 'body')
                        body.click()
                        time.sleep(3)
                        
                        # Press Space
                        body.send_keys(Keys.SPACE)
                        time.sleep(3)
                        
                        # Press Enter
                        body.send_keys(Keys.ENTER)
                        time.sleep(3)
                        
                        # Press F11
                        body.send_keys(Keys.F11)
                        time.sleep(3)
                        
                        # Scroll
                        self.driver.execute_script('window.scrollTo(0, 100)')
                        time.sleep(3)
                        
                    except Exception as e:
                        logger.warning(f"Trigger methods failed: {e}")
                    
                    # Wait again after triggers
                    time.sleep(10)
                    
                    # Final content check
                    final_check = self.driver.execute_script('''() => {
                        const bodyText = document.body.innerText.trim();
                        const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                        
                        return {
                            textLength: bodyText.length,
                            loadingElements: loadingElements.length,
                            hasSlideNumbers: bodyText.match(/\\d+\\s*\\/\\s*\\d+/)
                        };
                    }''')
                    
                    logger.info(f"Final content check for URL {i+1}: {final_check}")
                    
                    if final_check['textLength'] > 100 and final_check['loadingElements'] < 2:
                        logger.info(f"URL {i+1} successful after triggers")
                        return True
                        
                except Exception as e:
                    logger.warning(f"URL {i+1} failed: {e}")
                    continue
            
            logger.warning("All URL attempts failed")
            return False
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def detect_slide_count_sync(self) -> int:
        """Detect slide count with Selenium"""
        try:
            logger.info("Detecting slide count...")
            
            # Wait for content
            time.sleep(5)
            
            # Try multiple detection methods
            slide_count = self.driver.execute_script('''() => {
                // Method 1: Look for slide counter text
                const bodyText = document.body.innerText;
                const match = bodyText.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                if (match) {
                    console.log('Found slide counter:', match[0]);
                    return match[0];
                }
                
                // Method 2: Look for slide elements
                const slideElements = document.querySelectorAll('[class*="slide"]');
                if (slideElements.length > 0) {
                    console.log('Found slide elements:', slideElements.length);
                    return slideElements.length;
                }
                
                // Method 3: Look for navigation dots
                const dots = document.querySelectorAll('[class*="dot"], [class*="indicator"]');
                if (dots.length > 0) {
                    console.log('Found navigation dots:', dots.length);
                    return dots.length;
                }
                
                // Method 4: Look for pagination
                const pagination = document.querySelectorAll('[class*="pagination"]');
                if (pagination.length > 0) {
                    console.log('Found pagination elements:', pagination.length);
                    return pagination.length;
                }
                
                return null;
            }''')
            
            if slide_count:
                if isinstance(slide_count, str) and '/' in slide_count:
                    parts = slide_count.split('/')
                    if len(parts) == 2:
                        try:
                            total = int(parts[1].strip())
                            logger.info(f"Found slide count: {total}")
                            return min(total, self.max_slides)
                        except ValueError:
                            pass
                elif isinstance(slide_count, int):
                    logger.info(f"Found slide elements: {slide_count}")
                    return min(slide_count, self.max_slides)
            
            # Default fallback
            logger.info("Using default: 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    def capture_slide_sync(self, slide_number: int) -> Optional[bytes]:
        """Capture slide with Selenium"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to load
            time.sleep(5)
            
            # Try to validate content before capture
            content_valid = self.driver.execute_script('''() => {
                const bodyText = document.body.innerText.trim();
                const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                
                // Check for loading indicators
                if (loadingElements.length > 0) {
                    console.log('Still loading, found loading elements:', loadingElements.length);
                    return false;
                }
                
                // Check for meaningful content
                if (bodyText.length < 50) {
                    console.log('Content too short:', bodyText.length);
                    return false;
                }
                
                // Check for slide numbers
                const hasSlideNumbers = bodyText.match(/\\d+\\s*\\/\\s*\\d+/);
                if (hasSlideNumbers) {
                    console.log('Found slide numbers:', hasSlideNumbers[0]);
                    return true;
                }
                
                // Check for presentation content
                const hasPresentationContent = bodyText.toLowerCase().includes('pitch') ||
                    bodyText.toLowerCase().includes('presentation') ||
                    bodyText.toLowerCase().includes('slide') ||
                    bodyText.length > 200;
                
                return hasPresentationContent;
            }''')
            
            if not content_valid:
                logger.warning(f"Slide {slide_number} content not ready, capturing anyway")
            
            # Take screenshot
            screenshot = self.driver.get_screenshot_as_png()
            
            logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    def navigate_to_next_slide_sync(self) -> bool:
        """Navigate to next slide with Selenium"""
        try:
            logger.info("Navigating to next slide...")
            
            # Try multiple navigation methods
            try:
                # Method 1: Arrow key
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.ARROW_RIGHT)
                time.sleep(3)
                
                # Method 2: Space key
                body.send_keys(Keys.SPACE)
                time.sleep(3)
                
                # Method 3: Click next button
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid*="next"], [aria-label*="next"], .next-slide')
                    next_button.click()
                    time.sleep(3)
                except NoSuchElementException:
                    pass
                
            except Exception as e:
                logger.warning(f"Navigation methods failed: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def create_pdf_from_screenshots(self, screenshots: List[bytes], filename: str) -> str:
        """Create PDF from screenshots"""
        try:
            logger.info(f"Creating PDF from {len(screenshots)} screenshots...")

            # Create temporary file
            temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)

            # Create PDF with landscape orientation
            page_width, page_height = landscape(letter)
            c = canvas.Canvas(output_path, pagesize=landscape(letter))

            for i, screenshot_data in enumerate(screenshots):
                logger.info(f"Adding slide {i+1} to PDF")

                # Convert screenshot to image
                img = Image.open(io.BytesIO(screenshot_data))

                # Save as temporary file for ReportLab
                temp_img_fd, temp_img_path = tempfile.mkstemp(suffix='.png')
                os.close(temp_img_fd)
                img.save(temp_img_path, 'PNG')

                # Add to PDF (full page)
                c.drawImage(temp_img_path, 0, 0, width=page_width, height=page_height)

                # Clean up temp image
                os.unlink(temp_img_path)

                # New page for next slide (except last)
                if i < len(screenshots) - 1:
                    c.showPage()

            c.save()
            logger.info(f"PDF created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PDF creation failed: {e}")
            raise
    
    def close_browser_sync(self):
        """Close browser"""
        if self.driver:
            try:
                logger.info("Closing browser...")
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
    
    def download_presentation(self, url: str, filename: str) -> Dict:
        """Selenium download method"""
        try:
            import time
            import signal
            
            # Set up signal handler
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, marking for shutdown")
                self._shutdown_requested = True
            
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            start_time = time.time()
            
            # Step 1: Launch browser
            if not self.launch_browser_sync():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Check for shutdown
            if self._shutdown_requested:
                return {'success': False, 'error': 'Shutdown requested'}
            
            # Step 2: Navigate to presentation
            if not self.navigate_to_presentation_sync(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Check for shutdown
            if self._shutdown_requested:
                return {'success': False, 'error': 'Shutdown requested'}
            
            # Step 3: Detect slides
            total_slides = self.detect_slide_count_sync()
            logger.info(f"Will capture {total_slides} slides")
            
            # Check for shutdown
            if self._shutdown_requested:
                return {'success': False, 'error': 'Shutdown requested'}
            
            # Step 4: Go to first slide
            logger.info("Going to first slide...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.HOME)
            time.sleep(5)
            
            # Check for shutdown
            if self._shutdown_requested:
                return {'success': False, 'error': 'Shutdown requested'}
            
            # Step 5: Capture slides
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Check for shutdown
                if self._shutdown_requested:
                    logger.info("Shutdown requested during slide capture")
                    break
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.timeout - 30:
                    logger.warning(f"Approaching timeout, stopping at slide {slide_num}")
                    break
                
                # Capture current slide
                screenshot = self.capture_slide_sync(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last)
                if slide_num < total_slides:
                    self.navigate_to_next_slide_sync()
            
            if not screenshots:
                return {'success': False, 'error': 'No slides captured'}
            
            # Step 6: Create PDF
            pdf_path = self.create_pdf_from_screenshots(screenshots, filename)
            
            # Step 7: Save and return
            file_id = str(uuid.uuid4())
            saved_path = f"/tmp/{file_id}.pdf"
            
            import shutil
            shutil.copy2(pdf_path, saved_path)
            
            # Read PDF data
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Clean up
            os.unlink(pdf_path)
            
            elapsed = time.time() - start_time
            logger.info(f"Download completed in {elapsed:.1f} seconds")
            
            return {
                'success': True,
                'filename': f"{filename}.pdf",
                'slides': len(screenshots),
                'data': base64.b64encode(pdf_data).decode('utf-8'),
                'file_id': file_id,
                'file_path': saved_path,
                'processing_time': f"{elapsed:.1f}s"
            }
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {'success': False, 'error': str(e)}
            
        finally:
            # Always close browser
            self.close_browser_sync()
