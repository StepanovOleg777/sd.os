const CACHE_NAME = "sdos-static-v2";

const PRECACHE_URLS = [
    "/static/manifest.webmanifest",
    "/static/icons/sdos-icon-192.png",
    "/static/icons/sdos-icon-512.png",
    "/static/icons/apple-touch-icon.png",
];


self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then((cache) => cache.addAll(PRECACHE_URLS))
    );

    self.skipWaiting();
});


self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((cacheNames) =>
                Promise.all(
                    cacheNames
                        .filter(
                            (cacheName) =>
                                cacheName !== CACHE_NAME
                        )
                        .map(
                            (cacheName) =>
                                caches.delete(cacheName)
                        )
                )
            )
    );

    self.clients.claim();
});


self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (url.origin !== self.location.origin) {
        return;
    }

    if (!url.pathname.startsWith("/static/")) {
        return;
    }


    // =====================================================
    // CSS / JS
    // Всегда сначала сеть, кэш только как резерв
    // =====================================================

    if (
        url.pathname.endsWith(".css")
        ||
        url.pathname.endsWith(".js")
    ) {
        event.respondWith(
            fetch(request)
                .then((networkResponse) => {
                    if (
                        !networkResponse
                        ||
                        networkResponse.status !== 200
                    ) {
                        return networkResponse;
                    }

                    const responseToCache =
                        networkResponse.clone();

                    caches
                        .open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(
                                request,
                                responseToCache
                            );
                        });

                    return networkResponse;
                })
                .catch(async () => {
                    const cachedResponse =
                        await caches.match(request);

                    if (cachedResponse) {
                        return cachedResponse;
                    }

                    throw new Error(
                        "Network unavailable and no cached response."
                    );
                })
        );

        return;
    }


    // =====================================================
    // Остальная статика
    // Кэш сначала, сеть если нет в кэше
    // =====================================================

    event.respondWith(
        caches
            .match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                return fetch(request).then(
                    (networkResponse) => {
                        if (
                            !networkResponse
                            ||
                            networkResponse.status !== 200
                        ) {
                            return networkResponse;
                        }

                        const responseToCache =
                            networkResponse.clone();

                        caches
                            .open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(
                                    request,
                                    responseToCache
                                );
                            });

                        return networkResponse;
                    }
                );
            })
    );
});