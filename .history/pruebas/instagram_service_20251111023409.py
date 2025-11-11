from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta
import logging
import time
import json
from pathlib import Path

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

# Rate limiting configuration
RATE_LIMIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rate_limit.json')
RATE_LIMIT_MINUTES = 15  # 15 minutes cooldown between fetches

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

def load_rate_limit():
    """Load rate limit data from file."""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading rate limit file: {e}")
    return {}

def save_rate_limit(data):
    """Save rate limit data to file."""
    try:
        with open(RATE_LIMIT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving rate limit file: {e}")

def can_fetch_thumbnails(username):
    """Check if we can fetch thumbnails for the given username based on rate limits."""
    rate_data = load_rate_limit()
    now = time.time()
    
    if username not in rate_data:
        return True  # No previous fetch for this user
        
    last_fetch = rate_data[username].get('last_fetch', 0)
    cooldown = RATE_LIMIT_MINUTES * 60  # Convert minutes to seconds
    
    return (now - last_fetch) >= cooldown

def update_rate_limit(username):
    """Update the rate limit for the given username."""
    rate_data = load_rate_limit()
    rate_data[username] = {
        'last_fetch': time.time(),
        'username': username
    }
    save_rate_limit(rate_data)

def fetch_eltiempo_thumbnails():
    """Automatically fetch and save thumbnails for eltiempo Instagram account with rate limiting."""
    username = "eltiempo"
    
    # Check rate limit
    if not can_fetch_thumbnails(username):
        logger.info(f"Rate limit active for {username}. Skipping fetch.")
        return False
        
    try:
        logger.info(f"Starting automatic fetch for {username} thumbnails...")
        
        # Prepare API request
        params = {
            "username_or_id_or_url": username,
            "url_embed_safe": "false"
        }
        
        # Make the API request
        response = requests.get(INSTAGRAM_API_URL, params=params, headers={"X-RapidAPI-Key": API_KEY})
        response.raise_for_status()
        
        # Extract and save thumbnails
        data = response.json()
        if 'data' in data and 'items' in data['data']:
            # Clean up old thumbnails before downloading new ones
            for old_file in Path(THUMBNAILS_FOLDER).glob(f"{username}_*.jpg"):
                try:
                    old_file.unlink()
                    logger.debug(f"Removed old thumbnail: {old_file.name}")
                except Exception as e:
                    logger.error(f"Error removing old thumbnail {old_file.name}: {e}")
            
            # Download new thumbnails
            for i, item in enumerate(data['data']['items']):
                if 'image_versions2' in item and 'candidates' in item['image_versions2']:
                    thumbnail_url = item['image_versions2']['candidates'][0]['url']
                    # Generate a unique filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{username}_{timestamp}_{i:03d}.jpg"
                    filepath = os.path.join(THUMBNAILS_FOLDER, filename)
                    
                    # Download and save the thumbnail
                    img_response = requests.get(thumbnail_url, timeout=10)
                    img_response.raise_for_status()
                    
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    
                    logger.info(f"Saved thumbnail: {filename}")
            
            logger.info(f"Successfully saved {len(data['data']['items'])} thumbnails for {username}")
            
            # Update rate limit after successful fetch
            update_rate_limit(username)
            return True
        else:
            logger.warning("No thumbnails found in the API response")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Instagram data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

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
