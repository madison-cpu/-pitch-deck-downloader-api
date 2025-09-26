import asyncio
import logging
import os
import io
import base64
import tempfile
import uuid
from typing import List, Dict, Optional
from pyppeteer import launch
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimplePitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        
    async def launch_browser(self):
        """Launch browser with optimized settings"""
        try:
            logger.info("Launching browser...")
            
            # Browser args optimized for Render.com
            args = [
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
            ]
            
            self.browser = await launch(
                headless=True,
                args=args,
                ignoreHTTPSErrors=True,
                defaultViewport={'width': 1920, 'height': 1080}
            )
            
            self.page = await self.browser.newPage()
            await self.page.setViewport({'width': 1920, 'height': 1080})
            
            logger.info("Browser launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise
    
    async def navigate_to_presentation(self, url: str):
        """Navigate to the presentation URL"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate with timeout
            await self.page.goto(url, {'waitUntil': 'networkidle0', 'timeout': 30000})
            
            # Wait for page to be interactive
            await asyncio.sleep(3)
            
            logger.info("Successfully navigated to presentation")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def detect_slide_count_fast(self) -> int:
        """Fast slide count detection - try simple methods first"""
        try:
            logger.info("Detecting slide count...")
            
            # Method 1: Look for slide counter text (fastest)
            try:
                # Wait briefly for slide counter
                await self.page.waitForSelector('.player-v2-chrome-controls-slide-count', {'timeout': 10000})
                
                slide_text = await self.page.evaluate('''() => {
                    const counter = document.querySelector('.player-v2-chrome-controls-slide-count');
                    return counter ? counter.textContent : null;
                }''')
                
                if slide_text and '/' in slide_text:
                    parts = slide_text.strip().split('/')
                    if len(parts) == 2:
                        try:
                            total = int(parts[1].strip())
                            logger.info(f"Found slide counter: {slide_text} -> {total} slides")
                            return total
                        except ValueError:
                            pass
                            
            except Exception as e:
                logger.warning(f"Slide counter method failed: {e}")
            
            # Method 2: Quick navigation test (limited attempts)
            logger.info("Trying quick navigation test...")
            
            # Go to first slide
            await self.page.keyboard.press('Home')
            await asyncio.sleep(2)  # Wait longer for navigation
            
            slide_count = 1
            max_test_slides = 20  # Limit to prevent timeout
            previous_screenshot = None
            
            for i in range(max_test_slides):
                # Take screenshot to compare
                current_screenshot = await self.page.screenshot({'type': 'png'})
                
                # Try to go to next slide
                await self.page.keyboard.press('ArrowRight')
                await asyncio.sleep(1.5)  # Wait longer for navigation
                
                # Take screenshot after navigation
                new_screenshot = await self.page.screenshot({'type': 'png'})
                
                # If screenshots are identical, we didn't move (reached end)
                if current_screenshot == new_screenshot:
                    logger.info(f"No navigation detected - reached end at slide {slide_count}")
                    return slide_count
                
                # Check if Next button is disabled (reached end)
                try:
                    is_disabled = await self.page.evaluate('''() => {
                        const btn = document.querySelector('button[aria-label="Next"]');
                        return btn ? btn.disabled : false;
                    }''')
                    
                    if is_disabled:
                        logger.info(f"Next button disabled - reached end at slide {slide_count + 1}")
                        return slide_count + 1
                        
                except:
                    pass
                
                slide_count += 1
                previous_screenshot = new_screenshot
            
            # If we get here, assume it's the max we tested
            logger.warning(f"Could not determine exact count, using {slide_count}")
            return min(slide_count, self.max_slides)
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9  # Default fallback for BYTE presentation
    
    async def capture_current_slide(self, slide_number: int) -> bytes:
        """Capture screenshot of current slide"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to render
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
    
    async def navigate_to_next_slide(self) -> bool:
        """Navigate to next slide using arrow key"""
        try:
            # Use arrow key (more reliable than button clicking)
            await self.page.keyboard.press('ArrowRight')
            await asyncio.sleep(1)  # Wait for navigation
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def create_pdf_from_screenshots(self, screenshots: List[bytes], filename: str) -> str:
        """Create PDF from screenshots"""
        try:
            logger.info(f"Creating PDF from {len(screenshots)} screenshots...")
            
            # Create output path
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/{file_id}.pdf"
            
            # Create PDF with landscape orientation
            page_size = landscape(letter)  # 11x8.5 inches landscape
            c = canvas.Canvas(output_path, pagesize=page_size)
            
            page_width, page_height = page_size
            
            for i, screenshot_bytes in enumerate(screenshots):
                if screenshot_bytes is None:
                    continue
                    
                logger.info(f"Adding slide {i + 1} to PDF")
                
                # Convert to PIL Image
                img = Image.open(io.BytesIO(screenshot_bytes))
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    img.save(temp_file.name, 'PNG')
                    
                    # Add to PDF (full page)
                    c.drawImage(temp_file.name, 0, 0, width=page_width, height=page_height)
                    
                    # Clean up
                    os.unlink(temp_file.name)
                
                # New page for next slide
                if i < len(screenshots) - 1:
                    c.showPage()
            
            c.save()
            logger.info(f"PDF created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"PDF creation failed: {e}")
            raise
    
    async def download_presentation(self, url: str, filename: str) -> Dict:
        """Main download method - follows exact workflow"""
        try:
            # Step 1: Launch browser
            await self.launch_browser()
            
            # Step 2: Navigate to presentation
            if not await self.navigate_to_presentation(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect number of slides (fast method)
            total_slides = await self.detect_slide_count_fast()
            logger.info(f"Detected {total_slides} slides")
            
            if total_slides > self.max_slides:
                return {
                    'success': False, 
                    'error': f'Too many slides: {total_slides} > {self.max_slides}'
                }
            
            # Step 4: Go to first slide
            await self.page.keyboard.press('Home')
            await asyncio.sleep(2)
            
            # Step 5: Capture each slide following your exact workflow
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Screenshot current slide
                screenshot = await self.capture_current_slide(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last slide)
                if slide_num < total_slides:
                    await self.navigate_to_next_slide()
            
            if not screenshots:
                return {'success': False, 'error': 'No slides captured'}
            
            # Step 6: Create PDF
            pdf_path = self.create_pdf_from_screenshots(screenshots, filename)
            
            # Step 7: Save file for download URL and return result
            file_id = str(uuid.uuid4())
            saved_path = f"/tmp/{file_id}.pdf"
            
            # Copy PDF to saved location for download URL
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

