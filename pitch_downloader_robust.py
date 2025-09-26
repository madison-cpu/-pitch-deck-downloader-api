import asyncio
import base64
import logging
import os
import tempfile
import uuid
import signal
import sys
from typing import Dict, List, Optional
from pyppeteer import launch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobustPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        self._shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_requested = True
        
    async def launch_browser(self):
        """Launch browser with robust settings"""
        try:
            logger.info("Launching browser...")
            
            self.browser = await launch({
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--window-size=1920,1080',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    '--no-zygote',
                    '--single-process'  # Important for Render.com
                ],
                'defaultViewport': {'width': 1920, 'height': 1080},
                'ignoreHTTPSErrors': True,
                'handleSIGINT': False,
                'handleSIGTERM': False,
                'handleSIGHUP': False
            })
            
            self.page = await self.browser.newPage()
            await self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Set longer timeouts
            self.page.setDefaultTimeout(30000)
            self.page.setDefaultNavigationTimeout(30000)
            
            logger.info("Browser launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    async def navigate_to_presentation(self, url: str) -> bool:
        """Navigate to presentation with robust error handling"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate with basic wait strategy
            await self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 30000})
            
            # Wait for basic content to load
            logger.info("Waiting for presentation to load...")
            await asyncio.sleep(5)
            
            # Check if we have basic content
            try:
                content_length = await self.page.evaluate('() => document.body.innerText.length')
                logger.info(f"Page content length: {content_length}")
                
                if content_length < 100:
                    logger.warning("Page seems to have minimal content, waiting longer...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.warning(f"Content check failed: {e}")
            
            logger.info("Navigation completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def detect_slide_count_robust(self) -> int:
        """Robust slide count detection with multiple fallbacks"""
        try:
            logger.info("Detecting slide count...")
            
            # Method 1: Look for slide counter element
            try:
                # Wait a bit for the counter to appear
                await asyncio.sleep(3)
                
                slide_text = await self.page.evaluate('''() => {
                    const counter = document.querySelector('.player-v2-chrome-controls-slide-count');
                    return counter ? counter.textContent.trim() : null;
                }''')
                
                if slide_text and '/' in slide_text:
                    parts = slide_text.split('/')
                    if len(parts) == 2:
                        try:
                            total = int(parts[1].strip())
                            logger.info(f"Found slide counter: '{slide_text}' -> {total} slides")
                            return min(total, self.max_slides)
                        except ValueError:
                            pass
            except Exception as e:
                logger.warning(f"Slide counter method failed: {e}")
            
            # Method 2: Search page text for slide patterns
            try:
                page_text = await self.page.evaluate('() => document.body.innerText')
                
                import re
                patterns = [
                    r'(\d+)\s*/\s*(\d+)',  # "1 / 9" or "1/9"
                    r'(\d+)\s+of\s+(\d+)',  # "1 of 9"
                    r'slide\s+(\d+)\s+of\s+(\d+)',  # "slide 1 of 9"
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        for match in matches:
                            try:
                                current, total = int(match[0]), int(match[1])
                                if 1 <= current <= total <= 50:
                                    logger.info(f"Found slide pattern: {current}/{total} -> {total} slides")
                                    return min(total, self.max_slides)
                            except ValueError:
                                continue
            except Exception as e:
                logger.warning(f"Text search failed: {e}")
            
            # Method 3: Manual navigation test (limited)
            try:
                logger.info("Trying manual navigation test...")
                
                # Go to first slide
                await self.page.keyboard.press('Home')
                await asyncio.sleep(2)
                
                slide_count = 1
                max_test = min(10, self.max_slides)  # Limit test to prevent timeout
                
                for i in range(max_test):
                    if self._shutdown_requested:
                        logger.info("Shutdown requested, stopping navigation test")
                        break
                        
                    # Try to go to next slide
                    await self.page.keyboard.press('ArrowRight')
                    await asyncio.sleep(2)
                    
                    # Check if we're still on a valid slide
                    try:
                        # Check if Next button is disabled
                        is_disabled = await self.page.evaluate('''() => {
                            const btn = document.querySelector('button[aria-label="Next"]');
                            return btn ? btn.disabled : false;
                        }''')
                        
                        if is_disabled:
                            logger.info(f"Next button disabled - reached end at slide {slide_count + 1}")
                            return slide_count + 1
                        
                        slide_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Navigation test failed at slide {slide_count}: {e}")
                        break
                
                logger.info(f"Navigation test completed: {slide_count} slides")
                return min(slide_count, self.max_slides)
                
            except Exception as e:
                logger.warning(f"Navigation test failed: {e}")
            
            # Method 4: Default to 9 slides (known for this presentation)
            logger.warning("Could not detect slide count, using default: 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    async def capture_slide_robust(self, slide_number: int) -> Optional[bytes]:
        """Robust slide capture with error handling"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to stabilize
            await asyncio.sleep(2)
            
            # Take screenshot
            screenshot = await self.page.screenshot({
                'type': 'png',
                'quality': 100,
                'fullPage': False
            })
            
            logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    async def navigate_to_next_slide_robust(self) -> bool:
        """Robust slide navigation"""
        try:
            logger.info("Navigating to next slide...")
            
            # Use arrow key navigation
            await self.page.keyboard.press('ArrowRight')
            
            # Wait for navigation
            await asyncio.sleep(2)
            
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
    
    async def download_presentation(self, url: str, filename: str) -> Dict:
        """Robust download method with proper error handling"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Step 1: Launch browser
            if not await self.launch_browser():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Step 2: Navigate to presentation
            if not await self.navigate_to_presentation(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect slides
            total_slides = await self.detect_slide_count_robust()
            logger.info(f"Will capture {total_slides} slides")
            
            # Step 4: Go to first slide
            logger.info("Going to first slide...")
            await self.page.keyboard.press('Home')
            await asyncio.sleep(3)
            
            # Step 5: Capture slides following the exact workflow
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Check for shutdown request
                if self._shutdown_requested:
                    logger.info("Shutdown requested, stopping capture")
                    break
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.timeout - 30:  # Leave 30 seconds for PDF creation
                    logger.warning(f"Approaching timeout, stopping at slide {slide_num}")
                    break
                
                # Capture current slide
                screenshot = await self.capture_slide_robust(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last slide)
                if slide_num < total_slides:
                    await self.navigate_to_next_slide_robust()
            
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
            
            elapsed = asyncio.get_event_loop().time() - start_time
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
            # Always close browser gracefully
            await self.close_browser()
    
    async def close_browser(self):
        """Close browser gracefully"""
        if self.browser:
            try:
                logger.info("Closing browser...")
                await self.browser.close()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.page = None
