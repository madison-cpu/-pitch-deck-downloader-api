#!/usr/bin/env python3
"""
Pre-install Chromium for Render.com deployment
This script runs during the build process to download Chromium
so it's available when the app starts
"""

import asyncio
import logging
import os
import sys
from pyppeteer import launch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def install_chromium():
    """Download and install Chromium during build process"""
    try:
        logger.info("Pre-installing Chromium for Render.com...")
        
        # This will trigger Chromium download if not present
        browser = await launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        # Close immediately after download
        await browser.close()
        
        logger.info("Chromium pre-installation completed successfully!")
        
    except Exception as e:
        logger.error(f"Chromium pre-installation failed: {str(e)}")
        # Don't fail the build, just log the error
        logger.warning("Continuing build without Chromium pre-installation...")
        pass

if __name__ == "__main__":
    try:
        asyncio.run(install_chromium())
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(0)  # Don't fail the build

