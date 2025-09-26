#!/usr/bin/env python3
"""
Utility functions for Pitch.com Downloader API
"""

import re
import logging
import sys
from typing import Dict, Any
from urllib.parse import urlparse

def validate_pitch_url(url: str) -> bool:
    """
    Validate if URL is a valid Pitch.com presentation URL
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Check if it's a valid URL
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check if it's a Pitch.com domain
        valid_domains = [
            'pitch.com',
            'app.pitch.com',
            'www.pitch.com'
        ]
        
        if parsed.netloc not in valid_domains:
            return False
        
        # Check URL patterns
        path = parsed.path
        
        # Valid Pitch.com URL patterns
        patterns = [
            r'^/v/[^/]+',                                    # Classic: /v/presentation-name
            r'^/public/[a-f0-9-]+/[a-f0-9-]+',             # Public: /public/uuid/uuid
            r'^/app/public/player/[a-f0-9-]+/[a-f0-9-]+'   # App: /app/public/player/uuid/uuid
        ]
        
        for pattern in patterns:
            if re.match(pattern, path):
                return True
        
        return False
        
    except Exception as e:
        return False

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/pitch_downloader.log')
        ]
    )
    
    # Set specific log levels
    logging.getLogger('pyppeteer').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    # Ensure it's not empty
    if not filename:
        filename = 'presentation'
    
    return filename

def get_presentation_title_from_url(url: str) -> str:
    """Extract presentation title from URL if possible"""
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # For classic format: /v/presentation-name
        if '/v/' in path:
            title = path.split('/v/')[-1].split('/')[0]
            return title.replace('-', ' ').title()
        
        # For other formats, use generic name
        return 'Pitch Presentation'
        
    except Exception:
        return 'Pitch Presentation'

