// Offline cache. syllabus.json is network-first so edits show up immediately when online;
// the rest of the app shell is stale-while-revalidate (served from cache, refreshed in the background).
// Bump CACHE_VERSION when the SHELL list changes (e.g. a new Alpine version).
const CACHE_VERSION = 'judo-v4';
const SHELL = [
  './',
  'index.html',
  'style.css',
  'syllabus.json',
  'icon.svg',
  'manifest.webmanifest',
  'https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  const isShell = SHELL.some((path) => new URL(path, self.registration.scope).href === url.href);
  if (!isShell) return; // YouTube thumbnails etc. go straight to the network.

  if (url.pathname.endsWith('/syllabus.json')) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  event.respondWith(
    caches.open(CACHE_VERSION).then(async (cache) => {
      const cached = await cache.match(request);
      const refresh = fetch(request)
        .then((res) => {
          if (res.ok) cache.put(request, res.clone());
          return res;
        })
        .catch(() => cached);
      if (cached) event.waitUntil(refresh);
      return cached || refresh;
    })
  );
});
