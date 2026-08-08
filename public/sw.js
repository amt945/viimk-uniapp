/* VIIMK PWA Service Worker
 * 策略：
 *   · App Shell（index.html / manifest / icons）: 安装时预缓存，请求时 CacheFirst（网络不可达走缓存）
 *   · 静态资源 (assets/*.js / assets/*.css / static/**)：StaleWhileRevalidate
 *     —— 优先用缓存秒开，后台异步拉取新版本
 *   · API 请求 (/api/**、/__pyapi/**)：NetworkFirst，失败时 fallback 静默
 *   · m3u8 / 视频文件：默认不缓存（视频一般大，且是流式）
 */
const CACHE_VERSION = 'viimk-v1';
const SHELL_CACHE = `shell-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;

// App Shell —— 这些文件在安装阶段就缓存，离线可直接秒开
const PRECACHE_URLS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './static/icons/icon-192.png',
  './static/icons/icon-512.png',
  './static/icons/icon-512-maskable.png',
  './static/icons/apple-touch-icon-180.png',
  './static/hls.min.js'
];

const isApiRequest = (url) => {
  const p = url.pathname;
  return p.includes('/api/') || p.includes('/__pyapi/');
};
const isStaticAsset = (url) => {
  const p = url.pathname;
  return (
    p.startsWith('/assets/') ||
    p.includes('/assets/') ||
    p.startsWith('/static/') ||
    p.includes('/static/') ||
    /\.(?:css|js|json|png|jpg|jpeg|gif|webp|svg|woff2?|ttf|eot|otf|wasm)$/i.test(p)
  );
};
const isVideo = (url) => {
  const p = url.pathname;
  return /\.(?:m3u8|mp4|m4s|ts|flv|mkv|webm|mov|aac|mp3)$/i.test(p) || p.includes('/stream');
};

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(PRECACHE_URLS)).catch((err) => {
      console.warn('[SW] precache failed (some files may not exist yet)', err);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== RUNTIME_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting().then(() => self.clients.claim());
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const res = await fetch(request);
    if (res && res.status === 200 && res.type !== 'opaque') {
      const clone = res.clone();
      caches.open(SHELL_CACHE).then((c) => c.put(request, clone));
    }
    return res;
  } catch (e) {
    // 离线时 shell 回退到 index.html（SPA 路由）
    return (await caches.match('./index.html')) || Response.error();
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const networkPromise = fetch(request)
    .then((res) => {
      if (res && res.status === 200 && res.type !== 'opaque') {
        const clone = res.clone();
        caches.open(RUNTIME_CACHE).then((c) => c.put(request, clone));
      }
      return res;
    })
    .catch(() => cached || Response.error());
  return cached || networkPromise;
}

async function networkFirst(request) {
  try {
    const res = await fetch(request, { credentials: 'same-origin' });
    return res;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // API 离线无缓存 → 返回空 JSON，让前端自行处理错误
    if (isApiRequest(new URL(request.url))) {
      return new Response(JSON.stringify({ code: 600, msg: '离线状态', data: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    return Response.error();
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // 同域才处理，跨域（如腾讯 SCF、m3u8 源站）不拦
  if (url.origin !== location.origin) return;
  // 视频：不缓存
  if (isVideo(url)) return;
  // API 请求：网络优先
  if (isApiRequest(url)) {
    event.respondWith(networkFirst(req));
    return;
  }
  // 静态资源：SWR
  if (isStaticAsset(url)) {
    event.respondWith(staleWhileRevalidate(req));
    return;
  }
  // index.html 等页面：缓存优先（离线可开），回退到 index.html
  event.respondWith(cacheFirst(req));
});
