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

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configure CORS
cors = CORS()

def create_app():
    app = Flask(__name__)
    cors.init_app(app)
    
    # Configure temp directory
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    logger.info(f'Using temp directory: {temp_dir}')
    
    # Log all available files in temp directory
    try:
        files = os.listdir(temp_dir)
        logger.info(f'Initial files in temp directory: {files}')
    except Exception as e:
        logger.error(f'Error listing temp directory: {str(e)}')
    
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

def save_to_temp(content, filename, subdir=''):
    """
    Save content to a file in the temp directory.
    
    Args:
        content: Content to save (str or bytes)
        filename: Name of the file (can include subdirectories)
        subdir: Optional subdirectory within temp
        
    Returns:
        str: Full path to the saved file
    """
    try:
        # Create full path ensuring it's within temp directory
        full_dir = os.path.join(temp_dir, subdir) if subdir else temp_dir
        os.makedirs(full_dir, exist_ok=True)
        
        # Sanitize filename
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(full_dir, safe_filename)
        
        # Ensure we're still within the temp directory
        if not os.path.commonpath([file_path, temp_dir]) == temp_dir:
            raise ValueError('Attempt to write outside temp directory')
        
        # Write content
        mode = 'wb' if isinstance(content, bytes) else 'w'
        encoding = None if isinstance(content, bytes) else 'utf-8'
        
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
            
        logger.info(f'Saved file to {file_path}')
        return file_path
        
    except Exception as e:
        logger.error(f'Error saving file {filename}: {str(e)}', exc_info=True)
        raise

