import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { execSync } from 'child_process';

// Función para abrir el navegador de forma compatible con Windows
const openBrowser = (url: string) => {
  const start = process.platform === 'win32' ? 'start' : 'xdg-open';
  try {
    execSync(`${start} ${url.replace(/&/g, '^&')}`, { stdio: 'ignore' });
  } catch (e) {
    console.warn('No se pudo abrir el navegador automáticamente');
  }
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [react()],
  root: '.',
  publicDir: 'public',
  server: {
    port: 3000, // Cambiado a 3000 para coincidir con tu configuración de Docker
    host: '0.0.0.0', // Aceptar conexiones de cualquier IP
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/instagram': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/instagram/, '')
      }
    },
    // Deshabilitar apertura automática del navegador para evitar errores en Docker
    open: false,
    strictPort: true, // No intentar puertos alternativos si el 3000 está ocupado
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
});
