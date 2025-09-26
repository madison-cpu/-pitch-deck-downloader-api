import asyncio
import base64
import logging
import os
import tempfile
import uuid
import random
import time
from typing import Dict, List, Optional
from pyppeteer import launch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StealthPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        self.loop = None
        self._shutdown_requested = False
        
    def launch_browser_sync(self):
        """Launch browser with stealth configuration"""
        try:
            logger.info("Launching stealth browser...")

            # Create persistent event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Stealth browser configuration
            # Use headless on Render.com, visible locally for testing
            is_headless = os.getenv('RENDER', False)  # Render.com sets this
            self.browser = self.loop.run_until_complete(launch({
                'headless': is_headless,  # Headless on Render, visible locally
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--window-size=1920,1080',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-default-browser-check',
                    '--no-pings',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-background-timer-throttling',
                    '--disable-features=TranslateUI',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '--exclude-switches=enable-automation',
                    '--disable-extensions-except',
                    '--disable-plugins-discovery',
                    '--disable-background-networking',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--metrics-recording-only',
                    '--safebrowsing-disable-auto-update'
                ],
                'defaultViewport': {'width': 1920, 'height': 1080},
                'ignoreHTTPSErrors': True,
                'ignoreDefaultArgs': ['--enable-automation'],
                'handleSIGINT': False,
                'handleSIGTERM': False,
                'handleSIGHUP': False
            }))

            self.page = self.loop.run_until_complete(self.browser.newPage())
            
            # Set realistic viewport
            self.loop.run_until_complete(self.page.setViewport({
                'width': 1920,
                'height': 1080,
                'deviceScaleFactor': 1,
                'hasTouch': False,
                'isLandscape': True,
                'isMobile': False
            }))
            
            # Set realistic user agent
            self.loop.run_until_complete(self.page.setUserAgent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ))
            
            # Remove webdriver property
            self.loop.run_until_complete(self.page.evaluate('''() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            }'''))
            
            # Override plugins
            self.loop.run_until_complete(self.page.evaluate('''() => {
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            }'''))
            
            # Override languages
            self.loop.run_until_complete(self.page.evaluate('''() => {
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            }'''))
            
            # Override permissions
            self.loop.run_until_complete(self.page.evaluate('''() => {
                const originalQuery = window.navigator.permissions.query;
                return window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }'''))

            logger.info("Stealth browser launched successfully")
            return True

        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate with human-like behavior"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Human-like navigation
            self.loop.run_until_complete(self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 60000}))
            
            # Random human-like delay
            delay = random.uniform(3, 7)
            logger.info(f"Waiting {delay:.1f}s for page load...")
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Simulate human behavior - scroll around
            logger.info("Simulating human behavior...")
            self.loop.run_until_complete(self.page.evaluate('''() => {
                // Random scroll
                window.scrollTo(0, Math.random() * 200);
            }'''))
            
            # Random delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(1, 3)))
            
            # Move mouse around (simulate human presence)
            self.loop.run_until_complete(self.page.mouse.move(random.randint(100, 800), random.randint(100, 600)))
            
            # Random delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(2, 4)))
            
            # Check if we're on the right page
            try:
                page_title = self.loop.run_until_complete(self.page.title())
                logger.info(f"Page title: {page_title}")
                
                # Check for Pitch.com specific elements
                has_pitch_content = self.loop.run_until_complete(self.page.evaluate('''() => {
                    const bodyText = document.body.innerText.toLowerCase();
                    return bodyText.includes('pitch') || bodyText.includes('presentation') || bodyText.length > 500;
                }'''))
                
                if not has_pitch_content:
                    logger.warning("Page doesn't seem to have Pitch content, waiting longer...")
                    self.loop.run_until_complete(asyncio.sleep(5))
                    
            except Exception as e:
                logger.warning(f"Page check failed: {e}")
            
            logger.info("Navigation completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def detect_slide_count_sync(self) -> int:
        """Detect slide count with human-like behavior"""
        try:
            logger.info("Detecting slide count...")
            
            # Random delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(2, 4)))
            
            # Look for slide counter
            slide_text = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Try multiple selectors for slide counter
                const selectors = [
                    '.player-v2-chrome-controls-slide-count',
                    '[class*="slide-count"]',
                    '[class*="counter"]',
                    '.slide-counter',
                    '.presentation-counter'
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent) {
                        return element.textContent.trim();
                    }
                }
                
                return null;
            }'''))
            
            if slide_text and '/' in slide_text:
                parts = slide_text.split('/')
                if len(parts) == 2:
                    try:
                        total = int(parts[1].strip())
                        logger.info(f"Found slide counter: '{slide_text}' -> {total} slides")
                        return min(total, self.max_slides)
                    except ValueError:
                        pass
            
            # Try to detect slides by looking for slide elements
            slide_elements = self.loop.run_until_complete(self.page.evaluate('''() => {
                const slideSelectors = [
                    '[class*="slide"]',
                    '[class*="page"]',
                    '.presentation-slide',
                    '.slide-container'
                ];
                
                let maxSlides = 0;
                for (const selector of slideSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > maxSlides) {
                        maxSlides = elements.length;
                    }
                }
                
                return maxSlides;
            }'''))
            
            if slide_elements > 0:
                logger.info(f"Detected {slide_elements} slide elements")
                return min(slide_elements, self.max_slides)
            
            # Default to 9 slides
            logger.info("Using default: 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    def capture_slide_sync(self, slide_number: int) -> Optional[bytes]:
        """Capture slide with human-like behavior"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Human-like delay
            delay = random.uniform(2, 5)
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Simulate human behavior before capture
            self.loop.run_until_complete(self.page.mouse.move(
                random.randint(200, 800), 
                random.randint(200, 600)
            ))
            
            # Small delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(0.5, 1.5)))
            
            # Take screenshot
            screenshot = self.loop.run_until_complete(self.page.screenshot({
                'type': 'png',
                'quality': 100,
                'fullPage': False
            }))
            
            logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    def navigate_to_next_slide_sync(self) -> bool:
        """Navigate to next slide with human-like behavior"""
        try:
            logger.info("Navigating to next slide...")
            
            # Human-like delay before navigation
            delay = random.uniform(1, 3)
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Move mouse to center (human-like)
            self.loop.run_until_complete(self.page.mouse.move(960, 540))
            
            # Small delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(0.3, 0.8)))
            
            # Use arrow key navigation
            self.loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
            
            # Human-like delay after navigation
            delay = random.uniform(2, 4)
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Random mouse movement
            self.loop.run_until_complete(self.page.mouse.move(
                random.randint(300, 700), 
                random.randint(300, 500)
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def create_pdf_from_screenshots(self, screenshots: List[bytes], filename: str) -> str:
        """Create PDF from screenshots - synchronous method"""
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
        """Close browser synchronously with better error handling"""
        if self.browser:
            try:
                logger.info("Closing browser...")
                
                # Check if loop is still running
                if self.loop and not self.loop.is_closed():
                    try:
                        self.loop.run_until_complete(self.browser.close())
                        logger.info("Browser closed successfully")
                    except RuntimeError as e:
                        if "This event loop is already running" in str(e):
                            logger.warning("Event loop conflict during browser close, forcing close")
                            # Force close without using the loop
                            import subprocess
                            try:
                                subprocess.run(['pkill', '-f', 'chrome'], check=False)
                            except:
                                pass
                        else:
                            raise e
                else:
                    logger.warning("Event loop is closed, forcing browser close")
                    import subprocess
                    try:
                        subprocess.run(['pkill', '-f', 'chrome'], check=False)
                    except:
                        pass
                
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.page = None
                # Close the event loop safely
                if hasattr(self, 'loop') and self.loop and not self.loop.is_closed():
                    try:
                        self.loop.close()
                    except:
                        pass
    
    def download_presentation(self, url: str, filename: str) -> Dict:
        """Stealth download method with human-like behavior"""
        try:
            import time
            import signal
            
            # Set up signal handler for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, marking for shutdown")
                self._shutdown_requested = True
            
            # Register signal handlers
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            start_time = time.time()
            
            # Step 1: Launch stealth browser
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
            self.loop.run_until_complete(self.page.keyboard.press('Home'))
            
            # Human-like delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(3, 6)))
            
            # Check for shutdown
            if self._shutdown_requested:
                return {'success': False, 'error': 'Shutdown requested'}
            
            # Step 5: Capture slides following the exact workflow
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Check for shutdown before each slide
                if self._shutdown_requested:
                    logger.info("Shutdown requested during slide capture")
                    break
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.timeout - 30:  # Leave 30 seconds for PDF creation
                    logger.warning(f"Approaching timeout, stopping at slide {slide_num}")
                    break
                
                # Capture current slide
                screenshot = self.capture_slide_sync(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last slide)
                if slide_num < total_slides:
                    self.navigate_to_next_slide_sync()
            
            if not screenshots:
                return {'success': False, 'error': 'No slides captured'}
            
            # Step 6: Create PDF (synchronous)
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
