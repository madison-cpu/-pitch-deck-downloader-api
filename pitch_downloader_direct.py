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

class DirectPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        self.loop = None
        self._shutdown_requested = False
        self.presentation_data = None
        self.slide_count = None
    
    def try_requests_approach(self, url: str) -> bool:
        """Try to get presentation data via requests library"""
        try:
            logger.info("Trying requests-based approach...")
            
            # Extract presentation ID
            if '/v/' in url:
                parts = url.split('/v/')
                if len(parts) > 1:
                    pres_id = parts[1].split('/')[0]
                    logger.info(f"Presentation ID: {pres_id}")
                    
                    # Try different API endpoints
                    api_endpoints = [
                        f"https://pitch.com/api/v1/presentations/{pres_id}",
                        f"https://pitch.com/api/presentations/{pres_id}",
                        f"https://pitch.com/api/v2/presentations/{pres_id}",
                        f"https://pitch.com/presentations/{pres_id}.json",
                        f"https://pitch.com/api/presentation/{pres_id}/slides"
                    ]
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json',
                        'Referer': url
                    }
                    
                    for endpoint in api_endpoints:
                        try:
                            logger.info(f"Trying requests endpoint: {endpoint}")
                            response = requests.get(endpoint, headers=headers, timeout=30)
                            
                            if response.status_code == 200:
                                data = response.json()
                                logger.info(f"Requests response received from {endpoint}: {len(str(data))} characters")
                                
                                # Try to extract slide count
                                if isinstance(data, dict):
                                    if 'slides' in data:
                                        self.slide_count = len(data['slides'])
                                        self.presentation_data = data
                                        logger.info(f"Found {self.slide_count} slides via requests")
                                        return True
                                    elif 'data' in data and 'slides' in data['data']:
                                        self.slide_count = len(data['data']['slides'])
                                        self.presentation_data = data
                                        logger.info(f"Found {self.slide_count} slides in nested requests response")
                                        return True
                                    elif 'presentation' in data and 'slides' in data['presentation']:
                                        self.slide_count = len(data['presentation']['slides'])
                                        self.presentation_data = data
                                        logger.info(f"Found {self.slide_count} slides in presentation requests response")
                                        return True
                                        
                        except Exception as e:
                            logger.warning(f"Requests endpoint {endpoint} failed: {e}")
                            continue
            
            return False
            
        except Exception as e:
            logger.error(f"Requests approach failed: {e}")
            return False
        
    def launch_browser_sync(self):
        """Launch browser with minimal configuration"""
        try:
            logger.info("Launching minimal browser...")

            # Create persistent event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Try different browser configurations
            is_headless = os.getenv('RENDER', False)
            
            browser_configs = [
                {
                    'headless': is_headless,
                    'args': [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ],
                    'defaultViewport': {'width': 1920, 'height': 1080},
                    'ignoreHTTPSErrors': True
                },
                {
                    'headless': is_headless,
                    'args': [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1366,768',
                        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ],
                    'defaultViewport': {'width': 1366, 'height': 768},
                    'ignoreHTTPSErrors': True
                },
                {
                    'headless': is_headless,
                    'args': [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                        '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    ],
                    'defaultViewport': {'width': 1920, 'height': 1080},
                    'ignoreHTTPSErrors': True
                }
            ]
            
            # Try each configuration
            for i, config in enumerate(browser_configs):
                try:
                    logger.info(f"Trying browser configuration {i+1}...")
                    self.browser = self.loop.run_until_complete(launch(config))
                    logger.info(f"Browser configuration {i+1} successful")
                    break
                except Exception as e:
                    logger.warning(f"Browser configuration {i+1} failed: {e}")
                    if i == len(browser_configs) - 1:
                        raise e

            self.page = self.loop.run_until_complete(self.browser.newPage())
            
            # Set basic user agent
            self.loop.run_until_complete(self.page.setUserAgent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ))

            logger.info("Minimal browser launched successfully")
            return True

        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate with network-based approach"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Try to get presentation data via network requests first
            logger.info("Attempting network-based data extraction...")
            
            # Extract presentation ID
            if '/v/' in url:
                parts = url.split('/v/')
                if len(parts) > 1:
                    pres_id = parts[1].split('/')[0]
                    logger.info(f"Presentation ID: {pres_id}")
                    
                    # Try different API endpoints
                    api_endpoints = [
                        f"https://pitch.com/api/v1/presentations/{pres_id}",
                        f"https://pitch.com/api/presentations/{pres_id}",
                        f"https://pitch.com/api/v2/presentations/{pres_id}",
                        f"https://pitch.com/presentations/{pres_id}.json",
                        f"https://pitch.com/api/presentation/{pres_id}/slides"
                    ]
                    
                    for endpoint in api_endpoints:
                        try:
                            logger.info(f"Trying API endpoint: {endpoint}")
                            
                            # Make request via browser
                            response = self.loop.run_until_complete(self.page.evaluate(f'''() => {{
                                return fetch('{endpoint}', {{
                                    method: 'GET',
                                    headers: {{
                                        'Accept': 'application/json',
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        'Referer': '{url}'
                                    }}
                                }}).then(response => {{
                                    if (response.ok) {{
                                        return response.json();
                                    }} else {{
                                        throw new Error('HTTP ' + response.status);
                                    }}
                                }}).catch(e => null);
                            }}'''))
                            
                            if response:
                                logger.info(f"API response received from {endpoint}: {len(str(response))} characters")
                                
                                # Try to extract slide count
                                if isinstance(response, dict):
                                    if 'slides' in response:
                                        slide_count = len(response['slides'])
                                        logger.info(f"Found {slide_count} slides in API response")
                                        return True
                                    elif 'data' in response and 'slides' in response['data']:
                                        slide_count = len(response['data']['slides'])
                                        logger.info(f"Found {slide_count} slides in nested API response")
                                        return True
                                    elif 'presentation' in response and 'slides' in response['presentation']:
                                        slide_count = len(response['presentation']['slides'])
                                        logger.info(f"Found {slide_count} slides in presentation API response")
                                        return True
                                        
                        except Exception as e:
                            logger.warning(f"API endpoint {endpoint} failed: {e}")
                            continue
            
            # If API approach fails, try browser navigation
            logger.info("API approach failed, trying browser navigation...")
            
            # Navigate with different strategies
            navigation_strategies = [
                {'waitUntil': 'domcontentloaded', 'timeout': 60000},
                {'waitUntil': 'load', 'timeout': 60000},
                {'waitUntil': 'networkidle0', 'timeout': 60000}
            ]
            
            for i, strategy in enumerate(navigation_strategies):
                try:
                    logger.info(f"Trying navigation strategy {i+1}: {strategy['waitUntil']}")
                    self.loop.run_until_complete(self.page.goto(url, strategy))
                    
                    # Wait for content
                    logger.info("Waiting for content to load...")
                    self.loop.run_until_complete(asyncio.sleep(15))
                    
                    # Check if we got actual content
                    content_check = self.loop.run_until_complete(self.page.evaluate('''() => {
                        const bodyText = document.body.innerText.trim();
                        const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                        
                        return {
                            textLength: bodyText.length,
                            loadingElements: loadingElements.length,
                            hasSlideNumbers: bodyText.match(/\\d+\\s*\\/\\s*\\d+/),
                            title: document.title
                        };
                    }'''))
                    
                    logger.info(f"Content check after strategy {i+1}: {content_check}")
                    
                    # If we have substantial content, break
                    if content_check['textLength'] > 100 and content_check['loadingElements'] < 2:
                        logger.info(f"Strategy {i+1} successful - content loaded")
                        break
                        
                except Exception as e:
                    logger.warning(f"Navigation strategy {i+1} failed: {e}")
                    continue
            
            # Try to access the presentation data directly
            logger.info("Attempting to extract presentation data...")
            
            # Extract presentation ID
            if '/v/' in url:
                parts = url.split('/v/')
                if len(parts) > 1:
                    pres_id = parts[1].split('/')[0]
                    logger.info(f"Presentation ID: {pres_id}")
                    
                    # Try to get presentation data from the page
                    try:
                        pres_data = self.loop.run_until_complete(self.page.evaluate('''() => {
                            // Look for presentation data in window object
                            if (window.__INITIAL_STATE__) {
                                return window.__INITIAL_STATE__;
                            }
                            if (window.__NEXT_DATA__) {
                                return window.__NEXT_DATA__;
                            }
                            if (window.presentationData) {
                                return window.presentationData;
                            }
                            
                            // Look for script tags with data
                            const scripts = document.querySelectorAll('script');
                            for (let script of scripts) {
                                if (script.textContent && script.textContent.includes('slides')) {
                                    try {
                                        return JSON.parse(script.textContent);
                                    } catch (e) {
                                        // Try to extract JSON from script
                                        const match = script.textContent.match(/\\{[\\s\\S]*\\}/);
                                        if (match) {
                                            try {
                                                return JSON.parse(match[0]);
                                            } catch (e2) {
                                                continue;
                                            }
                                        }
                                    }
                                }
                            }
                            
                            return null;
                        }'''))
                        
                        if pres_data:
                            logger.info(f"Found presentation data: {len(str(pres_data))} characters")
                            
                            # Try to extract slide count from data
                            if isinstance(pres_data, dict):
                                if 'slides' in pres_data:
                                    slide_count = len(pres_data['slides'])
                                    logger.info(f"Found {slide_count} slides in data")
                                    return True
                                elif 'presentation' in pres_data and 'slides' in pres_data['presentation']:
                                    slide_count = len(pres_data['presentation']['slides'])
                                    logger.info(f"Found {slide_count} slides in nested data")
                                    return True
                        
                    except Exception as e:
                        logger.warning(f"Data extraction failed: {e}")
            
            # Check page content
            content_info = self.loop.run_until_complete(self.page.evaluate('''() => {
                const bodyText = document.body.innerText.trim();
                const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                
                return {
                    textLength: bodyText.length,
                    loadingElements: loadingElements.length,
                    hasSlideNumbers: bodyText.match(/\\d+\\s*\\/\\s*\\d+/),
                    title: document.title
                };
            }'''))
            
            logger.info(f"Content info: {content_info}")
            
            # If we have content, try to wait for it to load
            if content_info['textLength'] > 0:
                logger.info("Content detected, waiting for full load...")
                self.loop.run_until_complete(asyncio.sleep(15))
                
                # Try clicking to start presentation
                self.loop.run_until_complete(self.page.click('body'))
                self.loop.run_until_complete(asyncio.sleep(5))
            
            logger.info("Navigation completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def detect_slide_count_sync(self) -> int:
        """Detect slide count with direct approach"""
        try:
            logger.info("Detecting slide count...")
            
            # Wait for content
            self.loop.run_until_complete(asyncio.sleep(5))
            
            # Look for slide counter
            slide_count = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Look for slide counter text
                const bodyText = document.body.innerText;
                const match = bodyText.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                if (match) {
                    return match[0];
                }
                
                // Look for slide elements
                const slideElements = document.querySelectorAll('[class*="slide"]');
                if (slideElements.length > 0) {
                    return slideElements.length;
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
        """Capture slide with direct approach"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to load
            self.loop.run_until_complete(asyncio.sleep(3))
            
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
        """Navigate to next slide with direct approach"""
        try:
            logger.info("Navigating to next slide...")
            
            # Use arrow key
            self.loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
            
            # Wait for navigation
            self.loop.run_until_complete(asyncio.sleep(3))
            
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
        if self.browser:
            try:
                logger.info("Closing browser...")
                self.loop.run_until_complete(self.browser.close())
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.page = None
                if hasattr(self, 'loop') and self.loop and not self.loop.is_closed():
                    try:
                        self.loop.close()
                    except:
                        pass
    
    def download_presentation(self, url: str, filename: str) -> Dict:
        """Direct download method"""
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
            
            # Step 1: Try requests approach first
            if self.try_requests_approach(url):
                logger.info("Requests approach successful, using data directly")
                # We have the data, but we still need browser for screenshots
                if not self.launch_browser_sync():
                    return {'success': False, 'error': 'Browser launch failed'}
            else:
                logger.info("Requests approach failed, trying browser approach")
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
            if self.slide_count:
                total_slides = min(self.slide_count, self.max_slides)
                logger.info(f"Using slide count from requests: {total_slides}")
            else:
                total_slides = self.detect_slide_count_sync()
                logger.info(f"Using slide count from browser: {total_slides}")
            
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
