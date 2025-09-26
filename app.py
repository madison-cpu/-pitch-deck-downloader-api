from flask import Flask, request, jsonify
import logging
import os
import traceback
from pitch_downloader_stealth import StealthPitchDownloader
from utils import validate_pitch_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration for Render.com
MAX_SLIDES = int(os.getenv('MAX_SLIDES', '15'))
TIMEOUT = int(os.getenv('TIMEOUT', '180'))

@app.route('/')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Pitch.com Downloader API - Stealth Mode',
        'version': '3.8',
        'max_slides': MAX_SLIDES,
        'timeout': TIMEOUT,
        'features': [
            'Stealth mode to bypass detection',
            'Human-like behavior simulation',
            'Realistic mouse movements',
            'Anti-automation measures',
            'Visible browser mode'
        ]
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/limits')
def limits():
    return jsonify({
        'max_slides': MAX_SLIDES,
        'timeout_seconds': TIMEOUT,
        'supported_formats': ['base64'],
        'note': 'Stealth mode to bypass Pitch.com anti-bot detection',
        'improvements': [
            'Human-like behavior simulation',
            'Anti-automation detection bypass',
            'Realistic mouse movements',
            'Visible browser mode',
            'Stealth configuration'
        ]
    })

@app.route('/api/download', methods=['POST'])
def download_presentation():
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        
        # Validate URL
        if not validate_pitch_url(url):
            return jsonify({'success': False, 'error': 'Invalid Pitch.com URL'}), 400
        
        # Get options
        filename = data.get('filename', 'pitch-deck')
        format_type = data.get('format', 'base64')
        options = data.get('options', {})
        
        # Override max_slides if provided in options
        max_slides = min(options.get('max_slides', MAX_SLIDES), MAX_SLIDES)
        
        logger.info(f"Starting download for URL: {url}")
        logger.info(f"Stealth approach - max_slides: {max_slides}, timeout: {TIMEOUT}s")
        
        # Create stealth downloader
        downloader = StealthPitchDownloader(max_slides=max_slides, timeout=TIMEOUT)
        
        # Run download synchronously (no event loop issues)
        result = downloader.download_presentation(url, filename)
        
        if not result['success']:
            logger.error(f"Download failed: {result['error']}")
            return jsonify(result), 500
        
        # Return result based on format
        if format_type == 'base64':
            response_data = {
                'success': True,
                'data': {
                    'filename': result['filename'],
                    'slides': result['slides'],
                    'base64': result['data'],
                    'download_url': f"/api/files/{result['file_id']}"
                }
            }
        else:
            response_data = {
                'success': True,
                'data': {
                    'filename': result['filename'],
                    'slides': result['slides'],
                    'download_url': f"/api/files/{result['file_id']}"
                }
            }
        
        logger.info(f"Download completed: {result['slides']} slides")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/files/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download generated PDF file"""
    try:
        file_path = f"/tmp/{file_id}.pdf"
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File not found or expired'
            }), 404
        
        from flask import send_file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"pitch-deck-{file_id}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'File download failed'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

