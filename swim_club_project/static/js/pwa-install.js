(function () {
    "use strict";

    var banner = document.getElementById("pwa-install");
    if (!banner) return;

    var DISMISS_KEY = "pwa-install-dismissed-at";
    var DISMISS_DAYS = 7;
    var SHOW_DELAY_MS = 2500;
    var text = banner.querySelector("[data-pwa-text]");
    var installBtn = banner.querySelector("[data-pwa-install]");
    var closeBtn = banner.querySelector("[data-pwa-dismiss]");
    var deferredPrompt = null;
    var showTimer = null;

    var isStandalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;
    var isIos =
        /iphone|ipad|ipod/i.test(window.navigator.userAgent) ||
        (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

    function dismissedRecently() {
        try {
            var at = parseInt(localStorage.getItem(DISMISS_KEY), 10);
            return Boolean(at && Date.now() - at < DISMISS_DAYS * 86400000);
        } catch (e) {
            return false;
        }
    }

    function saveDismissal() {
        try {
            localStorage.setItem(DISMISS_KEY, String(Date.now()));
        } catch (e) {}
    }

    function scheduleShow() {
        if (showTimer || isStandalone || dismissedRecently()) return;
        showTimer = window.setTimeout(function () {
            showTimer = null;
            if (!isStandalone && !dismissedRecently()) {
                banner.hidden = false;
            }
        }, SHOW_DELAY_MS);
    }

    function hide() {
        if (showTimer) {
            clearTimeout(showTimer);
            showTimer = null;
        }
        banner.hidden = true;
    }

    if (isStandalone || dismissedRecently()) return;

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;
        if (installBtn) installBtn.hidden = false;
        scheduleShow();
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        hide();
    });

    if (isIos) {
        if (text) {
            text.textContent =
                "Uygulamayı yüklemek için Paylaş simgesine dokunup “Ana Ekrana Ekle”yi seçin.";
        }
        if (installBtn) installBtn.hidden = true;
        scheduleShow();
    }

    if (installBtn) {
        installBtn.addEventListener("click", function () {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            deferredPrompt.userChoice
                .then(function (choiceResult) {
                    if (choiceResult && choiceResult.outcome === "dismissed") {
                        saveDismissal();
                    }
                })
                .finally(function () {
                    deferredPrompt = null;
                    hide();
                });
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", function () {
            saveDismissal();
            hide();
        });
    }
})();