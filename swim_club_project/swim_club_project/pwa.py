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

SERVICE_WORKER = """
const CACHE_NAME = "alphaacademy-static-v11";
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
                    const offlinePage = await caches.match("/static/offline.html");
                    if (offlinePage) return offlinePage;

                    return new Response("You are offline.", {
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
            fetch(event.request)
                .then(async (response) => {
                    if (!response.ok) return response;

                    try {
                        const cache = await caches.open(CACHE_NAME);
                        await cache.put(event.request, response.clone());
                    } catch (error) {
                        console.error("Unable to cache a static resource.", error);
                    }
                    return response;
                })
                .catch(async () => {
                    const cachedResponse = await caches.match(event.request);
                    if (cachedResponse) return cachedResponse;
                    throw new Error("Static resource unavailable while offline.");
                })
        );
    }
});
""".strip()


def manifest(request):
    return HttpResponse(MANIFEST, content_type="application/manifest+json")


def service_worker(request):
    return HttpResponse(
        SERVICE_WORKER,
        content_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )
