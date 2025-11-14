from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
INSTAGRAM_API_KEY = os.environ.get('INSTAGRAM_API_KEY', '3e2a25eb4b2f0107dc145aaf9a7fafb3')
INSTAGRAM_API_URL = os.environ.get('INSTAGRAM_API_URL', 'https://instagram-social-api.scraper.tech/user-posts-reels')

# Update the paths to be relative to the container's working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_FOLDER = os.path.join(BASE_DIR, 'public')
THUMBNAILS_FOLDER = os.path.join(PUBLIC_FOLDER, 'thumbnails')

# Ensure the Flask app is created with the correct static folder
app = Flask(__name__, static_folder=PUBLIC_FOLDER)

# Update CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Create necessary directories
os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)

def extract_thumbnail_urls(obj, urls=None):
    """Recursively extract all thumbnail URLs from the Instagram API response."""
    if urls is None:
        urls = []
    
    if isinstance(obj, dict):
        if 'thumbnail_url' in obj and obj['thumbnail_url']:
            urls.append(obj['thumbnail_url'])
        
        for value in obj.values():
            extract_thumbnail_urls(value, urls)
    
    elif isinstance(obj, list):
        for item in obj:
            extract_thumbnail_urls(item, urls)
    
    return urls

def download_thumbnail(url, save_path):
    """Download a thumbnail from the given URL and save it to the specified path."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading thumbnail {url}: {str(e)}")
        return False

@app.route('/api/fetch-thumbnails', methods=['POST'])
def fetch_thumbnails():
    """
    Fetch Instagram thumbnails for a given username or URL.
    Expected JSON payload: {"username_or_url": "instagram_username_or_url"}
    """
    try:
        data = request.get_json()
        if not data or 'username_or_url' not in data:
            return jsonify({"error": "Missing 'username_or_url' in request body"}), 400
        
        username_or_url = data['username_or_url']
        
        # Prepare API request
        params = {
            "username_or_id_or_url": username_or_url,
            "url_embed_safe": "false"
        }
        
        headers = {
            "Scraper-Key": API_KEY
        }
        
        logger.info(f"Fetching Instagram data for: {username_or_url}")
        response = requests.get(INSTAGRAM_API_URL, headers=headers, params=params)
        response.raise_for_status()
        
        # Extract thumbnail URLs
        data = response.json()
        thumbnail_urls = extract_thumbnail_urls(data)
        
        if not thumbnail_urls:
            return jsonify({"message": "No thumbnails found", "thumbnails": []})
        
        # Download and save thumbnails
        saved_thumbnails = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, url in enumerate(thumbnail_urls):
            if not url:
                continue
                
            # Create a safe filename with .jpg extension
            filename = f"{timestamp}_{i:03d}.jpg"
            save_path = os.path.join(THUMBNAILS_FOLDER, filename)
            
            if download_thumbnail(url, save_path):
                saved_thumbnails.append({
                    "original_url": url,
                    "saved_path": f"thumbnails/{filename}",
                    "filename": filename
                })
        
        return jsonify({
            "message": f"Successfully saved {len(saved_thumbnails)} thumbnails",
            "thumbnails": saved_thumbnails
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return jsonify({"error": f"Failed to fetch Instagram data: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/thumbnails', methods=['GET'])
def list_thumbnails():
    """List all available thumbnails in the public/thumbnails directory."""
    try:
        if not os.path.exists(THUMBNAILS_FOLDER):
            return jsonify([])
            
        thumbnails = [
            f for f in os.listdir(THUMBNAILS_FOLDER) 
            if not f.startswith('.') and os.path.isfile(os.path.join(THUMBNAILS_FOLDER, f))
        ]
        return jsonify(thumbnails)
    except Exception as e:
        logger.error(f"Error listing thumbnails: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Serve static files from the public directory
@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve a thumbnail image."""
    try:
        # Security check to prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            return jsonify({"error": "Invalid filename"}), 400
            
        return send_from_directory(THUMBNAILS_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving thumbnail {filename}: {str(e)}")
        return jsonify({"error": "File not found"}), 404

def fetch_instagram_thumbnails(source):
    """
    Fetch and save thumbnails for a given Instagram source.
    
    Args:
        source (str): Instagram username or URL (e.g., 'eltiempo' or 'https://www.instagram.com/eltiempo/')
    """
    try:
        # Extract username from URL if a full URL is provided
        if 'instagram.com' in source:
            username = source.split('instagram.com/')[-1].strip('/')
        else:
            username = source
            
        logger.info(f"Starting fetch for {username} thumbnails...")
        
        # Prepare API request
        params = {
            "username_or_id_or_url": username,
            "url_embed_safe": "false"
        }
        
        headers = {
            "Scraper-Key": API_KEY
        }
        
        # Make the API request
        response = requests.get(INSTAGRAM_API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        # Extract thumbnail URLs
        data = response.json()
        thumbnail_urls = extract_thumbnail_urls(data)
        
        if not thumbnail_urls:
            logger.warning(f"No thumbnails found for {username} account")
            return 0
            
        # Download and save thumbnails with source prefix (limit to 8 per source)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_count = 0
        max_thumbnails = 8  # Límite de 8 miniaturas por fuente
        
        for i, url in enumerate(thumbnail_urls[:max_thumbnails]):  # Solo procesar las primeras 8
            if not url:
                continue
                
            # Create a safe filename with source prefix
            filename = f"{username}_{timestamp}_{i:03d}.jpg"
            save_path = os.path.join(THUMBNAILS_FOLDER, filename)
            
            if download_thumbnail(url, save_path):
                saved_count += 1
                logger.info(f"Saved thumbnail: {filename}")
                
        if len(thumbnail_urls) > max_thumbnails:
            logger.info(f"Limited to {max_thumbnails} thumbnails out of {len(thumbnail_urls)} available for {username}")
                
        logger.info(f"Successfully saved {saved_count} thumbnails for {username}")
        return saved_count
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching {source} thumbnails: {str(e)}")
        return 0
    except Exception as e:
        logger.error(f"Error processing {source} thumbnails: {str(e)}")
        return 0

def fetch_all_sources():
    """Fetch thumbnails from all configured Instagram sources."""
    # List of Instagram sources to fetch
    instagram_sources = [
        'eltiempo',
        'https://www.instagram.com/elespectador/',
        'https://www.instagram.com/bluradio/'
    ]
    
    total_saved = 0
    
    for source in instagram_sources:
        saved = fetch_instagram_thumbnails(source)
        total_saved += saved
        
        # Add a small delay between requests to avoid rate limiting
        import time
        if source != instagram_sources[-1]:  # Don't wait after the last one
            time.sleep(2)
    
    return total_saved

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)
    
    # Fetch thumbnails from all sources when server starts
    try:
        total_saved = fetch_all_sources()
        logger.info(f"Total thumbnails saved across all sources: {total_saved}")
    except Exception as e:
        logger.error(f"Error fetching thumbnails on startup: {str(e)}")
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5001))
    
    # Print available routes
    print("\nAvailable routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        print(f"{rule.endpoint}: {rule.rule} [{methods}]")
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
