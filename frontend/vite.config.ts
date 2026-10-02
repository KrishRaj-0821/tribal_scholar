import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['mota-logo.png', 'mota-logo.svg', 'pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'Ministry of Tribal Affairs - Tribal Scholar Platform',
        short_name: 'TribalScholar',
        description: 'AI-Enabled Scholarship and Fellowship Management System (MoTA SIH 26239)',
        theme_color: '#1D0A69',
        background_color: '#F4F6F8',
        display: 'standalone',
        icons: [
          {
            src: '/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          {
            urlPattern: /^\/api\/.*/,
            handler: 'NetworkOnly',
            options: {
              backgroundSync: {
                name: 'api-sync-queue',
                options: {
                  maxRetentionTime: 24 * 60
                }
              }
            }
          }
        ]
      }
    })

  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
