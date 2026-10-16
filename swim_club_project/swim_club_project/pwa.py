import hashlib
from django.conf import settings
from django.http import HttpResponse


MANIFEST = """
{
    "id": "/",
    "name": "Alpha Academy Kulüp Yönetim Paneli",
    "short_name": "Alpha",
    "description": "Alpha Academy spor kulübü yönetim paneli",
    "start_url": "/dashboard/",
    "scope": "/",
    "display": "standalone",
    "display_override": [
        "window-controls-overlay",
        "standalone"
    ],
    "orientation": "portrait-primary",
    "background_color": "#F1F1EF",
    "theme_color": "#F1F1EF",
    "lang": "tr-TR",
    "dir": "ltr",
    "prefer_related_applications": false,
    "categories": [
        "business",
        "sports"
    ],
    "icons": [
        {
            "src": "/media/logos/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/media/logos/icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/media/logos/icon-512-maskable.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable"
        }
    ]
}
""".strip()

TRACKED_STATIC_FILES = (
    "css/app.css",
    "js/app.js",
    "js/form-controls.js",
    "js/pwa-install.js",
    "js/pwa-runtime.js",
    "offline.html",
)


def _get_cache_version():
    """
    Takip edilen statik dosyaların son değiştirilme zamanı (mtime) ve boyutuna göre
    otomatik önbellek sürüm özeti (hash) üretir. Dosyalardan biri değiştiğinde
    CACHE_NAME otomatik değişir ve istemcilerde PWA güncelleme bildirimi tetiklenir.
    """
    hasher = hashlib.sha256()
    static_dir = settings.BASE_DIR / "static"

    for rel_path in TRACKED_STATIC_FILES:
        file_path = static_dir / rel_path
        try:
            stat = file_path.stat()
            hasher.update(f"{rel_path}:{stat.st_mtime_ns}:{stat.st_size};".encode("utf-8"))
        except OSError:
            hasher.update(f"{rel_path}:missing;".encode("utf-8"))

    return hasher.hexdigest()[:10]


SERVICE_WORKER_TEMPLATE = """
const CACHE_NAME = "alphaacademy-static-__CACHE_VERSION__";
const CACHE_PREFIX = "alphaacademy-static-";
const STATIC_ASSETS = [
    "/manifest.webmanifest",
    "/static/css/app.css",
    "/static/fonts/Manrope-Variable.woff2",
    "/static/js/app.js",
    "/static/js/form-controls.js",
    "/static/js/htmx.min.js",
    "/static/js/pwa-install.js",
    "/static/js/pwa-runtime.js",
    "/static/offline.html",
    "/media/logos/icon-192.png",
    "/media/logos/icon-512.png",
    "/media/logos/icon-512-maskable.png"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS))
    );
});

self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys
                    .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const requestUrl = new URL(event.request.url);

    if (event.request.method !== "GET" || requestUrl.origin !== self.location.origin) {
        return;
    }

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .catch(async () => {
                    const offlinePage = await caches.match("/static/offline.html", {
                        ignoreSearch: true
                    });
                    if (offlinePage) return offlinePage;

                    return new Response("Çevrimdışısınız.", {
                        status: 503,
                        headers: { "Content-Type": "text/plain; charset=utf-8" }
                    });
                })
        );
        return;
    }

    const isStaticAsset = requestUrl.pathname.startsWith("/static/");
    const isAppIcon = requestUrl.pathname.startsWith("/media/logos/icon-");

    if (isStaticAsset || isAppIcon) {
        event.respondWith(
            caches.open(CACHE_NAME).then(async (cache) => {
                const cachedResponse = await cache.match(event.request, {
                    ignoreSearch: true
                });

                const networkFetch = fetch(event.request)
                    .then((networkResponse) => {
                        if (networkResponse && networkResponse.ok) {
                            cache.put(event.request, networkResponse.clone()).catch(() => {});
                        }
                        return networkResponse;
                    })
                    .catch(() => null);

                if (cachedResponse) {
                    event.waitUntil(networkFetch);
                    return cachedResponse;
                }

                const freshResponse = await networkFetch;
                if (freshResponse) return freshResponse;

                throw new Error("Static resource unavailable while offline.");
            })
        );
    }
});
""".strip()


def manifest(request):
    return HttpResponse(MANIFEST, content_type="application/manifest+json; charset=utf-8")


def service_worker(request):
    sw_body = SERVICE_WORKER_TEMPLATE.replace("__CACHE_VERSION__", _get_cache_version())
    return HttpResponse(
        sw_body,
        content_type="application/javascript; charset=utf-8",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )

