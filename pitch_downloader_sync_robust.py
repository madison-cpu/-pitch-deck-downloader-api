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
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncRobustPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        
    def launch_browser_sync(self):
        """Launch browser synchronously"""
        try:
            logger.info("Launching browser...")
            
            # Create new event loop for browser operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self.browser = loop.run_until_complete(launch({
                    'headless': True,
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
                        '--single-process'
                    ],
                    'defaultViewport': {'width': 1920, 'height': 1080},
                    'ignoreHTTPSErrors': True
                }))
                
                self.page = loop.run_until_complete(self.browser.newPage())
                loop.run_until_complete(self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'))
                
                logger.info("Browser launched successfully")
                return True
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate to presentation synchronously"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Create new event loop for navigation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Navigate with longer timeout
                loop.run_until_complete(self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 60000}))
                
                # Wait for content to load
                logger.info("Waiting for presentation to load...")
                loop.run_until_complete(asyncio.sleep(8))
                
                logger.info("Navigation completed")
                return True
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def detect_slide_count_sync(self) -> int:
        """Detect slide count synchronously"""
        try:
            logger.info("Detecting slide count...")
            
            # Create new event loop for detection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Method 1: Look for slide counter
                loop.run_until_complete(asyncio.sleep(3))
                
                slide_text = loop.run_until_complete(self.page.evaluate('''() => {
                    const counter = document.querySelector('.player-v2-chrome-controls-slide-count');
                    return counter ? counter.textContent.trim() : null;
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
                
                # Method 2: Default to 9 slides
                logger.info("Using default: 9 slides")
                return 9
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    def capture_slide_sync(self, slide_number: int) -> Optional[bytes]:
        """Capture slide synchronously"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Create new event loop for capture
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Wait for slide to stabilize
                loop.run_until_complete(asyncio.sleep(3))
                
                # Take screenshot
                screenshot = loop.run_until_complete(self.page.screenshot({
                    'type': 'png',
                    'quality': 100,
                    'fullPage': False
                }))
                
                logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
                return screenshot
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    def navigate_to_next_slide_sync(self) -> bool:
        """Navigate to next slide synchronously"""
        try:
            logger.info("Navigating to next slide...")
            
            # Create new event loop for navigation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Use arrow key navigation
                loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
                
                # Wait for navigation
                loop.run_until_complete(asyncio.sleep(3))
                
                return True
                
            finally:
                loop.close()
            
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
        """Close browser synchronously"""
        if self.browser:
            try:
                logger.info("Closing browser...")
                
                # Create new event loop for cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(self.browser.close())
                    logger.info("Browser closed successfully")
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.page = None
    
    def download_presentation(self, url: str, filename: str) -> Dict:
        """Synchronous download method"""
        try:
            import time
            start_time = time.time()
            
            # Step 1: Launch browser
            if not self.launch_browser_sync():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Step 2: Navigate to presentation
            if not self.navigate_to_presentation_sync(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect slides
            total_slides = self.detect_slide_count_sync()
            logger.info(f"Will capture {total_slides} slides")
            
            # Step 4: Go to first slide
            logger.info("Going to first slide...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.page.keyboard.press('Home'))
                loop.run_until_complete(asyncio.sleep(3))
            finally:
                loop.close()
            
            # Step 5: Capture slides following the exact workflow
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
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
            # Always close browser gracefully
            self.close_browser_sync()
