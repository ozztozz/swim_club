(function () {
    "use strict";

    var status = document.getElementById("pwa-status");
    if (!status) return;

    var offlineMessage = status.querySelector("[data-pwa-offline]");
    var updatePanel = status.querySelector("[data-pwa-update]");
    var updateButton = status.querySelector("[data-pwa-apply-update]");
    var dismissButton = status.querySelector("[data-pwa-dismiss-update]");
    var UPDATE_DISMISSED_KEY = "pwa-update-dismissed-at";
    var UPDATE_DISMISS_MS = 24 * 60 * 60 * 1000;
    var registration = null;
    var updateAccepted = false;
    var wasOffline = !navigator.onLine;

    function updateDismissedRecently() {
        try {
            var dismissedAt = Number(localStorage.getItem(UPDATE_DISMISSED_KEY));
            return dismissedAt > 0 && Date.now() - dismissedAt < UPDATE_DISMISS_MS;
        } catch (error) {
            console.warn("Unable to read the PWA update dismissal preference.", error);
            return false;
        }
    }

    function refreshStatus() {
        offlineMessage.hidden = navigator.onLine;
        status.hidden = navigator.onLine && updatePanel.hidden;
    }

    function showUpdate() {
        if (updateDismissedRecently()) return;
        updatePanel.hidden = false;
        refreshStatus();
    }

    window.addEventListener("online", function () {
        refreshStatus();

        if (wasOffline && typeof window.showToast === "function") {
            window.showToast("Ağ bağlantısı yeniden etkin.");
        }
        wasOffline = false;
    });
    window.addEventListener("offline", function () {
        wasOffline = true;
        refreshStatus();
    });

    if (dismissButton) dismissButton.addEventListener("click", function () {
        updatePanel.hidden = true;
        try {
            localStorage.setItem(UPDATE_DISMISSED_KEY, String(Date.now()));
        } catch (error) {
            console.warn("Unable to save the PWA update dismissal preference.", error);
        }
        refreshStatus();
    });

    if (updateButton) updateButton.addEventListener("click", function () {
        if (!registration || !registration.waiting) return;
        updateAccepted = true;
        registration.waiting.postMessage({ type: "SKIP_WAITING" });
        updateButton.disabled = true;
    });

    refreshStatus();

    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.addEventListener("controllerchange", function () {
        if (updateAccepted) window.location.reload();
    });

    navigator.serviceWorker.register("/sw.js", { scope: "/" })
        .then(function (currentRegistration) {
            registration = currentRegistration;

            if (registration.waiting) showUpdate();

            registration.addEventListener("updatefound", function () {
                var installing = registration.installing;
                if (!installing) return;

                installing.addEventListener("statechange", function () {
                    if (
                        installing.state === "installed" &&
                        navigator.serviceWorker.controller
                    ) {
                        showUpdate();
                    }
                });
            });
        })
        .catch(function (error) {
            console.error("PWA service worker registration failed.", error);
            if (typeof window.showToast === "function") {
                window.showToast("Çevrimdışı destek başlatılamadı.");
            }
        });
})();
