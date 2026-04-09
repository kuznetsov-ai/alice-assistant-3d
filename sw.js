const CACHE = "alisa-v8";
const STATIC = ["/", "/index.html", "/manifest.json"];

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(STATIC)));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  );
  return self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Never cache API calls or VRM models
  if (e.request.url.includes("/api/") || e.request.url.endsWith(".vrm")) {
    return;
  }
  e.respondWith(
    fetch(e.request).then((resp) => {
      const clone = resp.clone();
      caches.open(CACHE).then((c) => c.put(e.request, clone));
      return resp;
    }).catch(() => caches.match(e.request)),
  );
});
