from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from flask_cors import CORS, cross_origin
from PIL import Image
import requests
from io import BytesIO, StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os
import logging
import sys
import pytesseract
from werkzeug.serving import WSGIRequestHandler
import tempfile
from datetime import datetime
import subprocess
import json
from pathlib import Path

# Configure CORS
cors = CORS()

def create_app():
    app = Flask(__name__)
    cors.init_app(app)
    return app

app = create_app()

# Configure CORS to allow all origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configure Tesseract path (update this to your Tesseract installation path)
if sys.platform == 'win32':
    # Common Tesseract installation paths on Windows
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
    else:
        print("Warning: Tesseract not found in common locations. Please ensure it's installed and in your PATH.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create temp directory if it doesn't exist
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
os.makedirs(temp_dir, exist_ok=True)

# Path for the text file to store all extracted text
text_file_path = os.path.join(temp_dir, 'extracted_texts.txt')

# Ensure the text file exists
try:
    if not os.path.exists(text_file_path):
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write('Archivo de textos extraídos\n' + '=' * 30 + '\n\n')
except Exception as e:
    logger.error(f'Error creating text file: {str(e)}')

def save_extracted_text(text: str):
    """Append extracted text to the text file with a timestamp"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(text_file_path, 'a', encoding='utf-8') as f:
            f.write(f'\n\n--- {timestamp} ---\n')
            f.write(text.strip())
            f.write('\n' + '='*50 + '\n')  # Add separator between entries
    except Exception as e:
        logger.error(f'Error saving extracted text: {str(e)}')
        raise

# CORS is already configured above

# Log all requests
@app.before_request
def log_request_info():
    if request.path != '/':  # Skip logging for static files unless needed
        logger.info(f'Request: {request.method} {request.path}')
        logger.info(f'Headers: {dict(request.headers)}')
        if request.get_data():
            logger.info(f'Body: {request.get_data().decode()}')

@app.after_request
def after_request(response):
    # Skip logging for static files
    if request.path.startswith('/static/'):
        return response
        
    # Log response status and data if it's JSON
    response_data = None
    try:
        if response.is_json:
            response_data = response.get_json()
    except:
        pass
        
    if response_data:
        logger.info(f'Response: {response.status} {response_data}')
    else:
        logger.info(f'Response: {response.status} [Non-JSON response]')
        
    return response

def obtener_imagen_instagram(url):
    # Configurar Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configurar el navegador para parecer más real
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Abrir la URL
        driver.get(url)
        
        # Esperar a que la página cargue completamente
        time.sleep(5)
        
        # Intentar diferentes selectores comunes de Instagram
        selectores = [
            "//img[contains(@alt, 'Photo by')]",  # Selector por atributo alt
            "//div[contains(@class, 'x5yr21d')]//img",  # Selector por clase contenedora
            "//div[contains(@class, '_aagv')]//img",  # Clase común para imágenes
            "//article//img",  # Último recurso: cualquier imagen dentro de un artículo
            "//img[contains(@src, 'scontent.cdninstagram.com')]"  # Selector por dominio de la imagen
        ]
        
        img_element = None
        for selector in selectores:
            try:
                elements = driver.find_elements("xpath", selector)
                for element in elements:
                    src = element.get_attribute('src')
                    if src and 'http' in src:
                        img_element = element
                        break
                if img_element:
                    break
            except:
                continue
        
        if not img_element:
            # Tomar captura de pantalla para depuración
            driver.save_screenshot('debug_screenshot.png')
            print("Se ha guardado una captura de pantalla para depuración: debug_screenshot.png")
            raise Exception("No se pudo encontrar ningún elemento de imagen con los selectores conocidos")
        
        img_url = img_element.get_attribute('src')
        if not img_url:
            raise Exception("La URL de la imagen está vacía")
            
        # Descargar imagen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        logger.info(f'Imagen descargada - Dimensiones originales: {img.width}x{img.height}')
        return img

    except Exception as e:
        print(f"Error al obtener la imagen: {str(e)}")
        return None
    finally:
        driver.quit()

@app.route('/extract-image', methods=['POST'])
def extract_image():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL no proporcionada'}), 400
    
    try:
        img = obtener_imagen_instagram(data['url'])
        if img:
            # Create a temporary file while preserving original image quality
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', dir=temp_dir) as temp_file:
                # Save with maximum quality (100) and original dimensions
                img.save(temp_file, 'JPEG', quality=100, optimize=True, progressive=True)
                temp_filename = os.path.basename(temp_file.name)
            
            image_url = f'http://{request.host}/download/{temp_filename}'
            logger.info(f'Imagen guardada con dimensiones originales: {img.width}x{img.height}')
            
            # Extract text using pytesseract
            try:
                # Convert image to RGB if it's not
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Extract text in Spanish and English
                text = pytesseract.image_to_string(img, lang='spa+eng')
                
                if text and text.strip():
                    logger.info(f'Successfully extracted text: {text[:100]}...')  # Log first 100 chars
                    save_extracted_text(text)
                else:
                    logger.info('No text was extracted from the image')
            except Exception as e:
                logger.error(f'Error extracting text: {str(e)}', exc_info=True)
                # Continue even if text extraction fails - we still want to return the image
            
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        else:
            return jsonify({'error': 'No se pudo extraer la imagen'}), 500
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}', exc_info=True)
        return jsonify({'error': f'Error al procesar la imagen: {str(e)}'}), 500

# Route to serve downloaded images
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(temp_dir, filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f'Error serving file {filename}: {str(e)}')
        return jsonify({'error': 'Error serving file'}), 500

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
@cross_origin()
def extract_text():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response, 200

    try:
        data = request.get_json()
        if not data or 'image_url' not in data:
            return jsonify({'success': False, 'error': 'No se proporcionó la URL de la imagen'}), 400
        
        image_url = data['image_url']
        logger.info(f'Processing image URL: {image_url}')
        
        # Download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        
        # Open the image
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB if needed (required by pytesseract)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Extract text using pytesseract
        text = pytesseract.image_to_string(img, lang='spa+eng')
        
        # Clean up the extracted text
        text = text.strip()
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'No se pudo extraer texto de la imagen'
            })
            
        logger.info(f'Successfully extracted text: {text[:100]}...')
        
        # Save the extracted text
        save_extracted_text(text)
        
        return jsonify({
            'success': True,
            'text': text
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f'Error downloading image: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'Error al descargar la imagen: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al procesar la imagen: {str(e)}'
        }), 500

@app.route('/analyze-texts', methods=['POST'])
def analyze_texts():
    try:
        # Ensure the text file exists
        if not os.path.exists(text_file_path):
            return jsonify({
                'success': False,
                'error': 'No hay textos extraídos para analizar'
            }), 400
            
        # Check if file has content (more than just the header)
        with open(text_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if len(content) <= 50:  # Just the header or empty
            return jsonify({
                'success': False,
                'error': 'No hay suficiente texto para analizar'
            }), 400
        
        # Get the path to the Gemini script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        gemini_script_path = os.path.join(project_dir, 'gemini', 'inputTxt.py')
        
        # Ensure the extracted_texts.txt file is copied to the gemini directory
        gemini_text_path = os.path.join(project_dir, 'gemini', 'extracted_texts.txt')
        
        # Copy the extracted text file to the gemini directory
        with open(text_file_path, 'r', encoding='utf-8') as src_file:
            text_content = src_file.read()
            
        with open(gemini_text_path, 'w', encoding='utf-8') as dest_file:
            dest_file.write(text_content)
        
        logger.info(f'Running Gemini analysis script at: {gemini_script_path}')
        
        # Run the Gemini script
        try:
            # Use subprocess to run the Python script
            result = subprocess.run(
                [sys.executable, gemini_script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get the output from the script
            output = result.stdout
            
            # Extract the analysis part from the output
            analysis_start = output.find("Respuesta del modelo:")
            if analysis_start != -1:
                analysis_text = output[analysis_start:]
            else:
                analysis_text = output
                
            logger.info(f'Gemini analysis completed successfully')
            
            return jsonify({
                'success': True,
                'analysis': analysis_text
            })
            
        except subprocess.CalledProcessError as e:
            logger.error(f'Error running Gemini script: {str(e)}')
            logger.error(f'Script stderr: {e.stderr}')
            return jsonify({
                'success': False,
                'error': f'Error al ejecutar el análisis: {e.stderr}'
            }), 500
            
    except Exception as e:
        logger.error(f'Error analyzing texts: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error al analizar los textos: {str(e)}'
        }), 500

@app.route('/download-texts')
def download_texts():
    try:
        # Ensure the file exists (create empty if it doesn't)
        if not os.path.exists(text_file_path):
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write('Archivo de textos extraídos\n' + '=' * 30 + '\n\n')
            
        # Check if file has content (more than just the header)
        with open(text_file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if len(content) <= 50:  # Just the header or empty
            return jsonify({'error': 'No se han extraído textos aún'}), 404
            
        return send_file(
            text_file_path,
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name='textos_extraidos.txt'
        )
    except Exception as e:
        logger.error(f'Error serving text file: {str(e)}', exc_info=True)
        return jsonify({'error': f'Error al descargar los textos: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)