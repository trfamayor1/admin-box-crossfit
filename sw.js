// Service Worker para Machine Box PWA
const CACHE_NAME = 'machinebox-v1';

self.addEventListener('install', event => {
    self.skipWaiting();
    console.log('Service Worker instalado');
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.map(key => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    self.clients.claim();
    console.log('Service Worker activado');
});

self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});