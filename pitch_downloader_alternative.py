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
from pyppeteer import launch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlternativePitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        self.loop = None
        self._shutdown_requested = False
        
    def launch_browser_sync(self):
        """Launch browser with alternative approach"""
        try:
            logger.info("Launching alternative browser...")

            # Create persistent event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Alternative browser configuration - try to look like a real user
            is_headless = os.getenv('RENDER', False)
            
            # Use a more realistic configuration
            self.browser = self.loop.run_until_complete(launch({
                'headless': is_headless,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--no-first-run',
                    '--disable-default-apps',
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
            
            # Set realistic headers
            self.loop.run_until_complete(self.page.setExtraHTTPHeaders({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }))
            
            # Set realistic user agent
            self.loop.run_until_complete(self.page.setUserAgent(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ))

            # Remove webdriver property
            self.loop.run_until_complete(self.page.evaluate('''() => {
                try {
                    if (navigator.webdriver !== undefined) {
                        delete navigator.webdriver;
                    }
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                        configurable: true
                    });
                } catch (e) {
                    console.log('Webdriver property already handled');
                }
            }'''))

            logger.info("Alternative browser launched successfully")
            return True

        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate with alternative approach"""
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
                    
                    # Navigate with different strategies
                    self.loop.run_until_complete(self.page.goto(test_url, {
                        'waitUntil': 'networkidle2', 
                        'timeout': 60000
                    }))
                    
                    # Wait for content
                    logger.info("Waiting for content to load...")
                    self.loop.run_until_complete(asyncio.sleep(20))
                    
                    # Check content
                    content_check = self.loop.run_until_complete(self.page.evaluate('''() => {
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
                    }'''))
                    
                    logger.info(f"Content check for URL {i+1}: {content_check}")
                    
                    # If we have good content, break
                    if content_check['textLength'] > 100 and content_check['loadingElements'] < 2:
                        logger.info(f"URL {i+1} successful - content loaded")
                        return True
                    
                    # Try to trigger presentation loading
                    logger.info("Attempting to trigger presentation...")
                    
                    # Try multiple trigger methods
                    trigger_methods = [
                        lambda: self.loop.run_until_complete(self.page.click('body')),
                        lambda: self.loop.run_until_complete(self.page.keyboard.press('Space')),
                        lambda: self.loop.run_until_complete(self.page.keyboard.press('Enter')),
                        lambda: self.loop.run_until_complete(self.page.keyboard.press('F11')),
                        lambda: self.loop.run_until_complete(self.page.evaluate('window.scrollTo(0, 100)'))
                    ]
                    
                    for j, trigger in enumerate(trigger_methods):
                        try:
                            trigger()
                            self.loop.run_until_complete(asyncio.sleep(3))
                            
                            # Check if content improved
                            new_content = self.loop.run_until_complete(self.page.evaluate('''() => {
                                const bodyText = document.body.innerText.trim();
                                return bodyText.length;
                            }'''))
                            
                            if new_content > content_check['textLength']:
                                logger.info(f"Trigger method {j+1} improved content: {new_content} chars")
                                break
                                
                        except Exception as e:
                            logger.warning(f"Trigger method {j+1} failed: {e}")
                            continue
                    
                    # Wait again after triggers
                    self.loop.run_until_complete(asyncio.sleep(10))
                    
                    # Final content check
                    final_check = self.loop.run_until_complete(self.page.evaluate('''() => {
                        const bodyText = document.body.innerText.trim();
                        const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                        
                        return {
                            textLength: bodyText.length,
                            loadingElements: loadingElements.length,
                            hasSlideNumbers: bodyText.match(/\\d+\\s*\\/\\s*\\d+/)
                        };
                    }'''))
                    
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
        """Detect slide count with alternative approach"""
        try:
            logger.info("Detecting slide count...")
            
            # Wait for content
            self.loop.run_until_complete(asyncio.sleep(5))
            
            # Try multiple detection methods
            slide_count = self.loop.run_until_complete(self.page.evaluate('''() => {
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
            }'''))
            
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
        """Capture slide with alternative approach"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to load
            self.loop.run_until_complete(asyncio.sleep(5))
            
            # Try to validate content before capture
            content_valid = self.loop.run_until_complete(self.page.evaluate('''() => {
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
            }'''))
            
            if not content_valid:
                logger.warning(f"Slide {slide_number} content not ready, capturing anyway")
            
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
        """Navigate to next slide with alternative approach"""
        try:
            logger.info("Navigating to next slide...")
            
            # Try multiple navigation methods
            navigation_methods = [
                lambda: self.loop.run_until_complete(self.page.keyboard.press('ArrowRight')),
                lambda: self.loop.run_until_complete(self.page.keyboard.press('Space')),
                lambda: self.loop.run_until_complete(self.page.evaluate('''() => {
                    const nextButton = document.querySelector('[data-testid*="next"], [aria-label*="next"], .next-slide');
                    if (nextButton) {
                        nextButton.click();
                        return true;
                    }
                    return false;
                }'''))
            ]
            
            for i, method in enumerate(navigation_methods):
                try:
                    method()
                    self.loop.run_until_complete(asyncio.sleep(3))
                    
                    # Check if navigation was successful
                    nav_check = self.loop.run_until_complete(self.page.evaluate('''() => {
                        const bodyText = document.body.innerText.trim();
                        return bodyText.length > 50;
                    }'''))
                    
                    if nav_check:
                        logger.info(f"Navigation method {i+1} successful")
                        return True
                        
                except Exception as e:
                    logger.warning(f"Navigation method {i+1} failed: {e}")
                    continue
            
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
        """Close browser with better error handling"""
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
        """Alternative download method"""
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
            self.loop.run_until_complete(self.page.keyboard.press('Home'))
            self.loop.run_until_complete(asyncio.sleep(5))
            
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