# Ensure the text file exists
try:
    if not os.path.exists(text_file_path):
        save_to_temp('Archivo de textos extraídos\n' + '=' * 30 + '\n\n', 'extracted_texts.txt')
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
    logger.info(f'Obteniendo imagen de Instagram para URL: {url}')
    
    # Configurar Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configurar el navegador para parecer más real
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    try:
        logger.info('Iniciando navegador Chrome...')
        driver = webdriver.Chrome(options=chrome_options)
        
        # Abrir la URL
        logger.info(f'Accediendo a la URL: {url}')
        driver.get(url)
        
        # Esperar a que la página cargue completamente
        logger.info('Esperando a que la página cargue...')
        time.sleep(5)  # Considerar usar WebDriverWait en lugar de time.sleep()
        
        # Tomar captura de pantalla para depuración
        screenshot_path = os.path.join(temp_dir, 'instagram_page.png')
        driver.save_screenshot(screenshot_path)
        logger.info(f'Captura de pantalla guardada en: {screenshot_path}')
        
        # Intentar diferentes selectores comunes de Instagram
        selectores = [
            "//img[contains(@alt, 'Photo by')]",  # Selector por atributo alt
            "//div[contains(@class, 'x5yr21d')]//img",  # Selector por clase contenedora
            "//div[contains(@class, '_aagv')]//img",  # Clase común para imágenes
            "//article//img",  # Último recurso: cualquier imagen dentro de un artículo
            "//img[contains(@src, 'scontent.cdninstagram.com')]"  # Selector por dominio de la imagen
        ]
        
        img_element = None
        for i, selector in enumerate(selectores, 1):
            try:
                logger.info(f'Intentando selector {i}/{len(selectores)}: {selector}')
                elements = driver.find_elements("xpath", selector)
                logger.info(f'Se encontraron {len(elements)} elementos con el selector: {selector}')
                
                for j, element in enumerate(elements, 1):
                    try:
                        src = element.get_attribute('src')
                        logger.debug(f'Elemento {j} - src: {src}')
                        if src and 'http' in src:
                            img_element = element
                            logger.info(f'Imagen encontrada con selector {selector}')
                            break
                    except Exception as e:
                        logger.warning(f'Error al obtener atributo src: {str(e)}')
                        continue
                        
                if img_element:
                    break
                    
            except Exception as e:
                logger.warning(f'Error con selector {selector}: {str(e)}')
                continue
        
        if not img_element:
            error_msg = "No se pudo encontrar ningún elemento de imagen con los selectores conocidos"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        img_url = img_element.get_attribute('src')
        if not img_url:
            error_msg = "La URL de la imagen está vacía"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        logger.info(f'URL de la imagen encontrada: {img_url}')
            
        # Descargar imagen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.instagram.com/'
        }
        
        logger.info('Descargando imagen...')
        response = requests.get(img_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        logger.info(f'Imagen descargada exitosamente - Dimensiones: {img.width}x{img.height}')
        
        # Verificar que la imagen sea válida
        if img.width == 0 or img.height == 0:
            error_msg = "La imagen descargada no tiene dimensiones válidas"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        return img

    except requests.exceptions.RequestException as e:
        logger.error(f'Error de red al descargar la imagen: {str(e)}')
        raise Exception(f"Error de red al descargar la imagen: {str(e)}")
    except Exception as e:
        logger.error(f'Error al obtener la imagen: {str(e)}', exc_info=True)
        raise Exception(f"Error al procesar la imagen: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info('Navegador cerrado correctamente')
            except Exception as e:
                logger.error(f'Error al cerrar el navegador: {str(e)}')

@app.route('/extract-image', methods=['POST'])
def extract_image():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL no proporcionada'}), 400
    
    try:
        img = obtener_imagen_instagram(data['url'])
        if img:
            # Create a unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'extracted_{timestamp}.jpg'
            
            # Save image to temp directory
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=100, optimize=True, progressive=True)
            
            # Generate a unique filename that matches the frontend's expectation
            # Using the same pattern as before to maintain compatibility
            import uuid
            temp_filename = f'tmp{uuid.uuid4().hex[:8]}.jpg'
            
            # Save the image directly in the temp root directory
            file_path = save_to_temp(
                img_byte_arr.getvalue(),
                temp_filename
            )
            
            # Generate the URL for the saved image
            image_url = f'http://{request.host}/download/{temp_filename}'
            logger.info(f'Imagen guardada: {file_path} ({img.width}x{img.height})')
            
            # Extract text using pytesseract
            try:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                text = pytesseract.image_to_string(img, lang='spa+eng')
                
                if text and text.strip():
                    logger.info(f'Extraído texto: {text[:100]}...')
                    save_extracted_text(text)
                else:
                    logger.info('No se pudo extraer texto de la imagen')
            except Exception as e:
                logger.error(f'Error extrayendo texto: {str(e)}', exc_info=True)
            
            # Return the temporary filename that was actually used
            return jsonify({
                'success': True,
                'image_url': image_url,
                'filename': temp_filename,  # Use the actual filename that was saved
                'file_path': file_path     # For debugging
            })
        else:
            return jsonify({'error': 'No se pudo extraer la imagen'}), 500
    except Exception as e:
        logger.error(f'Error procesando imagen: {str(e)}', exc_info=True)
        return jsonify({
            'error': f'Error al procesar la imagen: {str(e)}',
            'temp_dir': temp_dir
        }), 500

# Route to serve files from temp directory
@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        # Security: Resolve path and ensure it's within temp directory
        safe_path = os.path.normpath(os.path.join(temp_dir, filename))
        
        # Ensure the resolved path is still within the temp directory
        if not os.path.commonpath([safe_path, temp_dir]) == temp_dir:
            logger.error(f'Security violation: Attempt to access path outside temp directory: {filename}')
            return jsonify({'error': 'Access denied'}), 403
        
        logger.info(f'Request to download file: {filename}')
        logger.info(f'Resolved path: {safe_path}')
        
        # Check if file exists and is a file (not a directory)
        if not os.path.exists(safe_path):
            # Try to find the file case-insensitively
            dir_path = os.path.dirname(safe_path)
            base_name = os.path.basename(safe_path).lower()
            
            if os.path.exists(dir_path):
                # List all files in the directory and find a case-insensitive match
                for f in os.listdir(dir_path):
                    if f.lower() == base_name:
                        safe_path = os.path.join(dir_path, f)
                        logger.info(f'Found case-insensitive match: {f}')
                        break
                else:
                    logger.error(f'File not found: {safe_path}')
                    logger.info(f'Available files in {dir_path}: {os.listdir(dir_path) if os.path.exists(dir_path) else "Directory not found"}')
                    return jsonify({
                        'error': 'File not found',
                        'requested_file': filename,
                        'available_files': os.listdir(temp_dir) if os.path.exists(temp_dir) else []
                    }), 404
        
        if not os.path.isfile(safe_path):
            logger.error(f'Path is not a file: {safe_path}')
            return jsonify({'error': 'Path is not a file'}), 400
        
        # Determine MIME type based on file extension
        mime_type = 'application/octet-stream'
        ext = os.path.splitext(safe_path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif']:
            mime_type = 'image/jpeg'
        elif ext == '.txt':
            mime_type = 'text/plain; charset=utf-8'
        elif ext == '.json':
            mime_type = 'application/json'
        
        logger.info(f'Serving file: {safe_path} (MIME: {mime_type})')
        
        # Send file with cache headers
        response = send_file(
            safe_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=os.path.basename(safe_path)
        )
        
        # Cache for 1 hour
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
        
    except Exception as e:
        logger.error(f'Error serving file {filename}: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Error serving file',
            'details': str(e),
            'temp_dir': temp_dir,
            'resolved_path': safe_path if 'safe_path' in locals() else 'Not resolved'
        }), 500

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