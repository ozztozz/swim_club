(function () {
    "use strict";

    var banner = document.getElementById("pwa-install");
    if (!banner) return;

    var DISMISS_KEY = "pwa-install-dismissed-at";
    var DISMISS_DAYS = 7;
    var text = banner.querySelector("[data-pwa-text]");
    var installBtn = banner.querySelector("[data-pwa-install]");
    var closeBtn = banner.querySelector("[data-pwa-dismiss]");
    var deferredPrompt = null;

    var isStandalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;
    var isIos =
        /iphone|ipad|ipod/i.test(window.navigator.userAgent) ||
        (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

    function dismissedRecently() {
        try {
            var at = parseInt(localStorage.getItem(DISMISS_KEY), 10);
            return at && Date.now() - at < DISMISS_DAYS * 86400000;
        } catch (e) {
            return false;
        }
    }

    function show() {
        banner.hidden = false;
    }

    function hide() {
        banner.hidden = true;
    }

    if (isStandalone || dismissedRecently()) return;

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;
        show();
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        hide();
    });

    if (isIos) {
        text.textContent =
            "Uygulamayı yüklemek için Paylaş simgesine dokunup “Ana Ekrana Ekle”yi seçin.";
        installBtn.hidden = true;
        show();
    }

    installBtn.addEventListener("click", function () {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        deferredPrompt.userChoice.finally(function () {
            deferredPrompt = null;
            hide();
        });
    });

    closeBtn.addEventListener("click", function () {
        try {
            localStorage.setItem(DISMISS_KEY, String(Date.now()));
        } catch (e) {}
        hide();
    });
})();