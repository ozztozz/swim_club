(function () {
    "use strict";

    /* =========================================================
       HELPERS
       ========================================================= */

    function qs(selector, root = document) {
        return root.querySelector(selector);
    }

    function qsa(selector, root = document) {
        return Array.from(root.querySelectorAll(selector));
    }

    /* =========================================================
       MODAL MANAGEMENT
       ========================================================= */

    let modalReturnFocus = null;
    let modalCloseTimer = null;

    function getModalContainer() {
        return qs("#modal-container");
    }

    function getActiveModal() {
        const container = getModalContainer();
        if (!container || !container.classList.contains("is-open")) {
            return null;
        }
        return qs(".ui-modal, dialog", container);
    }

    function focusModal(modal) {
        const focusTarget = qsa("[autofocus], [data-modal-close]", modal).find(
            function (element) {
                return element.getClientRects().length > 0;
            }
        );

        if (focusTarget) {
            focusTarget.focus({ preventScroll: true });
            return;
        }

        modal.setAttribute("tabindex", "-1");
        modal.focus({ preventScroll: true });
    }

    function initializeModal(root = document) {
        const modal = qs(".ui-modal, dialog", root);
        if (!modal) return;

        if (window.AlphaFormControls) {
            window.AlphaFormControls.initializeModal(modal);
        }
    }

    function openModal() {
        const container = getModalContainer();
        if (!container) return;

        const modal = qs(".ui-modal, dialog", container);
        if (!modal) return;

        const isClosing = Boolean(modalCloseTimer);
        if (modalCloseTimer) {
            clearTimeout(modalCloseTimer);
            modalCloseTimer = null;
            container.classList.remove("is-closing");
        }

        const wasOpen = container.classList.contains("is-open") && !isClosing;
        if (!wasOpen && document.activeElement && !container.contains(document.activeElement)) {
            modalReturnFocus = document.activeElement;
        }

        if (modal.tagName === "DIALOG") {
            modal.setAttribute("open", "");
        } else {
            modal.setAttribute("role", "dialog");
        }
        modal.setAttribute("aria-modal", "true");

        container.classList.add("is-open");
        container.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");

        initializeModal(container);
        focusModal(modal);
    }

    function finishCloseModal(container) {
        const modal = qs(".ui-modal, dialog", container);
        if (modal && modal.tagName === "DIALOG") {
            modal.removeAttribute("open");
        }

        container.classList.remove("is-open");
        container.setAttribute("aria-hidden", "true");
        container.innerHTML = "";
        document.body.classList.remove("modal-open");

        if (
            modalReturnFocus &&
            modalReturnFocus.isConnected &&
            typeof modalReturnFocus.focus === "function"
        ) {
            modalReturnFocus.focus({ preventScroll: true });
        }
        modalReturnFocus = null;
    }

    function closeModal() {
        const container = getModalContainer();
        if (
            !container ||
            modalCloseTimer ||
            !container.classList.contains("is-open")
        ) {
            return;
        }

        const reduceMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        container.classList.add("is-closing");

        modalCloseTimer = setTimeout(
            function () {
                modalCloseTimer = null;
                container.classList.remove("is-closing");
                finishCloseModal(container);
            },
            reduceMotion ? 0 : 220
        );
    }

    // Ortak ve modüle özel kapatma olaylarını dinle
    [
        "closeModal",
        "closeTeamModal",
        "closeScheduleModal",
        "closeAthleteModal",
        "closeAthletePaymentModal",
        "closeAthleteStatusModal",
        "closeRegularExpenseModal",
        "closeExpenseModal",
        "closeEquipmentStockModal"
    ].forEach(function (eventName) {
        document.body.addEventListener(eventName, closeModal);
    });

    window.openModal = openModal;
    window.closeModal = closeModal;

    /* =========================================================
       TOAST NOTIFICATIONS
       ========================================================= */

    const MAX_VISIBLE_TOASTS = 3;
    const TOAST_COLORS = {
        success: "var(--ui-success-text)",
        error: "#ef4444",
        warning: "#f59e0b"
    };

    function decodeToastHeader(value) {
        try {
            return decodeURIComponent(value);
        } catch (error) {
            console.warn("Unable to decode the toast response header.", error);
            return value;
        }
    }

    function dismissToast(toast) {
        if (!toast || toast.classList.contains("is-hiding")) return;
        toast.classList.add("is-hiding");
        window.setTimeout(function () {
            toast.remove();
        }, 180);
    }

    function showToast(message, type = "success") {
        const container = qs("#toast-container");
        if (!container || !message) return;

        // Maksimum görünür toast sınırını koru
        const activeToasts = qsa(".app-toast:not(.is-hiding)", container);
        if (activeToasts.length >= MAX_VISIBLE_TOASTS) {
            dismissToast(activeToasts[0]);
        }

        const toast = document.createElement("div");
        const indicator = document.createElement("span");
        const text = document.createElement("span");

        toast.className = "app-toast";
        toast.dataset.toastType = type;
        toast.setAttribute("role", type === "error" ? "alert" : "status");

        indicator.className = "app-toast-indicator";
        indicator.setAttribute("aria-hidden", "true");
        if (TOAST_COLORS[type]) {
            indicator.style.backgroundColor = TOAST_COLORS[type];
        }

        text.textContent = String(message);
        toast.append(indicator, text);
        container.appendChild(toast);

        window.setTimeout(function () {
            dismissToast(toast);
        }, 2800);
    }

    window.showToast = showToast;

    qsa("[data-server-toast]").forEach(function (messageEl) {
        const text = messageEl.textContent.trim();
        const type = messageEl.dataset.serverToast || "success";
        if (text) {
            showToast(text, type);
        }
        messageEl.remove();
    });

    /* =========================================================
       ATTENDANCE & MAKEUP HELPERS
       ========================================================= */

    function createAttendanceRow(athleteId, athleteName, isMakeup) {
        const row = document.createElement("div");
        row.className = "ui-list-item bg-ui-bg-success";
        row.dataset.extraAthleteId = athleteId;

        const name = document.createElement("span");
        name.className = "ui-list-title";
        name.textContent = athleteName;
        row.appendChild(name);

        if (isMakeup) {
            const makeupLabel = document.createElement("span");
            makeupLabel.className = "text-primary-custom";
            makeupLabel.textContent = "Telafi";
            row.appendChild(makeupLabel);
        }

        const attendedLabel = document.createElement("span");
        attendedLabel.className = "text-success-custom";
        row.appendChild(attendedLabel);

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "ui-btn ui-btn-sm ui-btn-ghost";
        removeButton.dataset.athleteId = athleteId;
        removeButton.textContent = "Sil";
        row.appendChild(removeButton);

        return row;
    }

    function handleAttendanceClick(event) {
        const addButton = event.target.closest(".add-makeup-athlete");
        if (addButton) {
            event.preventDefault();

            const form = addButton.closest("form");
            const list = form && qs("#attendance-athlete-list", form);
            const athleteId = addButton.dataset.athleteId;
            const athleteName = addButton.dataset.athleteName;

            if (!form || !list || !athleteId || !athleteName) {
                return true;
            }

            const resultItem = addButton.closest(".ui-list-item");
            const alreadyAdded = qsa("[data-extra-athlete-id]", list).some(
                function (row) {
                    return row.dataset.extraAthleteId === athleteId;
                }
            );

            if (alreadyAdded) {
                if (resultItem) resultItem.remove();
                return true;
            }

            const isMakeup = Boolean(
                resultItem && qs('input[type="radio"]', resultItem)?.checked
            );

            const hiddenInput = document.createElement("input");
            hiddenInput.type = "hidden";
            hiddenInput.name = isMakeup ? "makeup_athlete" : "extra_athlete";
            hiddenInput.value = athleteId;
            form.appendChild(hiddenInput);

            const row = createAttendanceRow(athleteId, athleteName, isMakeup);
            list.prepend(row);
            if (resultItem) resultItem.remove();
            return true;
        }

        const removeButton = event.target.closest(
            "#attendance-athlete-list [data-athlete-id]"
        );
        if (removeButton) {
            const row = removeButton.closest("[data-extra-athlete-id]");
            const form = removeButton.closest("form");
            if (!row || !form) return true;

            const athleteId = row.dataset.extraAthleteId;
            qsa('input[type="hidden"]', form).forEach(function (input) {
                if (
                    input.value === athleteId &&
                    (input.name === "makeup_athlete" ||
                        input.name === "extra_athlete")
                ) {
                    input.remove();
                }
            });
            row.remove();
            return true;
        }

        return false;
    }

    /* =========================================================
       DASHBOARD TABS
       ========================================================= */

    function handleTabClick(event) {
        const button = event.target.closest(
            "[data-dashboard-tab], [data-tab-button]"
        );
        if (!button) return false;

        const group = button.closest("[data-tab-group]");
        if (!group) return false;

        const tabName =
            button.dataset.dashboardTab || button.dataset.tabButton;
        if (!tabName) return false;

        const buttons = qsa(
            "[data-dashboard-tab], [data-tab-button]",
            group
        );
        const panels = qsa("[data-tab-panel]", group);
        const selectedPanel = panels.find(function (panel) {
            return panel.dataset.tabPanel === tabName;
        });
        if (!selectedPanel) return false;

        event.preventDefault();

        buttons.forEach(function (tabButton) {
            const selected =
                tabButton.dataset.dashboardTab === tabName ||
                tabButton.dataset.tabButton === tabName;
            const activeClass = tabButton.hasAttribute("data-dashboard-tab")
                ? "active"
                : "is-active";

            tabButton.classList.toggle(activeClass, selected);
            tabButton.setAttribute("aria-selected", String(selected));
        });

        panels.forEach(function (panel) {
            const selected = panel === selectedPanel;
            panel.hidden = !selected;
            panel.classList.toggle("hidden", !selected);
        });

        return true;
    }

    /* =========================================================
       UNIFIED CLICK & CHANGE LISTENERS
       ========================================================= */

    document.addEventListener("click", function (event) {
        // 1. Modal kapatma butonu
        const closeButton = event.target.closest("[data-modal-close]");
        if (closeButton) {
            event.preventDefault();
            closeModal();
            return;
        }

        // 2. Modal container dış alanı (overlay)
        const container = event.target.closest("#modal-container");
        if (container && event.target === container) {
            closeModal();
            return;
        }

        // 3. Modal kendi backdrop alanı
        const modal = event.target.closest(".ui-modal");
        if (
            modal &&
            event.target === modal &&
            modal.dataset.modalBackdropClose !== "false"
        ) {
            closeModal();
            return;
        }

        // 4. Genel Geri Butonu (Smart Back Navigation)
        const backButton = event.target.closest("[data-app-back]");
        if (backButton) {
            event.preventDefault();
            const fallbackUrl = backButton.dataset.fallbackUrl || "/dashboard/";
            const hasSameOriginReferrer =
                document.referrer &&
                document.referrer.indexOf(window.location.origin) === 0;

            if (window.history.length > 1 && hasSameOriginReferrer) {
                window.history.back();
            } else {
                window.location.href = fallbackUrl;
            }
            return;
        }

        // 5. Yoklama sporcu ekleme / çıkarma
        if (handleAttendanceClick(event)) {
            return;
        }

        // 6. Sekme (Tab) geçişleri
        handleTabClick(event);
    });

    document.addEventListener("change", function (event) {
        const target = event.target;

        // 1. Kategori seçici (Category Picker)
        if (
            target instanceof HTMLInputElement &&
            target.name === "category" &&
            target.type === "radio"
        ) {
            const picker = target.closest("[data-category-picker]");
            if (picker) {
                const selectedGroup = target.closest("[data-category-children]");
                const selectedParent = selectedGroup
                    ? selectedGroup.dataset.categoryChildren
                    : target.value;

                qsa("[data-category-children]", picker).forEach(function (group) {
                    const isVisible =
                        group.dataset.categoryChildren === selectedParent;
                    group.hidden = !isVisible;
                    group.classList.toggle("hidden", !isVisible);
                });
                return;
            }
        }

        // 2. Yoklama durumu (katıldı / katılmadı) satır rengi
        const attendanceInput = target.closest(
            '#attendance-athlete-list input[type="radio"][name^="attendance_"]'
        );
        if (attendanceInput) {
            const athleteRow = attendanceInput.closest(".ui-list-item");
            if (athleteRow) {
                const attended = attendanceInput.value === "attended";
                athleteRow.classList.toggle("bg-ui-bg-success", attended);
                athleteRow.classList.toggle("bg-ui-bg-error", !attended);
            }
        }
    });

    /* =========================================================
       KEYBOARD (FOCUS TRAP & ESCAPE)
       ========================================================= */

    document.addEventListener("keydown", function (event) {
        const modal = getActiveModal();
        if (!modal) return;

        if (event.key === "Tab") {
            const focusable = qsa(
                'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
                modal
            ).filter(function (element) {
                return (
                    !element.hasAttribute("hidden") &&
                    element.getAttribute("aria-hidden") !== "true" &&
                    element.getClientRects().length > 0
                );
            });

            if (!focusable.length) {
                event.preventDefault();
                modal.focus();
                return;
            }

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (!modal.contains(document.activeElement)) {
                event.preventDefault();
                (event.shiftKey ? last : first).focus();
            } else if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
            return;
        }

        if (event.key === "Escape") {
            event.preventDefault();
            closeModal();
        }
    });

    /* =========================================================
       HTMX INTEGRATION (MODAL, TOAST & LOADING)
       ========================================================= */

    const activeHtmxRequests = new Set();

    function updateLoadingIndicator() {
        const loading = qs("#global-loading");
        if (!loading) return;

        const isLoading = activeHtmxRequests.size > 0;
        loading.classList.toggle("is-visible", isLoading);
        loading.setAttribute("aria-hidden", String(!isLoading));
    }

    function settleHtmxRequest(event) {
        const xhr = event.detail && event.detail.xhr;
        if (!xhr || !activeHtmxRequests.delete(xhr)) return;
        updateLoadingIndicator();
    }

    document.body.addEventListener("htmx:beforeSend", function (event) {
        const xhr = event.detail && event.detail.xhr;
        if (!xhr) return;

        activeHtmxRequests.add(xhr);
        updateLoadingIndicator();
    });

    /*
     * Modal formu hatalı gönderildiğinde sunucu yeniden <dialog> dönerse,
     * hedef ne olursa olsun yanıtı ortak #modal-container alanına yönlendir.
     */
    document.body.addEventListener("htmx:beforeSwap", function (event) {
        const detail = event.detail;
        const container = getModalContainer();

        if (
            !container ||
            !detail.target ||
            detail.target.id === "modal-container" ||
            typeof detail.serverResponse !== "string"
        ) {
            return;
        }

        if (!/^\s*(<!--[\s\S]*?-->\s*)*<dialog[\s>]/i.test(detail.serverResponse)) {
            return;
        }

        detail.target = container;
        detail.swapOverride = "innerHTML";
        detail.shouldSwap = true;
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail.target;
        if (!target) return;

        if (target.id === "modal-container") {
            const modal = qs(".ui-modal, dialog", target);
            if (modal) {
                openModal();
            }
        }
    });

    document.body.addEventListener("htmx:afterRequest", function (event) {
        settleHtmxRequest(event);

        const xhr = event.detail.xhr;
        const requestConfig = event.detail.requestConfig;
        if (!xhr || !requestConfig) return;

        const trigger = requestConfig.elt;
        if (
            trigger &&
            trigger.matches("[data-close-modal-on-success]") &&
            xhr.status >= 200 &&
            xhr.status < 300
        ) {
            closeModal();
        }

        const toast = xhr.getResponseHeader("X-App-Toast");
        if (toast) {
            const toastType =
                xhr.status >= 400 ? "error" : "success";
            showToast(decodeToastHeader(toast), toastType);
            return;
        }

        const method = String(requestConfig.verb || "").toLowerCase();
        const modal =
            trigger && trigger.closest(".ui-modal, dialog");
        const htmxTriggers = xhr.getResponseHeader("HX-Trigger") || "";

        if (
            modal &&
            ["post", "put", "patch"].includes(method) &&
            xhr.status >= 200 &&
            xhr.status < 300 &&
            /close[A-Z][A-Za-z]*/.test(htmxTriggers)
        ) {
            showToast("Değişiklikler kaydedildi.", "success");
        }
    });

    document.body.addEventListener("htmx:responseError", function (event) {
        settleHtmxRequest(event);
        const xhr = event.detail && event.detail.xhr;
        if (xhr && xhr.getResponseHeader("X-App-Toast")) {
            return;
        }
        showToast("İşlem sırasında bir hata oluştu.", "error");
    });

    document.body.addEventListener("htmx:sendError", function (event) {
        settleHtmxRequest(event);
        showToast("Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin.", "error");
    });

    ["htmx:sendAbort", "htmx:timeout"].forEach(function (eventName) {
        document.body.addEventListener(eventName, settleHtmxRequest);
    });

    /* =========================================================
       ACTIVE BOTTOM NAVIGATION
       ========================================================= */

    function updateActiveNav() {
        const currentPath = window.location.pathname;
        const navItems = qsa(".app-bottom-nav-item");
        let bestMatch = null;
        let bestMatchLength = -1;

        navItems.forEach(function (item) {
            item.classList.remove("active");
            const href = item.getAttribute("href");
            if (!href || href === "#") return;

            if (href === currentPath) {
                bestMatch = item;
                bestMatchLength = href.length + 1000;
            } else if (
                href !== "/" &&
                currentPath.startsWith(href) &&
                href.length > bestMatchLength
            ) {
                bestMatch = item;
                bestMatchLength = href.length;
            }
        });

        if (bestMatch) {
            bestMatch.classList.add("active");
        }

        const backButton = qs("[data-app-back]");
        if (backButton) {
            const isRootPage =
                currentPath === "/" ||
                currentPath === "/dashboard/" ||
                currentPath === "/login/";
            backButton.hidden = isRootPage;
        }
    }

    updateActiveNav();
    document.body.addEventListener("htmx:afterSettle", updateActiveNav);
    window.addEventListener("popstate", updateActiveNav);

    /* =========================================================
       SMART SWIPE NAVIGATION (TABS, BOTTOM NAV & BACK/FORWARD)
       ========================================================= */

    (function initSwipeNavigation() {
        const SWIPE_THRESHOLD = 72;
        const SWIPE_LOCK_MIN = 18;
        const MAX_SWIPE_DURATION = 650;

        let startX = 0;
        let startY = 0;
        let startTime = 0;
        let tracking = false;
        let axisLocked = null; // "x" | "y" | null
        let startTarget = null;
        let indicatorEl = null;

        function getSwipeIndicator() {
            if (indicatorEl && indicatorEl.isConnected) {
                return indicatorEl;
            }
            indicatorEl = document.createElement("div");
            indicatorEl.className = "app-swipe-indicator";
            indicatorEl.setAttribute("aria-hidden", "true");
            document.body.appendChild(indicatorEl);
            return indicatorEl;
        }

        function hideSwipeIndicator() {
            if (!indicatorEl) return;
            indicatorEl.classList.remove("is-visible", "is-ready", "is-left", "is-right");
            indicatorEl.style.transform = "";
        }

        function shouldIgnoreSwipe(target) {
            if (!target || !(target instanceof Element)) return true;
            if (document.body.classList.contains("modal-open")) return true;
            if (qs("#pwa-install:not([hidden])")) return true;

            if (
                target.closest(
                    'input, textarea, select, [contenteditable="true"], [data-no-swipe], .app-bottom-nav, .app-topbar'
                )
            ) {
                return true;
            }

            let el = target;
            while (el && el !== document.body && el !== document.documentElement) {
                if (el.scrollWidth > el.clientWidth + 6) {
                    const style = window.getComputedStyle(el);
                    if (
                        style.overflowX === "auto" ||
                        style.overflowX === "scroll"
                    ) {
                        return true;
                    }
                }
                el = el.parentElement;
            }
            return false;
        }

        function resolveSwipeAction(direction, target) {
            // direction: "prev" (sağa çekme / geri) veya "next" (sola çekme / ileri)

            // 1. Öncelik: Sayfa içi sekme grubu ([data-tab-group])
            const tabGroup =
                (target && target.closest("[data-tab-group]")) ||
                qs("[data-tab-group]");
            if (tabGroup) {
                const tabs = qsa(
                    "[data-dashboard-tab], [data-tab-button]",
                    tabGroup
                ).filter(function (btn) {
                    return btn.getClientRects().length > 0;
                });

                if (tabs.length > 1) {
                    const activeIndex = tabs.findIndex(function (btn) {
                        return (
                            btn.classList.contains("active") ||
                            btn.classList.contains("is-active") ||
                            btn.getAttribute("aria-selected") === "true"
                        );
                    });

                    if (activeIndex !== -1) {
                        const nextIndex =
                            direction === "next"
                                ? activeIndex + 1
                                : activeIndex - 1;
                        if (nextIndex >= 0 && nextIndex < tabs.length) {
                            const nextTab = tabs[nextIndex];
                            return {
                                type: "tab",
                                element: nextTab,
                                label: nextTab.textContent.replace(/\s+/g, " ").trim()
                            };
                        }
                    }
                }
            }

            // 2. Öncelik: Ana navigasyon sekmeleri (Alt menüdeki kök sayfalardaysak)
            const currentPath = window.location.pathname;
            const navLinks = qsa("a.app-bottom-nav-item[href]").filter(
                function (link) {
                    const href = link.getAttribute("href");
                    return Boolean(href && href !== "#");
                }
            );

            const exactNavIndex = navLinks.findIndex(function (link) {
                const href = link.getAttribute("href");
                return (
                    href === currentPath ||
                    (currentPath === "/" && href === "/dashboard/")
                );
            });

            if (exactNavIndex !== -1) {
                const targetIndex =
                    direction === "next"
                        ? exactNavIndex + 1
                        : exactNavIndex - 1;
                if (targetIndex >= 0 && targetIndex < navLinks.length) {
                    const targetLink = navLinks[targetIndex];
                    const labelEl = qs(".app-bottom-nav-item-label", targetLink);
                    return {
                        type: "nav",
                        url: targetLink.getAttribute("href"),
                        label: labelEl
                            ? labelEl.textContent.trim()
                            : "Sekme"
                    };
                }
                return null;
            }

            // 3. Öncelik: Alt sayfalarda İleri / Geri gezinme
            const isRootPage =
                currentPath === "/" ||
                currentPath === "/dashboard/" ||
                currentPath === "/login/";

            if (!isRootPage) {
                if (direction === "prev") {
                    return {
                        type: "back",
                        label: "Geri"
                    };
                }
                if (direction === "next" && window.history.length > 1) {
                    return {
                        type: "forward",
                        label: "İleri"
                    };
                }
            }

            return null;
        }

        function executeSwipeAction(action) {
            if (!action) return;

            if (action.type === "tab" && action.element) {
                action.element.click();
                return;
            }

            if (action.type === "nav" && action.url) {
                window.location.href = action.url;
                return;
            }

            if (action.type === "back") {
                const backButton = qs("[data-app-back]");
                const fallbackUrl =
                    (backButton && backButton.dataset.fallbackUrl) ||
                    "/dashboard/";
                const hasSameOriginReferrer =
                    document.referrer &&
                    document.referrer.indexOf(window.location.origin) === 0;

                if (window.history.length > 1 && hasSameOriginReferrer) {
                    window.history.back();
                } else {
                    window.location.href = fallbackUrl;
                }
                return;
            }

            if (action.type === "forward") {
                window.history.forward();
            }
        }

        document.addEventListener(
            "touchstart",
            function (event) {
                if (event.touches.length !== 1) {
                    tracking = false;
                    hideSwipeIndicator();
                    return;
                }

                const target = event.target;
                if (shouldIgnoreSwipe(target)) {
                    tracking = false;
                    return;
                }

                const touch = event.touches[0];
                startX = touch.clientX;
                startY = touch.clientY;
                startTime = Date.now();
                tracking = true;
                axisLocked = null;
                startTarget = target;
            },
            { passive: true }
        );

        document.addEventListener(
            "touchmove",
            function (event) {
                if (!tracking || event.touches.length !== 1) return;

                const touch = event.touches[0];
                const dx = touch.clientX - startX;
                const dy = touch.clientY - startY;
                const absX = Math.abs(dx);
                const absY = Math.abs(dy);

                if (!axisLocked) {
                    if (absX < SWIPE_LOCK_MIN && absY < SWIPE_LOCK_MIN) {
                        return;
                    }
                    axisLocked = absX > absY * 1.35 ? "x" : "y";
                }

                if (axisLocked !== "x") {
                    tracking = false;
                    hideSwipeIndicator();
                    return;
                }

                const direction = dx > 0 ? "prev" : "next";
                const action = resolveSwipeAction(direction, startTarget);
                if (!action) {
                    hideSwipeIndicator();
                    return;
                }

                const indicator = getSwipeIndicator();
                const isReady = absX >= SWIPE_THRESHOLD;
                const progress = Math.min(1, absX / SWIPE_THRESHOLD);
                const shift = (dx > 0 ? 1 : -1) * Math.min(24, Math.round(progress * 20));

                indicator.textContent =
                    dx > 0
                        ? "‹ " + action.label
                        : action.label + " ›";
                indicator.classList.toggle("is-left", dx > 0);
                indicator.classList.toggle("is-right", dx < 0);
                indicator.classList.add("is-visible");
                indicator.classList.toggle("is-ready", isReady);
                indicator.style.transform =
                    "translate3d(" + shift + "px, -50%, 0) scale(" + (0.9 + progress * 0.1) + ")";
            },
            { passive: true }
        );

        document.addEventListener(
            "touchend",
            function (event) {
                if (!tracking) return;
                tracking = false;

                const elapsed = Date.now() - startTime;
                const touch =
                    event.changedTouches && event.changedTouches[0];
                hideSwipeIndicator();

                if (
                    axisLocked !== "x" ||
                    !touch ||
                    elapsed > MAX_SWIPE_DURATION
                ) {
                    return;
                }

                const dx = touch.clientX - startX;
                const dy = touch.clientY - startY;

                if (
                    Math.abs(dx) < SWIPE_THRESHOLD ||
                    Math.abs(dx) < Math.abs(dy) * 1.35
                ) {
                    return;
                }

                const direction = dx > 0 ? "prev" : "next";
                const action = resolveSwipeAction(direction, startTarget);
                executeSwipeAction(action);
            },
            { passive: true }
        );

        document.addEventListener(
            "touchcancel",
            function () {
                tracking = false;
                axisLocked = null;
                hideSwipeIndicator();
            },
            { passive: true }
        );
    })();

    /* =========================================================
       MOBILE KEYBOARD & VISUAL VIEWPORT
       ========================================================= */

    (function initVisualViewport() {
        const vv = window.visualViewport;
        if (!vv) return;

        const root = document.documentElement;
        let lastInset = 0;
        let rafId = null;

        function updateViewport() {
            rafId = null;
            const inset = Math.max(
                0,
                Math.round(window.innerHeight - vv.height - vv.offsetTop)
            );

            if (inset === lastInset) return;

            const keyboardJustOpened = inset > lastInset && inset > 80;
            lastInset = inset;
            root.style.setProperty("--keyboard-inset", inset + "px");

            if (keyboardJustOpened) {
                const activeEl = document.activeElement;
                if (
                    activeEl &&
                    typeof activeEl.closest === "function" &&
                    activeEl.closest(".app-overlay")
                ) {
                    activeEl.scrollIntoView({
                        block: "center",
                        behavior: "smooth"
                    });
                }
            }
        }

        function scheduleUpdate() {
            if (rafId !== null) return;
            rafId = window.requestAnimationFrame(updateViewport);
        }

        vv.addEventListener("resize", scheduleUpdate);
        vv.addEventListener("scroll", scheduleUpdate);
    })();
})();
