FROM python:3.9-slim  
  
# Instalar dependencias del sistema (Tesseract, Chrome para Selenium)  
RUN apt-get update && apt-get install -y \  
    tesseract-ocr \  
    tesseract-ocr-spa \  
    tesseract-ocr-eng \  
    chromium \  
    chromium-driver \  
    && rm -rf /var/lib/apt/lists/*  
  
WORKDIR /app  
  
# Copiar requirements  
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt  
  
# Copiar código de la aplicación  
COPY . .  
  
# Crear directorio temp  
RUN mkdir -p temp  
  
EXPOSE 5000  
  
CMD ["python", "app.py"]