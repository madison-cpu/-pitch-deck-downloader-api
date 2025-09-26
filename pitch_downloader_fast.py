import asyncio
import base64
import logging
import os
import tempfile
import uuid
from typing import Dict, List, Optional
from pyppeteer import launch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        
    async def launch_browser(self):
        """Launch browser with minimal settings for speed"""
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
                    '--disable-images'  # Disable images for faster loading
                ],
                'defaultViewport': {'width': 1920, 'height': 1080}
            })
            
            self.page = await self.browser.newPage()
            await self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            logger.info("Browser launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    async def navigate_to_presentation(self, url: str) -> bool:
        """Navigate to presentation with minimal waiting"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate with minimal wait
            await self.page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 20000})
            
            # Minimal wait for basic content
            await asyncio.sleep(3)
            
            logger.info("Navigation completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def detect_slide_count_fast(self) -> int:
        """Ultra-fast slide detection"""
        try:
            logger.info("Detecting slide count...")
            
            # Method 1: Quick slide counter check
            try:
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
            except:
                pass
            
            # Method 2: Default to 9 slides (fastest)
            logger.info("Using default: 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    async def capture_slide_fast(self, slide_number: int) -> Optional[bytes]:
        """Ultra-fast slide capture"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Minimal wait
            await asyncio.sleep(1)
            
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
    
    async def navigate_to_next_slide_fast(self) -> bool:
        """Ultra-fast slide navigation"""
        try:
            # Use arrow key navigation
            await self.page.keyboard.press('ArrowRight')
            
            # Minimal wait
            await asyncio.sleep(1)
            
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
        """Ultra-fast download method"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Step 1: Launch browser
            if not await self.launch_browser():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Step 2: Navigate to presentation
            if not await self.navigate_to_presentation(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect slides (fast)
            total_slides = await self.detect_slide_count_fast()
            logger.info(f"Will capture {total_slides} slides")
            
            # Step 4: Go to first slide
            logger.info("Going to first slide...")
            await self.page.keyboard.press('Home')
            await asyncio.sleep(2)
            
            # Step 5: Capture all slides quickly
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.timeout - 30:  # Leave 30 seconds for PDF creation
                    logger.warning(f"Approaching timeout, stopping at slide {slide_num}")
                    break
                
                # Capture current slide
                screenshot = await self.capture_slide_fast(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last)
                if slide_num < total_slides:
                    await self.navigate_to_next_slide_fast()
            
            if not screenshots:
                return {'success': False, 'error': 'No slides captured'}
            
            # Step 6: Create PDF quickly
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
            # Always close browser
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
