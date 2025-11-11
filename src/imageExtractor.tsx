import { useState, useEffect } from 'react';
import { InstagramScraper } from './services/instagramScraper';

interface ImageItem {
  id: string;
  url: string;
  timestamp: number;
  extractedText?: string;
  processing?: boolean;
  error?: string;
  analysis?: string;
}

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
          
          updatedImages[i] = { 
            ...img, 
            extractedText: response.data.text,
            processing: false 
          };
          hasChanges = true;
        } else {
          throw new Error(response.data.error || 'No se pudo extraer texto de la imagen');
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
        console.error(`Error processing image ${i + 1}:`, errorMessage);
        updatedImages[i] = { 
          ...img, 
          error: errorMessage,
          processing: false 
        };
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

  return (
    <div className="p-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-4">Extractor de Imágenes de Instagram</h1>
        <div className="flex flex-col gap-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Pega la URL de Instagram"
              className="flex-1 p-2 border rounded"
            />
            <button
              onClick={handleExtract}
              disabled={isLoading}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300 whitespace-nowrap"
            >
              {isLoading ? 'Extrayendo...' : 'Extraer Imagen'}
            </button>
          </div>
          <div>
            <button
              onClick={contrastImages}
              disabled={!images.length || isExtracting || isAnalyzing}
              className={`bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 ${
                !images.length || isExtracting || isAnalyzing ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {isExtracting ? 'Extrayendo texto...' : isAnalyzing ? 'Analizando...' : 'Contrastar'}
            </button>
            <p className="text-sm text-gray-500 mt-1">Extrae texto y analiza con Gemini</p>
          </div>
        </div>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>
      <div className="mt-6">
        {images.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            {images.map((img) => (
              <div key={img.id} className="relative group">
                <img 
                  src={img.url} 
                  alt={`Instagram ${img.id}`} 
                  className="w-full max-h-[80vh] object-contain rounded-lg bg-gray-100"
                  style={{ maxWidth: '100%', height: 'auto' }}
                />
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-50 transition-all duration-300 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <button
                    onClick={() => {
                      const newImages = images.filter(i => i.id !== img.id);
                      setImages(newImages);
                      localStorage.setItem('savedInstagramImages', JSON.stringify(newImages));
                    }}
                    className="bg-red-500 text-white p-2 rounded-full hover:bg-red-600 transition-colors"
                    title="Eliminar imagen"
                  >
                    🗑️
                  </button>
                </div>
                
                {/* Image Info Overlay */}
                <div className="absolute bottom-0 left-0 right-0 p-2 space-y-1">
                  {/* Timestamp */}
                  <div className="bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded inline-block">
                    {new Date(img.timestamp).toLocaleTimeString()}
                  </div>
                  
                  {/* Extracted Text Preview */}
                  {img.extractedText && (
                    <div className="bg-black bg-opacity-70 text-white text-xs p-2 rounded max-h-20 overflow-y-auto">
                      <p className="break-words">
                        {img.extractedText.length > 100 
                          ? `${img.extractedText.substring(0, 100)}...` 
                          : img.extractedText}
                      </p>
                    </div>
                  )}
                  
                  {/* Analysis Preview */}
                  {img.analysis && (
                    <div className="bg-purple-800 bg-opacity-80 text-white text-xs p-2 rounded max-h-20 overflow-y-auto mt-1">
                      <p className="break-words">
                        {img.analysis.length > 100 
                          ? `${img.analysis.substring(0, 100)}...` 
                          : img.analysis}
                      </p>
                    </div>
                  )}
                  
                  {/* Error Message */}
                  {img.error && (
                    <div className="bg-red-600 bg-opacity-80 text-white text-xs p-2 rounded">
                      Error: {img.error}
                    </div>
                  )}
                  
                  {/* Processing Indicator */}
                  {img.processing && (
                    <div className="bg-blue-600 bg-opacity-80 text-white text-xs p-2 rounded flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                      Procesando...
                    </div>
                  )}
                  
                  {/* Analyzing Indicator */}
                  {isAnalyzing && (
                    <div className="bg-purple-600 bg-opacity-80 text-white text-xs p-2 rounded flex items-center mt-1">
                      <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                      Analizando con Gemini...
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="text-center text-gray-500 py-8 border-2 border-dashed rounded-lg">
          No hay imágenes guardadas. Agrega una imagen para comenzar.
        </div>
      </div>
      
      {error && (
        <p className="text-red-500 mt-2 p-2 bg-red-50 rounded">
          {error}
        </p>
      )}
    </div>
  );
}