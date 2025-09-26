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

class NuclearPitchDownloader:
    def __init__(self, max_slides: int = 15, timeout: int = 180):
        self.browser = None
        self.page = None
        self.max_slides = max_slides
        self.timeout = timeout
        
    async def launch_browser(self):
        """Launch browser with minimal settings"""
        try:
            logger.info("Launching browser...")
            
            self.browser = await launch({
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--window-size=1920,1080'
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
        """Navigate to presentation with proper loading detection"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate with longer timeout
            await self.page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 60000})
            
            logger.info("Waiting for presentation to fully load...")
            
            # Wait for loading indicators to disappear
            try:
                await self.page.waitForFunction('''() => {
                    // Check for common loading indicators
                    const loadingElements = document.querySelectorAll(
                        '[class*="loading"], [class*="spinner"], [class*="loader"], [data-testid*="loading"]'
                    );
                    
                    // Check for loading text
                    const bodyText = document.body.innerText.toLowerCase();
                    const hasLoadingText = bodyText.includes('loading') || bodyText.includes('please wait');
                    
                    // Check if images are loaded
                    const images = document.querySelectorAll('img');
                    let imagesLoaded = true;
                    for (let img of images) {
                        if (!img.complete || img.naturalWidth === 0) {
                            imagesLoaded = false;
                            break;
                        }
                    }
                    
                    return loadingElements.length === 0 && !hasLoadingText && imagesLoaded;
                }''', {'timeout': 30000})
                logger.info("Loading indicators cleared")
            except:
                logger.warning("Loading detection timed out, continuing...")
            
            # Wait for presentation content to appear
            try:
                await self.page.waitForFunction('''() => {
                    // Look for presentation-specific elements
                    const presentationElements = document.querySelectorAll(
                        '[class*="slide"], [class*="presentation"], [class*="deck"], [class*="player"]'
                    );
                    
                    // Check for meaningful content
                    const bodyText = document.body.innerText.trim();
                    const hasContent = bodyText.length > 200 && !bodyText.includes('Loading');
                    
                    return presentationElements.length > 0 && hasContent;
                }''', {'timeout': 20000})
                logger.info("Presentation content detected")
            except:
                logger.warning("Content detection timed out, continuing...")
            
            # Additional wait to ensure everything is rendered
            await asyncio.sleep(5)
            
            logger.info("Navigation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def detect_slide_count(self) -> int:
        """Enhanced slide detection with multiple methods"""
        try:
            logger.info("Detecting slide count...")
            
            # Method 1: Look for slide counter (most reliable)
            try:
                await self.page.waitForSelector('.player-v2-chrome-controls-slide-count', {'timeout': 15000})
                
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
                                    return min(total, self.max_slides)
                            except ValueError:
                                continue
            except Exception as e:
                logger.warning(f"Text search failed: {e}")
            
            # Method 3: Try navigation test (limited)
            try:
                logger.info("Trying navigation test...")
                
                # Go to first slide
                await self.page.keyboard.press('Home')
                await asyncio.sleep(3)
                
                # Reset slide count for accurate counting
                slide_count = 1
                max_test = min(20, self.max_slides)  # Limit test
                
                for i in range(max_test):
                    # Check if we can navigate further
                    try:
                        # Try to go to next slide
                        await self.page.keyboard.press('ArrowRight')
                        await asyncio.sleep(2)
                        
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
            
            # Method 4: Default fallback
            logger.warning("Could not detect slide count, using default: 9 slides")
            return 9
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return 9
    
    async def capture_slide(self, slide_number: int) -> Optional[bytes]:
        """Capture slide with proper content validation"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to be fully loaded and rendered
            await self.page.waitForFunction('''() => {
                // Check that we're not in a loading state
                const loadingElements = document.querySelectorAll(
                    '[class*="loading"], [class*="spinner"], [class*="loader"]'
                );
                if (loadingElements.length > 0) return false;
                
                // Check for meaningful content
                const bodyText = document.body.innerText.trim();
                if (bodyText.length < 100) return false;
                
                // Check that images are loaded
                const images = document.querySelectorAll('img');
                for (let img of images) {
                    if (!img.complete || img.naturalWidth === 0) {
                        return false;
                    }
                }
                
                // Check for presentation-specific content
                const presentationElements = document.querySelectorAll(
                    '[class*="slide"], [class*="presentation"], [class*="deck"]'
                );
                
                return presentationElements.length > 0 || bodyText.length > 200;
            }''', {'timeout': 15000})
            
            # Additional wait for animations/transitions to complete
            await asyncio.sleep(3)
            
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
        """Navigate to next slide with proper timing"""
        try:
            logger.info("Navigating to next slide...")
            
            # Use arrow key navigation (most reliable)
            await self.page.keyboard.press('ArrowRight')
            
            # Wait for navigation to complete
            await asyncio.sleep(3)
            
            # Verify navigation was successful
            try:
                await self.page.waitForFunction('''() => {
                    // Check that we're not stuck in loading
                    const loadingElements = document.querySelectorAll(
                        '[class*="loading"], [class*="spinner"]'
                    );
                    return loadingElements.length === 0;
                }''', {'timeout': 10000})
                logger.info("Navigation completed successfully")
            except:
                logger.warning("Navigation verification timed out")
            
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
        """Nuclear simple download method"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Step 1: Launch browser
            if not await self.launch_browser():
                return {'success': False, 'error': 'Browser launch failed'}
            
            # Step 2: Navigate to presentation
            if not await self.navigate_to_presentation(url):
                return {'success': False, 'error': 'Navigation failed'}
            
            # Step 3: Detect slides (enhanced)
            total_slides = await self.detect_slide_count()
            logger.info(f"Will capture {total_slides} slides")
            
            # Step 4: Go to first slide and ensure it's loaded
            logger.info("Going to first slide...")
            await self.page.keyboard.press('Home')
            await asyncio.sleep(5)  # Longer wait for first slide
            
            # Verify first slide is loaded
            try:
                await self.page.waitForFunction('''() => {
                    const loadingElements = document.querySelectorAll(
                        '[class*="loading"], [class*="spinner"]'
                    );
                    const bodyText = document.body.innerText.trim();
                    return loadingElements.length === 0 && bodyText.length > 100;
                }''', {'timeout': 15000})
                logger.info("First slide loaded successfully")
            except:
                logger.warning("First slide verification timed out, continuing...")
            
            # Step 5: Capture all slides quickly
            screenshots = []
            
            for slide_num in range(1, total_slides + 1):
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.timeout - 30:  # Leave 30 seconds for PDF creation
                    logger.warning(f"Approaching timeout, stopping at slide {slide_num}")
                    break
                
                # Capture current slide
                screenshot = await self.capture_slide(slide_num)
                if screenshot:
                    screenshots.append(screenshot)
                
                # Navigate to next slide (except for last)
                if slide_num < total_slides:
                    await self.navigate_to_next_slide()
            
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

