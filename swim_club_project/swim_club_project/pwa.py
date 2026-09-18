from django.http import HttpResponse


MANIFEST = """
{
    "name": "Alpha Academy Kulup Yonetim Paneli",
    "short_name": "Alpha",
    "description": "Alpha Academy spor kulubu yonetim paneli",
    "start_url": "/dashboard/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait-primary",
    "background_color": "#ffffff",
    "theme_color": "#ffffff",
    "lang": "tr-TR",
    "icons": [
        {
            "src": "/media/logos/new_logo.png",
            "sizes": "1024x1024",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/media/logos/new_logo.png",
            "sizes": "1024x1024",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ]
}
""".strip()

SERVICE_WORKER = """
const CACHE_NAME = "alphaacademy-static-v6";
const STATIC_ASSETS = [
    "/manifest.webmanifest",
    "/static/css/app.css",
    "/static/js/htmx.min.js",
    "/media/logos/fk1.png",
    "/media/logos/new_logo.png"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
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

    const isStaticAsset = requestUrl.pathname.startsWith("/static/");
    const isLogo = requestUrl.pathname.startsWith("/media/logos/");

    if (isStaticAsset || isLogo) {
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (!response.ok) return response;

                    const responseCopy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseCopy);
                    });
                    return response;
                })
                .catch(() => caches.match(event.request))
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
