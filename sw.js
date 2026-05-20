// Service Worker para Machine Box PWA
const CACHE_NAME = 'machinebox-v3';

self.addEventListener('install', event => {
    console.log('SW instalado');
    self.skipWaiting();  // 👈 Fuerza activación inmediata
});

self.addEventListener('activate', event => {
    console.log('SW activado');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.map(key => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();  // 👈 Toma control inmediato
});

self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});