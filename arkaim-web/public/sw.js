/**
 * Service Worker — оффлайн-кэш для «Наследие Аркаима»
 *
 * Стратегии:
 * - Static assets (JS/CSS/fonts): Cache First
 * - Images: Cache First с network fallback
 * - API GET: Network First с cache fallback
 * - API mutations (POST/PUT/DELETE): Network Only
 * - Navigation: Network First с offline fallback
 */

const CACHE_NAME = 'arkaim-v1';
const STATIC_CACHE = 'arkaim-static-v1';
const IMAGE_CACHE = 'arkaim-images-v1';
const API_CACHE = 'arkaim-api-v1';
const OFFLINE_URL = '/offline.html';

const STATIC_ASSETS = [
  '/',
  '/offline.html',
  '/about',
  '/library',
  '/genres',
  '/reading',
];

// ── Install ──────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {
        // Игнорируем ошибки кэширования начальных страниц
      });
    })
  );
  self.skipWaiting();
});

// ── Activate ─────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== IMAGE_CACHE && name !== API_CACHE)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// ── Fetch ────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Пропускаем не-GET запросы
  if (request.method !== 'GET') return;

  // Пропускаемchrome-extension и прочие не-http
  if (!url.protocol.startsWith('http')) return;

  // Навигация — Network First
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
    return;
  }

  // Изображения — Cache First
  if (isImageRequest(request)) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
    return;
  }

  // Статические ресурсы (JS/CSS/fonts) — Cache First
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // API запросы — Network First с кэшем
  if (isApiRequest(url)) {
    event.respondWith(networkFirstWithCache(request, API_CACHE));
    return;
  }

  // По умолчанию — Network First
  event.respondWith(networkFirst(request));
});

// ── Стратегии ────────────────────────────────────────

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch {
    // Для навигации — offline fallback
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match(OFFLINE_URL);
      return offlineResponse || new Response('Offline', {
        status: 503,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    }
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ── Хелперы ──────────────────────────────────────────

function isImageRequest(request) {
  return request.destination === 'image' ||
    request.url.match(/\.(png|jpg|jpeg|gif|webp|svg|ico)$/i);
}

function isStaticAsset(url) {
  return url.pathname.match(/\.(js|css|woff2?|ttf|eot)$/i) ||
    url.pathname.startsWith('/_next/static/');
}

function isApiRequest(url) {
  return url.pathname.startsWith('/book/') ||
    url.pathname.startsWith('/auth/') ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/xray/') ||
    url.pathname.startsWith('/analytics') ||
    url.pathname.startsWith('/v1/');
}
