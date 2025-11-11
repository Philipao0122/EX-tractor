import { useState } from 'react';
import axios from 'axios';

interface ThumbnailItem {
  id: string;
  url: string;
  timestamp: number;
  error?: string;
}

interface InstagramThumbnailsProps {
  className?: string;
}

export default function InstagramThumbnails({ className = '' }: InstagramThumbnailsProps) {
  const [thumbnails, setThumbnails] = useState<ThumbnailItem[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState('');
  const [username, setUsername] = useState('');

  const fetchThumbnails = async () => {
    if (!username) {
      setError('Por favor ingresa un nombre de usuario o URL de Instagram');
      return;
    }

    setIsFetching(true);
    setError('');

    try {
      interface ThumbnailResponse {
        thumbnails?: string[];
        message?: string;
        error?: string;
      }

      const response = await axios.post<ThumbnailResponse>('http://localhost:5000/api/fetch-thumbnails', {
        username_or_url: username
      });

      if (response.data.thumbnails && response.data.thumbnails.length > 0) {
        const newThumbnails = response.data.thumbnails.map((url: string, index: number) => ({
          id: `thumb-${Date.now()}-${index}`,
          url: url,
          timestamp: Date.now()
        }));
        
        setThumbnails(newThumbnails);
      } else {
        setError('No se encontraron miniaturas para el usuario/URL proporcionado');
      }
    } catch (err) {
      console.error('Error fetching thumbnails:', err);
      setError('Error al obtener las miniaturas de Instagram');
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div className={`${className} border-t pt-8 mt-12`}>
      <h2 className="text-xl font-semibold mb-4">Servicio de Miniaturas de Instagram</h2>
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Nombre de usuario o URL de Instagram"
            className="flex-1 p-2 border rounded"
            onKeyDown={(e) => e.key === 'Enter' && fetchThumbnails()}
          />
          <button
            onClick={fetchThumbnails}
            disabled={isFetching}
            className={`px-4 py-2 rounded text-white ${isFetching ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isFetching ? 'Cargando...' : 'Obtener Miniaturas'}
          </button>
        </div>

        {error && (
          <div className="text-red-500 text-sm mb-4 p-2 bg-red-50 rounded">
            {error}
          </div>
        )}

        {thumbnails.length > 0 && (
          <div className="mt-4">
            <h3 className="text-lg font-medium mb-2">Miniaturas Obtenidas:</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {thumbnails.map((thumb) => (
                <div key={thumb.id} className="relative group">
                  <img 
                    src={thumb.url} 
                    alt="Instagram thumbnail"
                    className="w-full h-32 object-cover rounded border border-gray-200 hover:shadow-md transition-shadow"
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <a 
                      href={thumb.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-white bg-black bg-opacity-50 p-2 rounded-full hover:bg-opacity-70"
                      title="Ver imagen completa"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                      </svg>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
