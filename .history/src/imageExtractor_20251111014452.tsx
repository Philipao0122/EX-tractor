import { useState, useEffect } from 'react';
import { InstagramScraper } from './services/instagramScraper';
import axios from 'axios';
import InstagramThumbnails from './components/InstagramThumbnails';

interface ImageItem {
  id: string;
  url: string;
  timestamp: number;
  extractedText?: string;
  processing?: boolean;
  error?: string;
  analysis?: string;
}

// ThumbnailItem interface has been moved to InstagramThumbnails component

interface ApiResponse {
  success: boolean;
  image_url?: string;
  error?: string;
  text?: string;
}

interface ExtractTextResponse {
  success: boolean;
  text?: string;
  error?: string;
}

interface ExtractImageResponse {
  success: boolean;
  image_url?: string;
  error?: string;
}

export default function ImageExtractor() {
  const [url, setUrl] = useState('');
  const [images, setImages] = useState<ImageItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);


  // Create scraper instance with API key
  const scraper = new InstagramScraper({
    apiKey: '3e2a25eb4b2f0107dc145aaf9a7fafb3', // Using direct API key for now
  });

  // Load saved images from localStorage on component mount
  useEffect(() => {
    const savedImages = localStorage.getItem('savedInstagramImages');
    if (savedImages) {
      try {
        const parsed = JSON.parse(savedImages);
        const cleanedImages = parsed.map((img: any) => ({
          id: img.id || Date.now().toString(),
          url: img.url,
          timestamp: img.timestamp || Date.now()
        }));
        setImages(cleanedImages);
      } catch (e) {
        console.error('Error parsing saved images:', e);
      }
    }
  }, []);

  // Unified function to extract text and analyze with Gemini
  const contrastImages = async () => {
    if (isExtracting || isAnalyzing) return;

    console.log('Starting unified contrast flow...');
    setIsExtracting(true);
    setError('');

    const updatedImages = [...images];
    let hasChanges = false;

    // Step 1: Extract text from images
    for (let i = 0; i < updatedImages.length; i++) {
      const img = updatedImages[i];
      console.log(`Processing image ${i + 1}/${updatedImages.length}`);

      try {
        // Mark as processing
        updatedImages[i] = { ...img, processing: true, error: undefined };
        setImages([...updatedImages]);

        console.log(`Extracting text from image ${i + 1}...`);
        const response = await axios.post<ExtractTextResponse>(
          'http://localhost:5000/extract-text',
          { image_url: img.url }
        );

        if (response.data.success && response.data.text) {
          const previewText = response.data.text.substring(0, 50) + (response.data.text.length > 50 ? '...' : '');
          console.log(`Successfully extracted text from image ${i + 1}:`, previewText);

          updatedImages[i] = { ...img, extractedText: response.data.text, processing: false };
          hasChanges = true;
        } else {
          throw new Error(response.data.error || 'No se pudo extraer texto de la imagen');
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
        console.error(`Error processing image ${i + 1}:`, errorMessage);
        updatedImages[i] = { ...img, error: errorMessage, processing: false };
        hasChanges = true;
      }

      // Update state after each image to show progress
      if (hasChanges) {
        const newImages = [...updatedImages];
        setImages(newImages);
        localStorage.setItem('savedInstagramImages', JSON.stringify(newImages));
      }
    }

    if (!hasChanges) {
      console.log('No new images to process');
      setError('No hay imágenes nuevas para procesar');
      setIsExtracting(false);
      return;
    }

    setIsExtracting(false);

    // Step 2: Trigger Gemini analysis
    try {
      setIsAnalyzing(true);
      console.log('Starting Gemini analysis...');

      // Call a new endpoint that will trigger the Gemini analysis
      interface AnalyzeTextsResponse {
        success: boolean;
        analysis?: string;
        error?: string;
      }

      const response = await axios.post<AnalyzeTextsResponse>('http://localhost:5000/analyze-texts');

      if (response.data.success) {
        console.log('Gemini analysis completed successfully');

        // If the analysis returns content, we can update the UI with it
        if (response.data.analysis) {
          // Store the analysis in state or display it
          const updatedImagesWithAnalysis = updatedImages.map(img => ({
            ...img,
            analysis: response.data.analysis
          }));

          setImages(updatedImagesWithAnalysis);
          localStorage.setItem('savedInstagramImages', JSON.stringify(updatedImagesWithAnalysis));
        }
      } else {
        throw new Error(response.data.error || 'Error en el análisis de Gemini');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido en el análisis';
      console.error('Error during Gemini analysis:', errorMessage);
      setError(`Error en el análisis: ${errorMessage}`);
    } finally {
      setIsAnalyzing(false);
      console.log('Unified contrast flow completed');
    }
  };

  const handleExtract = async () => {
    if (!url) {
      setError('Por favor ingresa una URL de Instagram');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Extract username from URL if it's a profile URL
      let username = url;
      if (url.includes('instagram.com/')) {
        const match = url.match(/instagram\.com\/([^/]+)/);
        if (match && match[1]) {
          username = match[1];
        }
      }

      // Get posts using the scraper
      const response = await scraper.getUserPosts(username);

      if (response.data && response.data.length > 0) {
        const newImages = response.data.map((post: any) => ({
          id: post.id || `post-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          url: post.media_url,
          timestamp: post.timestamp ? new Date(post.timestamp).getTime() : Date.now(),
          caption: post.caption || '',
        }));

        // Update state with new images
        setImages(prevImages => {
          const updatedImages = [...prevImages, ...newImages];
          // Save to localStorage
          localStorage.setItem('savedInstagramImages', JSON.stringify(updatedImages));
          return updatedImages;
        });

        setUrl(''); // Clear the input after successful extraction
      } else {
        throw new Error('No se encontraron publicaciones en este perfil');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido al extraer la imagen';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // La funcionalidad de miniaturas se ha movido al componente InstagramThumbnails

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Extractor de Imágenes de Instagram</h1>
      
      {/* Formulario para extraer imágenes */}
      <div className="mb-8">
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Ingresa la URL de un perfil de Instagram"
            className="flex-1 p-2 border rounded"
            onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
          />
          <button
            onClick={handleExtract}
            disabled={isLoading}
            className={`px-4 py-2 rounded text-white ${isLoading ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isLoading ? 'Extrayendo...' : 'Extraer Imágenes'}
          </button>
        </div>
        
        {error && (
          <p className="text-red-500 mt-2 p-2 bg-red-50 rounded">
            {error}
          </p>
        )}
      </div>

      {/* Contenedor de imágenes extraídas */}
      {images.length > 0 && (
        <div className="mb-12">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Imágenes Extraídas</h2>
            <button
              onClick={contrastImages}
              disabled={isExtracting || isAnalyzing}
              className={`px-4 py-2 rounded text-white ${isExtracting || isAnalyzing ? 'bg-purple-400' : 'bg-purple-600 hover:bg-purple-700'}`}
            >
              {isExtracting ? 'Extrayendo texto...' : isAnalyzing ? 'Analizando...' : 'Extraer Texto y Analizar'}
            </button>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {images.map((img) => (
              <div key={img.id} className="relative group bg-white rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-shadow">
                <img 
                  src={img.url} 
                  alt={`Instagram ${img.id}`} 
                  className="w-full h-48 object-cover"
                />
                
                {/* Botón de eliminar */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => {
                      const newImages = images.filter(i => i.id !== img.id);
                      setImages(newImages);
                      localStorage.setItem('savedInstagramImages', JSON.stringify(newImages));
                    }}
                    className="bg-red-500 text-white p-1.5 rounded-full hover:bg-red-600 transition-colors"
                    title="Eliminar imagen"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
                
                {/* Información de la imagen */}
                <div className="p-3">
                  {/* Texto extraído */}
                  {img.extractedText && (
                    <div className="mb-2">
                      <h4 className="text-sm font-medium text-gray-700 mb-1">Texto Extraído:</h4>
                      <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded max-h-20 overflow-y-auto">
                        {img.extractedText.length > 100 
                          ? `${img.extractedText.substring(0, 100)}...` 
                          : img.extractedText}
                      </p>
                    </div>
                  )}
                  
                  {/* Análisis */}
                  {img.analysis && (
                    <div className="mb-2">
                      <h4 className="text-sm font-medium text-purple-700 mb-1">Análisis:</h4>
                      <p className="text-xs text-gray-700 bg-purple-50 p-2 rounded max-h-20 overflow-y-auto">
                        {img.analysis.length > 100 
                          ? `${img.analysis.substring(0, 100)}...` 
                          : img.analysis}
                      </p>
                    </div>
                  )}
                  
                  {/* Estado */}
                  <div className="flex justify-between items-center text-xs text-gray-500 mt-2">
                    <span>{new Date(img.timestamp).toLocaleString()}</span>
                    {img.processing && (
                      <span className="flex items-center text-blue-600">
                        <div className="animate-spin rounded-full h-3 w-3 border-t-2 border-b-2 border-blue-600 mr-1"></div>
                        Procesando...
                      </span>
                    )}
                    {img.error && (
                      <span className="text-red-500">Error</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Componente de Miniaturas de Instagram */}
      <InstagramThumbnails />
    </div>
  );
}