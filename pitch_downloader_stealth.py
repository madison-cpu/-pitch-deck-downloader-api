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
            
            # Remove webdriver property safely
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
            
            # Override plugins safely
            self.loop.run_until_complete(self.page.evaluate('''() => {
                try {
                    if (navigator.plugins) {
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                            configurable: true
                        });
                    }
                } catch (e) {
                    console.log('Plugins already handled');
                }
            }'''))
            
            # Override languages safely
            self.loop.run_until_complete(self.page.evaluate('''() => {
                try {
                    if (navigator.languages) {
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                            configurable: true
                        });
                    }
                } catch (e) {
                    console.log('Languages already handled');
                }
            }'''))
            
            # Override permissions safely
            self.loop.run_until_complete(self.page.evaluate('''() => {
                try {
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                } catch (e) {
                    console.log('Permissions already handled');
                }
            }'''))

            logger.info("Stealth browser launched successfully")
            return True

        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def navigate_to_presentation_sync(self, url: str) -> bool:
        """Navigate with aggressive stealth behavior"""
        try:
            logger.info(f"Navigating to: {url}")
            
            # Set additional stealth properties safely
            self.loop.run_until_complete(self.page.evaluate('''() => {
                // Override automation detection safely
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
                
                // Override chrome detection
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {},
                    };
                }
                
                // Override permissions safely
                try {
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                } catch (e) {
                    console.log('Permissions already handled');
                }
                
                // Override plugins safely
                try {
                    if (navigator.plugins) {
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                            configurable: true
                        });
                    }
                } catch (e) {
                    console.log('Plugins already handled');
                }
                
                // Override languages safely
                try {
                    if (navigator.languages) {
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                            configurable: true
                        });
                    }
                } catch (e) {
                    console.log('Languages already handled');
                }
            }'''))
            
            # Navigate with networkidle2 for better loading
            self.loop.run_until_complete(self.page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 60000}))
            
            # Wait longer for content to load
            delay = random.uniform(8, 12)
            logger.info(f"Waiting {delay:.1f}s for page load...")
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # More aggressive human simulation
            logger.info("Simulating extensive human behavior...")
            
            # Simulate reading behavior
            for i in range(3):
                self.loop.run_until_complete(self.page.evaluate(f'''() => {{
                    // Random scroll patterns
                    window.scrollTo(0, {random.randint(0, 500)});
                }}'''))
                self.loop.run_until_complete(asyncio.sleep(random.uniform(1, 3)))
                
                # Move mouse around
                self.loop.run_until_complete(self.page.mouse.move(
                    random.randint(100, 800), 
                    random.randint(100, 600)
                ))
                self.loop.run_until_complete(asyncio.sleep(random.uniform(0.5, 2)))
            
            # Try to trigger presentation loading
            logger.info("Attempting to trigger presentation loading...")
            self.loop.run_until_complete(self.page.evaluate('''() => {
                // Try clicking on the page to trigger loading
                const clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: 400,
                    clientY: 300
                });
                document.body.dispatchEvent(clickEvent);
                
                // Try pressing space or enter to start presentation
                const spaceEvent = new KeyboardEvent('keydown', {
                    key: ' ',
                    code: 'Space',
                    keyCode: 32,
                    which: 32,
                    bubbles: true
                });
                document.body.dispatchEvent(spaceEvent);
            }'''))
            
            # Wait for potential loading
            self.loop.run_until_complete(asyncio.sleep(random.uniform(3, 6)))
            
            # Check page content more thoroughly
            try:
                page_title = self.loop.run_until_complete(self.page.title())
                logger.info(f"Page title: {page_title}")
                
                # More comprehensive content check
                content_info = self.loop.run_until_complete(self.page.evaluate('''() => {
                    const bodyText = document.body.innerText.trim();
                    const bodyHTML = document.body.innerHTML;
                    
                    // Look for specific Pitch.com elements
                    const pitchElements = document.querySelectorAll(
                        '[class*="pitch"], [class*="presentation"], [class*="slide"], [class*="deck"]'
                    );
                    
                    // Check for loading states
                    const loadingElements = document.querySelectorAll(
                        '[class*="loading"], [class*="spinner"], [class*="skeleton"]'
                    );
                    
                    // Check for iframes (Pitch might load content in iframes)
                    const iframes = document.querySelectorAll('iframe');
                    
                    return {
                        textLength: bodyText.length,
                        htmlLength: bodyHTML.length,
                        pitchElements: pitchElements.length,
                        loadingElements: loadingElements.length,
                        iframes: iframes.length,
                        hasPitchText: bodyText.toLowerCase().includes('pitch'),
                        hasPresentationText: bodyText.toLowerCase().includes('presentation'),
                        hasSlideText: bodyText.toLowerCase().includes('slide')
                    };
                }'''))
                
                logger.info(f"Content analysis: {content_info}")
                
                # If we don't have good content, try refreshing
                if (content_info['textLength'] < 200 or 
                    content_info['loadingElements'] > 0 or
                    not any([content_info['hasPitchText'], content_info['hasPresentationText'], content_info['hasSlideText']])):
                    
                    logger.warning("Content seems insufficient, trying page refresh...")
                    self.loop.run_until_complete(self.page.reload({'waitUntil': 'networkidle2', 'timeout': 60000}))
                    self.loop.run_until_complete(asyncio.sleep(5))
                    
                    # Try clicking to start presentation
                    self.loop.run_until_complete(self.page.click('body'))
                    self.loop.run_until_complete(asyncio.sleep(3))
                    
            except Exception as e:
                logger.warning(f"Content analysis failed: {e}")
            
            logger.info("Navigation completed")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def detect_slide_count_sync(self) -> int:
        """Detect slide count with comprehensive detection methods"""
        try:
            logger.info("Detecting slide count with comprehensive methods...")
            
            # Wait for page to fully load
            self.loop.run_until_complete(asyncio.sleep(random.uniform(3, 6)))
            
            # Method 1: Look for slide counter in multiple locations
            slide_count = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Try multiple selectors for slide counter
                const selectors = [
                    '.player-v2-chrome-controls-slide-count',
                    '[class*="slide-count"]',
                    '[class*="counter"]',
                    '.slide-counter',
                    '.presentation-counter',
                    '[data-testid*="slide"]',
                    '[aria-label*="slide"]',
                    '.player-controls-slide-count',
                    '.chrome-controls-slide-count',
                    '.slide-indicator',
                    '.pagination',
                    '.progress',
                    '[class*="progress"]',
                    '[class*="pagination"]'
                ];
                
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.textContent) {
                        const text = element.textContent.trim();
                        console.log('Found counter element:', selector, text);
                        return text;
                    }
                }
                
                // Also check all elements with text containing numbers
                const allElements = document.querySelectorAll('*');
                for (const element of allElements) {
                    const text = element.textContent || '';
                    if (text.includes('/') && text.match(/\\d+\\s*\\/\\s*\\d+/)) {
                        console.log('Found counter in text:', text);
                        return text;
                    }
                }
                
                // Try to find any text that looks like slide numbers
                const bodyText = document.body.innerText;
                const slideMatch = bodyText.match(/(\\d+)\\s*\\/\\s*(\\d+)/);
                if (slideMatch) {
                    console.log('Found slide pattern in body text:', slideMatch[0]);
                    return slideMatch[0];
                }
                
                return null;
            }'''))
            
            if slide_count:
                logger.info(f"Found slide counter text: '{slide_count}'")
                if '/' in slide_count:
                    parts = slide_count.split('/')
                    if len(parts) == 2:
                        try:
                            total = int(parts[1].strip())
                            logger.info(f"Parsed slide count: {total} slides")
                            return min(total, self.max_slides)
                        except ValueError:
                            pass
            
            # Method 2: Navigate through slides to count them
            logger.info("Trying navigation method to count slides...")
            slide_count = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Try to find navigation elements
                const navSelectors = [
                    '[data-testid*="next"]',
                    '[aria-label*="next"]',
                    '.next-slide',
                    '.slide-next',
                    'button[title*="next"]',
                    'button[aria-label*="next"]'
                ];
                
                for (const selector of navSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        console.log('Found navigation element:', selector);
                        return true;
                    }
                }
                return false;
            }'''))
            
            if slide_count:
                logger.info("Found navigation elements, will count by navigating")
                return self._count_slides_by_navigation()
            
            # Method 3: Look for slide indicators/dots
            dots_count = self.loop.run_until_complete(self.page.evaluate('''() => {
                const dotSelectors = [
                    '.slide-indicator',
                    '.slide-dot',
                    '[class*="indicator"]',
                    '[class*="dot"]',
                    '.pagination-dot'
                ];
                
                for (const selector of dotSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        console.log('Found dot indicators:', selector, elements.length);
                        return elements.length;
                    }
                }
                return 0;
            }'''))
            
            if dots_count > 0:
                logger.info(f"Found {dots_count} slide indicators")
                return min(dots_count, self.max_slides)
            
            # Method 4: Look for slide content areas
            content_slides = self.loop.run_until_complete(self.page.evaluate('''() => {
                const contentSelectors = [
                    '[class*="slide-content"]',
                    '[class*="presentation-slide"]',
                    '[data-slide]',
                    '.slide-wrapper',
                    '.presentation-content'
                ];
                
                let maxSlides = 0;
                for (const selector of contentSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > maxSlides) {
                        maxSlides = elements.length;
                    }
                }
                
                return maxSlides;
            }'''))
            
            if content_slides > 0:
                logger.info(f"Found {content_slides} content slide elements")
                return min(content_slides, self.max_slides)
            
            # Method 5: Try to detect by looking at the URL or page structure
            url_slides = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Check if there are any slide-related data attributes
                const slideElements = document.querySelectorAll('[data-slide-number], [data-slide-index]');
                if (slideElements.length > 0) {
                    const numbers = Array.from(slideElements).map(el => {
                        return parseInt(el.getAttribute('data-slide-number') || el.getAttribute('data-slide-index') || '0');
                    });
                    return Math.max(...numbers) + 1;
                }
                return 0;
            }'''))
            
            if url_slides > 0:
                logger.info(f"Found {url_slides} slides from data attributes")
                return min(url_slides, self.max_slides)
            
            # Method 6: Try to force presentation mode
            logger.info("Trying to force presentation mode...")
            try:
                # Try pressing F11 for fullscreen
                self.loop.run_until_complete(self.page.keyboard.press('F11'))
                self.loop.run_until_complete(asyncio.sleep(2))
                
                # Try pressing space to start presentation
                self.loop.run_until_complete(self.page.keyboard.press('Space'))
                self.loop.run_until_complete(asyncio.sleep(3))
                
                # Try clicking on the center of the page
                self.loop.run_until_complete(self.page.click('body'))
                self.loop.run_until_complete(asyncio.sleep(2))
                
                # Check if we now have better content
                new_content = self.loop.run_until_complete(self.page.evaluate('''() => {
                    const bodyText = document.body.innerText.trim();
                    return bodyText.length;
                }'''))
                
                logger.info(f"Content length after presentation mode attempt: {new_content}")
                
            except Exception as e:
                logger.warning(f"Presentation mode attempt failed: {e}")
            
            # Method 7: Try different URL patterns
            logger.info("Trying alternative URL patterns...")
            try:
                current_url = self.loop.run_until_complete(self.page.url)
                logger.info(f"Current URL: {current_url}")
                
                # Try adding presentation parameters
                if 'presentation' not in current_url.lower():
                    alt_url = current_url + '?presentation=true'
                    logger.info(f"Trying alternative URL: {alt_url}")
                    self.loop.run_until_complete(self.page.goto(alt_url, {'waitUntil': 'networkidle2', 'timeout': 30000}))
                    self.loop.run_until_complete(asyncio.sleep(5))
                
            except Exception as e:
                logger.warning(f"Alternative URL attempt failed: {e}")
            
            # Default fallback - try a higher number
            logger.info("Using fallback: 15 slides (increased from 12)")
            return min(15, self.max_slides)
            
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            return min(12, self.max_slides)
    
    def _count_slides_by_navigation(self) -> int:
        """Count slides by navigating through them"""
        try:
            logger.info("Counting slides by navigation...")
            
            # Go to first slide
            self.loop.run_until_complete(self.page.keyboard.press('Home'))
            self.loop.run_until_complete(asyncio.sleep(2))
            
            slide_count = 0
            max_attempts = 20  # Prevent infinite loops
            
            for i in range(max_attempts):
                # Check if we can navigate to next slide
                can_navigate = self.loop.run_until_complete(self.page.evaluate('''() => {
                    // Check if next button is enabled or if we can press arrow right
                    const nextButton = document.querySelector('[data-testid*="next"], [aria-label*="next"], .next-slide');
                    if (nextButton && !nextButton.disabled) {
                        return true;
                    }
                    
                    // Check if we're at the end
                    const bodyText = document.body.innerText.toLowerCase();
                    if (bodyText.includes('end') || bodyText.includes('last slide')) {
                        return false;
                    }
                    
                    return true;
                }'''))
                
                if not can_navigate:
                    slide_count += 1
                    break
                
                slide_count += 1
                
                # Navigate to next slide
                self.loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
                self.loop.run_until_complete(asyncio.sleep(1))
                
                # Check if we've reached the end
                is_at_end = self.loop.run_until_complete(self.page.evaluate('''() => {
                    const bodyText = document.body.innerText.toLowerCase();
                    return bodyText.includes('end') || bodyText.includes('last slide') || bodyText.includes('finish');
                }'''))
                
                if is_at_end:
                    break
            
            logger.info(f"Navigation method found {slide_count} slides")
            return min(slide_count, self.max_slides)
            
        except Exception as e:
            logger.error(f"Navigation counting failed: {e}")
            return min(12, self.max_slides)
    
    def capture_slide_sync(self, slide_number: int) -> Optional[bytes]:
        """Capture slide with content validation"""
        try:
            logger.info(f"Capturing slide {slide_number}")
            
            # Wait for slide to load with validation
            max_attempts = 5
            for attempt in range(max_attempts):
                # Human-like delay
                delay = random.uniform(2, 5)
                self.loop.run_until_complete(asyncio.sleep(delay))
                
                # Validate content before capture with more aggressive checks
                is_valid_content = self.loop.run_until_complete(self.page.evaluate('''() => {
                    // Check for loading indicators
                    const loadingElements = document.querySelectorAll(
                        '[class*="loading"], [class*="spinner"], [class*="loader"], [class*="skeleton"], [class*="placeholder"]'
                    );
                    if (loadingElements.length > 0) {
                        console.log('Still loading, found loading elements:', loadingElements.length);
                        return false;
                    }
                    
                    // Check for meaningful content
                    const bodyText = document.body.innerText.trim();
                    if (bodyText.length < 100) {
                        console.log('Content too short:', bodyText.length);
                        return false;
                    }
                    
                    // Check for loading text
                    if (bodyText.toLowerCase().includes('loading') || 
                        bodyText.toLowerCase().includes('please wait') ||
                        bodyText.toLowerCase().includes('loading...') ||
                        bodyText.toLowerCase().includes('yzi')) {  // The minimal title we saw
                        console.log('Found loading text or minimal content');
                        return false;
                    }
                    
                    // Check for actual presentation content
                    const hasPresentationContent = bodyText.toLowerCase().includes('pitch') ||
                        bodyText.toLowerCase().includes('presentation') ||
                        bodyText.toLowerCase().includes('slide') ||
                        bodyText.toLowerCase().includes('deck') ||
                        bodyText.length > 500;  // Substantial content
                    
                    if (!hasPresentationContent) {
                        console.log('No presentation content detected');
                        return false;
                    }
                    
                    // Check for images
                    const images = document.querySelectorAll('img');
                    let loadedImages = 0;
                    for (let img of images) {
                        if (img.complete && img.naturalWidth > 0) {
                            loadedImages++;
                        }
                    }
                    
                    // Check for slide content
                    const slideContent = document.querySelectorAll(
                        '[class*="slide"], [class*="presentation"], [class*="content"], [class*="deck"]'
                    );
                    
                    console.log('Content validation:', {
                        textLength: bodyText.length,
                        images: images.length,
                        loadedImages: loadedImages,
                        slideContent: slideContent.length,
                        hasPresentationContent: hasPresentationContent
                    });
                    
                    // More lenient validation - just need substantial content
                    return bodyText.length > 200;
                }'''))
                
                if is_valid_content:
                    logger.info(f"Slide {slide_number} content validated on attempt {attempt + 1}")
                    break
                else:
                    logger.warning(f"Slide {slide_number} content not ready, attempt {attempt + 1}/{max_attempts}")
                    if attempt < max_attempts - 1:
                        self.loop.run_until_complete(asyncio.sleep(3))
                    else:
                        logger.warning(f"Slide {slide_number} content validation failed, capturing anyway")
            
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
            
            # Validate screenshot content
            if len(screenshot) < 10000:  # Very small screenshot might be loading page
                logger.warning(f"Slide {slide_number} screenshot seems too small ({len(screenshot)} bytes)")
            
            logger.info(f"Captured slide {slide_number} ({len(screenshot)} bytes)")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture slide {slide_number}: {e}")
            return None
    
    def navigate_to_next_slide_sync(self) -> bool:
        """Navigate to next slide with validation"""
        try:
            logger.info("Navigating to next slide...")
            
            # Human-like delay before navigation
            delay = random.uniform(1, 3)
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Move mouse to center (human-like)
            self.loop.run_until_complete(self.page.mouse.move(960, 540))
            
            # Small delay
            self.loop.run_until_complete(asyncio.sleep(random.uniform(0.3, 0.8)))
            
            # Try multiple navigation methods
            navigation_success = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Method 1: Try clicking next button
                const nextButton = document.querySelector(
                    '[data-testid*="next"], [aria-label*="next"], .next-slide, .slide-next, button[title*="next"]'
                );
                if (nextButton && !nextButton.disabled) {
                    console.log('Clicking next button');
                    nextButton.click();
                    return true;
                }
                
                // Method 2: Try arrow key
                console.log('Using arrow key navigation');
                return false; // Will use keyboard.press below
            }'''))
            
            if not navigation_success:
                # Use arrow key navigation
                self.loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
            
            # Human-like delay after navigation
            delay = random.uniform(2, 4)
            self.loop.run_until_complete(asyncio.sleep(delay))
            
            # Validate navigation was successful
            navigation_validated = self.loop.run_until_complete(self.page.evaluate('''() => {
                // Check if we're still on the same slide (navigation failed)
                const bodyText = document.body.innerText.trim();
                
                // Check for error messages
                if (bodyText.toLowerCase().includes('error') || 
                    bodyText.toLowerCase().includes('failed') ||
                    bodyText.toLowerCase().includes('not found')) {
                    console.log('Navigation error detected');
                    return false;
                }
                
                // Check if content changed (simple check)
                return bodyText.length > 50;
            }'''))
            
            if not navigation_validated:
                logger.warning("Navigation validation failed, trying alternative method")
                # Try alternative navigation
                self.loop.run_until_complete(self.page.keyboard.press('ArrowRight'))
                self.loop.run_until_complete(asyncio.sleep(2))
            
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
