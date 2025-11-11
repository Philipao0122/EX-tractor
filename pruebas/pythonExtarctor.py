import requests
import json

# Configuración de la API
url = "https://instagram-social-api.scraper.tech/user-posts-reels"
params = {
    "username_or_id_or_url": "https://www.instagram.com/eltiempo/",
    "pagination_token": "HE1lCxspFwdJLAMTCl5NIRI1DhUABhwiGisMEkc3byBXPgc8BxoUNAcpFSIWFAI9cxZHL1Q0CwwAFTspHCIfEE0bZT0BJQ86CQkRMTo3Hw0QNF4SSlgyIUU9DzYMCwo3Gx4hJgkNFQMeJikiPyU3ORY0HCAgCT4QFlAXKBcYNCs8DSEvKU43TT1GNxovFyYYHy0iPjgEIkYdQUNRDhYYBgAQLRg-KzFfakkqSkMHJC0EDwksQAAOCgBNbFABWhsRPS0EBCYQOAQwBzcbfUhQBgcBC30GFTtbCF4I",
    "url_embed_safe": "false"
}
headers = {
    "Scraper-key": "3e2a25eb4b2f0107dc145aaf9a7fafb3"
}

# Hacer la petición
print("🔄 Obteniendo datos de Instagram...")
response = requests.get(url, headers=headers, params=params)

if response.status_code != 200:
    print(f"❌ Error: Request failed with status code: {response.status_code}")
    exit()

# Parsear JSON
data = response.json()

# Función para extraer todos los thumbnail_url del JSON
def extract_thumbnail_urls(obj, urls=None):
    if urls is None:
        urls = []
    
    if isinstance(obj, dict):
        # Si encontramos thumbnail_url, agregarlo
        if 'thumbnail_url' in obj and obj['thumbnail_url']:
            urls.append(obj['thumbnail_url'])
        
        # Buscar recursivamente en todos los valores
        for value in obj.values():
            extract_thumbnail_urls(value, urls)
    
    elif isinstance(obj, list):
        # Buscar en cada elemento de la lista
        for item in obj:
            extract_thumbnail_urls(item, urls)
    
    return urls

# Extraer todas las URLs
thumbnail_urls = extract_thumbnail_urls(data)
print(f"✅ Se encontraron {len(thumbnail_urls)} imágenes")

# Template HTML
html_template = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Galería Instagram - El Tiempo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: white;
            margin-bottom: 20px;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .subtitle {
            text-align: center;
            color: rgba(255,255,255,0.9);
            margin-bottom: 40px;
            font-size: 1.1rem;
        }

        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
        }

        .gallery-item {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }

        .gallery-item:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 25px rgba(0,0,0,0.25);
        }

        .gallery-item img {
            width: 100%;
            height: 280px;
            object-fit: cover;
            display: block;
        }

        .gallery-item::after {
            content: '🔍';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 3rem;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .gallery-item:hover::after {
            opacity: 0.8;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.95);
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            max-width: 90%;
            max-height: 90%;
        }

        .modal-content img {
            max-width: 100%;
            max-height: 90vh;
            object-fit: contain;
            border-radius: 8px;
        }

        .close {
            position: absolute;
            top: 20px;
            right: 40px;
            color: white;
            font-size: 50px;
            font-weight: bold;
            cursor: pointer;
            z-index: 1001;
            transition: color 0.3s ease;
        }

        .close:hover {
            color: #667eea;
        }

        .counter {
            text-align: center;
            color: rgba(255,255,255,0.8);
            margin-top: 30px;
            font-size: 0.9rem;
        }

        @media (max-width: 768px) {
            .gallery {
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
            }
            
            h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Galería Instagram</h1>
        <p class="subtitle">El Espectador</p>
        <div class="gallery" id="gallery"></div>
        <p class="counter">Total de imágenes: <strong id="imageCount">0</strong></p>
    </div>

    <div id="modal" class="modal">
        <span class="close">&times;</span>
        <div class="modal-content">
            <img id="modalImg" src="" alt="Imagen ampliada">
        </div>
    </div>

    <script>
        const urls = ''' + json.dumps(thumbnail_urls) + ''';

        const gallery = document.getElementById('gallery');
        const modal = document.getElementById('modal');
        const modalImg = document.getElementById('modalImg');
        const closeBtn = document.querySelector('.close');
        const imageCount = document.getElementById('imageCount');

        // Actualizar contador
        imageCount.textContent = urls.length;

        // Crear galería
        urls.forEach((url, index) => {
            const item = document.createElement('div');
            item.className = 'gallery-item';
            
            const img = document.createElement('img');
            img.src = url;
            img.alt = `Post ${index + 1}`;
            img.loading = 'lazy';
            
            img.onerror = function() {
                this.style.display = 'none';
                item.style.display = 'none';
            };
            
            img.onclick = function() {
                modal.style.display = 'block';
                modalImg.src = this.src;
            };
            
            item.appendChild(img);
            gallery.appendChild(item);
        });

        // Cerrar modal
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        };

        modal.onclick = function(e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                modal.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

# Guardar el HTML
output_file = 'gallery_instagram.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"✅ Galería generada exitosamente!")
print(f"📁 Archivo: {output_file}")
print(f"🌐 Abre el archivo en tu navegador para ver la galería")

# Opcional: Guardar también el JSON para respaldo
with open('instagram_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    
print(f"💾 JSON guardado en: instagram_data.json")