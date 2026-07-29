/* Lamer Konekte service worker: app-shell precache + offline-first data caches. */
const SHELL = 'lamer-shell-v2'
const DATA = 'lamer-data-v2'
const SHELL_URLS = ['/', '/manifest.webmanifest', '/icon.svg', '/icons/icon-192.png', '/icons/icon-512.png']
const DATA_URLS = ['/api/species', '/api/config/public', '/api/demo/fixtures']

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(SHELL).then((c) => c.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => ![SHELL, DATA].includes(k)).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET') return

  // Data endpoints: network-first, fall back to cache (species catalogue,
  // config, fixtures, last marine forecast survive offline).
  if (DATA_URLS.includes(url.pathname) || url.pathname === '/api/marine-conditions') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone()
          caches.open(DATA).then((c) => c.put(e.request, copy))
          return res
        })
        .catch(() => caches.match(e.request))
    )
    return
  }

  // Other API calls: network only (analysis must never be silently faked offline).
  if (url.pathname.startsWith('/api')) return

  // Navigation / index.html: NETWORK-FIRST, cache only as an offline fallback.
  //
  // Serving a cached index.html after a redeploy points the browser at the
  // previous build's hashed asset filenames, which no longer exist -> 404 and a
  // broken page. The HTML is small; always prefer the fresh copy and fall back
  // to cache only when genuinely offline.
  if (e.request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone()
          caches.open(SHELL).then((c) => c.put(e.request, copy))
          return res
        })
        .catch(() => caches.match(e.request).then((hit) => hit || caches.match('/')))
    )
    return
  }

  // Hashed build assets are immutable, so cache-first is safe and fast: a new
  // build produces new filenames rather than changing these.
  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit
      return fetch(e.request).then((res) => {
        const copy = res.clone()
        caches.open(SHELL).then((c) => c.put(e.request, copy))
        return res
      })
    })
  )
})
