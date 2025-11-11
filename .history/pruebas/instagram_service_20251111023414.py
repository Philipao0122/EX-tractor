from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public')
CORS(app)  # Enable CORS for all routes

# Configuration
INSTAGRAM_API_URL = "https://instagram-social-api.scraper.tech/user-posts-reels"
API_KEY = "3e2a25eb4b2f0107dc145aaf9a7fafb3"  # Consider moving this to environment variables
PUBLIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
THUMBNAILS_FOLDER = os.path.join(PUBLIC_FOLDER, 'thumbnails')

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

def fetch_eltiempo_thumbnails():
    """Automatically fetch and save thumbnails for eltiempo Instagram account."""
    try:
        logger.info("Starting automatic fetch for eltiempo thumbnails...")
        
        # Prepare API request
        params = {
            "username_or_id_or_url": "eltiempo",
            "url_embed_safe": "false"
        }
        
        headers = {
            "Scraper-Key": API_KEY
        }
        
        # Make the API request
        response = requests.get(INSTAGRAM_API_URL, headers=headers, params=params)
        response.raise_for_status()
        
        # Extract thumbnail URLs
        data = response.json()
        thumbnail_urls = extract_thumbnail_urls(data)
        
        if not thumbnail_urls:
            logger.warning("No thumbnails found for eltiempo account")
            return
            
        # Download and save thumbnails with eltiempo prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_count = 0
        
        for i, url in enumerate(thumbnail_urls):
            if not url:
                continue
                
            # Create a safe filename with eltiempo prefix
            filename = f"eltiempo_{timestamp}_{i:03d}.jpg"
            save_path = os.path.join(THUMBNAILS_FOLDER, filename)
            
            if download_thumbnail(url, save_path):
                saved_count += 1
                logger.info(f"Saved thumbnail: {filename}")
                
        logger.info(f"Successfully saved {saved_count} thumbnails for eltiempo")
        
    except Exception as e:
        logger.error(f"Error fetching eltiempo thumbnails: {str(e)}")

if __name__ == '__main__':
    # Create the public directory if it doesn't exist
    os.makedirs(PUBLIC_FOLDER, exist_ok=True)
    os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)
    
    # Fetch eltiempo thumbnails when server starts
    fetch_eltiempo_thumbnails()
    
    # Print available routes
    print("\nAvailable routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        print(f"{rule.endpoint}: {rule.rule} [{methods}]")
    
    # Run the app
    app.run(debug=True, port=5001)  # Using port 5001 to avoid conflicts
