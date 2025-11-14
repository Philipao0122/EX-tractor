# EX-tractor

![Project Logo](https://via.placeholder.com/150) <!-- Consider adding a logo -->

EX-tractor es una aplicación web que permite extraer y analizar texto de imágenes, con un enfoque especial en la extracción de contenido de redes sociales como Instagram. La aplicación combina tecnologías de visión por computadora y procesamiento de lenguaje natural para ofrecer una solución completa de extracción de texto.

## Características Principales

- 🖼️ Extracción de imágenes de URLs (especialmente optimizado para Instagram)
- 🔍 Reconocimiento óptico de caracteres (OCR) con soporte para múltiples idiomas
- 📝 Análisis de textos extraídos
- 📱 Interfaz de usuario intuitiva y responsiva
- ⚡ Procesamiento rápido gracias a tecnologías modernas

## Requisitos Previos

- Python 3.8 o superior
- Node.js 16.x o superior
- Tesseract OCR instalado en el sistema
- Navegador web moderno (Chrome, Firefox, Safari, Edge)

## Instalación

### Backend

1. Clona el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd EX-tractor
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. Instala las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura Tesseract OCR:
   - En Linux: `sudo apt-get install tesseract-ocr`
   - En macOS: `brew install tesseract`
   - En Windows: Descarga el instalador desde [aquí](https://github.com/UB-Mannheim/tesseract/wiki)

### Frontend

1. Navega al directorio del proyecto:
   ```bash
   cd frontend  # Si el frontend está en un directorio separado
   ```

2. Instala las dependencias de Node.js:
   ```bash
   npm install
   ```

## Uso

1. Inicia el servidor backend:
   ```bash
   python app.py
   ```

2. En otra terminal, inicia el servidor de desarrollo del frontend:
   ```bash
   npm run dev
   ```

3. Abre tu navegador y navega a:
   ```
   http://localhost:3000
   ```

4. Ingresa la URL de la imagen o perfil de Instagram que deseas analizar y haz clic en "Extraer".

## Estructura del Proyecto

```
EX-tractor/
├── src/                    # Código fuente del frontend
│   ├── components/         # Componentes de React
│   └── App.tsx             # Componente principal
├── pruebas/                # Scripts y utilidades de prueba
│   ├── instagram_service.py # Servicio para pruebas con Instagram
│   ├── pythonExtractor.py  # Script de extracción de pruebas
│   ├── rate_limit.json     # Configuración de límites de tasa
│   └── requirements.txt    # Dependencias para pruebas
├── app.py                  # Aplicación Flask (backend)
├── requirements.txt        # Dependencias de Python
├── package.json            # Dependencias de Node.js
└── temp/                   # Almacenamiento temporal de imágenes
```

## Pruebas

El directorio `pruebas/` contiene scripts y utilidades para probar la funcionalidad del proyecto:

- `instagram_service.py`: Implementación de servicio para interactuar con la API de Instagram
- `pythonExtractor.py`: Script independiente para probar la extracción de imágenes y texto
- `rate_limit.json`: Configuración de límites de tasa para las pruebas
- `requirements.txt`: Dependencias específicas para las pruebas

### Ejecutando las pruebas

1. Asegúrate de tener instaladas las dependencias de pruebas:
   ```bash
   cd pruebas
   pip install -r requirements.txt
   ```

2. Ejecuta el script de extracción de prueba:
   ```bash
   python pythonExtractor.py [URL_DE_PRUEBA]
   ```

3. Para probar el servicio de Instagram:
   ```bash
   python instagram_service.py [URL_DE_INSTAGRAM]
   ```

### Notas sobre pruebas
- Las pruebas pueden requerir credenciales específicas de API
- Algunas pruebas pueden estar sujetas a límites de tasa
- Se recomienda usar cuentas de prueba para evitar restricciones

## Tecnologías Utilizadas

- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **Backend**: Python, Flask
- **Procesamiento de Imágenes**: OpenCV, Tesseract OCR
- **Automatización Web**: Selenium
- **Estilización**: TailwindCSS

## Contribución

¡Las contribuciones son bienvenidas! Por favor, lee nuestras pautas de contribución antes de enviar un pull request.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.

## Soporte

Si encuentras algún problema o tienes alguna pregunta, por favor abre un issue en el repositorio.

---

Desarrollado con ❤️ por [Tu Nombre]
