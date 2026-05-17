// Service Worker - Admin Box CrossFit
// Versión definitiva sin caché problemático

const CACHE_NAME = 'admin-box-v1';

// Instalación - sin cachear nada
self.addEventListener('install', event => {
    console.log('SW Admin instalado');
    self.skipWaiting(); // Activar inmediatamente
});

// Activación - limpiar cualquier caché viejo
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.map(key => {
                if (key !== CACHE_NAME) {
                    console.log('Eliminando caché viejo:', key);
                    return caches.delete(key);
                }
            }));
        })
    );
    self.clients.claim(); // Tomar control de todas las pestañas
    console.log('SW Admin activado - caché limpio');
});

// Fetch - Siempre ir a la red, nunca usar caché
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .catch(error => {
                console.error('Error de red:', error);
                // Si no hay internet, mostrar mensaje básico
                return new Response('Sin conexión a internet', {
                    status: 503,
                    statusText: 'Service Unavailable'
                });
            })
    );
});