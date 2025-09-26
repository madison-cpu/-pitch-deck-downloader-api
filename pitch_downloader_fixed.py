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

class FixedPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        
    async def launch_browser(self):
        """Launch browser with Render.com optimized settings"""
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
                    '--disable-renderer-backgrounding'
                ],
                'defaultViewport': {'width': 1920, 'height': 1080}
            })
            
            self.page = await self.browser.newPage()
            
            # Set user agent
            await self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            logger.info("Browser launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    async def navigate_to_presentation(self, url: str) -> bool:
        """Navigate to presentation and wait for it to fully load"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate to the URL
            await self.page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 60000})
            
            # Wait for the presentation to load completely
            logger.info("Waiting for presentation to load...")
            
            # Method 1: Wait for loading spinner to disappear
            try:
                # Wait for any loading elements to disappear
                await self.page.waitForFunction('''() => {
                    // Check if there are any loading spinners or loading text
                    const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"], [data-testid*="loading"]');
                    const loadingText = document.body.innerText.toLowerCase();
                    
                    // Return true when no loading elements and no "loading" text
                    return loadingElements.length === 0 && !loadingText.includes('loading');
                }''', {'timeout': 30000})
                logger.info("Loading spinner disappeared")
            except:
                logger.warning("Loading spinner check timed out, continuing...")
            
            # Method 2: Wait for slide content to appear
            try:
                await self.page.waitForFunction('''() => {
                    // Look for slide content indicators
                    const slideContent = document.querySelector('[class*="slide"], [class*="presentation"], [data-testid*="slide"]');
                    const hasContent = document.body.innerText.length > 100; // Some meaningful content
                    
                    return slideContent && hasContent;
                }''', {'timeout': 30000})
                logger.info("Slide content detected")
            except:
                logger.warning("Slide content detection timed out, continuing...")
            
            # Method 3: Wait for navigation controls to be ready
            try:
                await self.page.waitForFunction('''() => {
                    const nextBtn = document.querySelector('button[aria-label="Next"]');
                    const prevBtn = document.querySelector('button[aria-label="Previous"]');
                    return nextBtn || prevBtn; // At least one navigation button exists
                }''', {'timeout': 20000})
                logger.info("Navigation controls ready")
            except:
                logger.warning("Navigation controls not found, continuing...")
            
            # Additional wait to ensure everything is rendered
            await asyncio.sleep(5)
            
            logger.info("Successfully navigated to presentation")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def detect_slide_count(self) -> int:
        """Detect total number of slides with better methods"""
        try:
            logger.info("Detecting slide count...")
            
            # Method 1: Look for slide counter (most reliable)
            try:
                # Wait longer for slide counter to appear
                await self.page.waitForSelector('.player-v2-chrome-controls-slide-count', {'timeout': 20000})
                
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
                            return total
                        except ValueError:
                            pass
                            
            except Exception as e:
                logger.warning(f"Slide counter method failed: {e}")
            
            # Method 2: Search all text for slide patterns
            try:
                logger.info("Searching page text for slide patterns...")
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
                                if 1 <= current <= total <= 50:  # Reasonable range
                                    logger.info(f"Found slide pattern: {current}/{total} -> {total} slides")
                                    return total
                            except ValueError:
                                continue
                                
            except Exception as e:
                logger.warning(f"Text search failed: {e}")
            
            # Method 3: Default to 9 for BYTE presentation
            logger.warning("Could not detect slide count, defaulting to 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    async def wait_for_slide_ready(self, slide_number: int):
        """Wait for current slide to be fully rendered"""
        try:
            logger.info(f"Waiting for slide {slide_number} to be ready...")
            
            # Wait for slide content to stabilize
            await self.page.waitForFunction('''() => {
                // Check that we're not in a loading state
                const loadingElements = document.querySelectorAll('[class*="loading"], [class*="spinner"]');
                if (loadingElements.length > 0) return false;
                
                // Check that there's meaningful content
                const bodyText = document.body.innerText;
                if (bodyText.length < 50) return false;
                
                // Check that images are loaded
                const images = document.querySelectorAll('img');
                for (let img of images) {
                    if (!img.complete) return false;
                }
                
                return true;
            }''', {'timeout': 15000})
            
            # Additional wait for animations/transitions
            await asyncio.sleep(2)
            
            logger.info(f"Slide {slide_number} is ready")
            
        except Exception as e:
            logger.warning(f"Slide ready check failed for slide {slide_number}: {e}")
            # Continue anyway with a longer wait
            await asyncio.sleep(3)
    
    async def capture_current_slide(self, slide_number: int) -> Optional[bytes]:
        """Capture screenshot of current slide"""
        try:
            # Wait for slide to be ready
            await self.wait_for_slide_ready(slide_number)
            
            logger.info(f"Capturing slide {slide_number}")
            
            # Take screenshot
            screenshot = await self.page.screenshot({
                'type': 'png',
                'quality': 100,
                'fullPage': False  # Only capture viewport
            })
            
            logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    async def navigate_to_next_slide(self) -> bool:
        """Navigate to next slide and wait for it to load"""
        try:
            logger.info("Navigating to next slide...")
            
            # Use arrow key navigation (most reliable)
            await self.page.keyboard.press('ArrowRight')
            
            # Wait for navigation to complete
            await asyncio.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def create_pdf_from_screenshots(self, screenshots: List[bytes], filename: str) -> str:
        """Create PDF from screenshots with proper landscape formatting"""
        try:
            logger.info(f"Creating PDF from {len(screenshots)} screenshots...")
            
            # Create temporary file
            temp_fd, output_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # Create PDF with landscape orientation
            page_width, page_height = landscape(letter)  # 11x8.5 inches
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
        """Main download method with proper loading detection"""
        try:
            # Step 1: Launch browser
            if not await self.launch_browser():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Step 2: Navigate and wait for full loading
            if not await self.navigate_to_presentation(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect number of slides
            total_slides = await self.detect_slide_count()
            logger.info(f"Detected {total_slides} slides")
            
            if total_slides > self.max_slides:
                return {
                    'success': False, 
                    'error': f'Too many slides: {total_slides} > {self.max_slides}'
                }
            
            # Step 4: Go to first slide and wait
            logger.info("Going to first slide...")
            await self.page.keyboard.press('Home')
            await asyncio.sleep(3)
            
            # Step 5: Capture each slide with proper timing
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Capture current slide (with built-in waiting)
                screenshot = await self.capture_current_slide(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                else:
                    logger.warning(f"Failed to capture slide {slide_num}")
                
                # Navigate to next slide (except for last slide)
                if slide_num < total_slides:
                    await self.navigate_to_next_slide()
            
            if not screenshots:
                return {'success': False, 'error': 'No slides captured'}
            
            # Step 6: Create PDF
            pdf_path = self.create_pdf_from_screenshots(screenshots, filename)
            
            # Step 7: Save file and return result
            file_id = str(uuid.uuid4())
            saved_path = f"/tmp/{file_id}.pdf"
            
            import shutil
            shutil.copy2(pdf_path, saved_path)
            
            # Read PDF data for base64
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Clean up original
            os.unlink(pdf_path)
            
            return {
                'success': True,
                'filename': f"{filename}.pdf",
                'slides': len(screenshots),
                'data': base64.b64encode(pdf_data).decode('utf-8'),
                'file_id': file_id,
                'file_path': saved_path
            }
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {'success': False, 'error': str(e)}
            
        finally:
            # Always close browser
            if self.browser:
                await self.browser.close()

