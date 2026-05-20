// Service Worker para Admin Machine Box
const CACHE_NAME = 'admin-machinebox-v1';

self.addEventListener('install', event => {
    console.log('SW Admin instalado');
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    console.log('SW Admin activado');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.map(key => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();
});

self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});