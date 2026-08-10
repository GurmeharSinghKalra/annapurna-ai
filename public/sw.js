/**
 * Offline shell for Annapurna AI.
 *
 * Build assets are content-hashed, so their names are not known when this file is
 * written. Rather than precache a guessed list, the worker caches same-origin
 * responses as they are fetched: the first online visit populates the cache and
 * later visits work offline.
 *
 * A miss is never answered with the app shell. Returning index.html for a missing
 * script or stylesheet makes the browser refuse the response and renders a blank
 * page, which is worse than a clean network error.
 */

const CACHE_NAME = 'annapurna-ai-v2';
const APP_SHELL = '/index.html';
const PRECACHE = ['/', APP_SHELL, '/manifest.webmanifest', '/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // Added individually so one missing file cannot fail the whole install.
      Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => undefined)))
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

async function networkFirst(request, { fallbackToShell = false } = {}) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (fallbackToShell) {
      const shell = (await cache.match(APP_SHELL)) || (await cache.match('/'));
      if (shell) return shell;
    }
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Navigations resolve to the app shell so client-side routes work offline.
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, { fallbackToShell: true }));
    return;
  }

  // Hashed build output never changes under the same name.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  event.respondWith(networkFirst(request));
});
