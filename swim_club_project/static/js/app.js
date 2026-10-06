(function () {

    "use strict";


    /* =========================================================
       HELPERS
       ========================================================= */

    function qs(selector, root = document) {
        return root.querySelector(selector);
    }


    function qsa(selector, root = document) {
        return Array.from(
            root.querySelectorAll(selector)
        );
    }


    /* =========================================================
       MODAL
       ========================================================= */

    function getModalContainer() {
        return qs("#modal-container");
    }


    function getActiveModal() {

        const container =
            getModalContainer();

        if (!container) {
            return null;
        }

        if (!container.classList.contains("is-open")) {
            return null;
        }

        return qs(
            ".ui-modal, dialog",
            container
        );
    }

    let modalReturnFocus = null;

    function focusModal(modal) {
        const focusTarget = qsa(
            '[autofocus], [data-modal-close]',
            modal
        ).find(function (element) {
            return element.getClientRects().length > 0;
        });

        if (focusTarget) {
            focusTarget.focus({ preventScroll: true });
            return;
        }

        modal.setAttribute("tabindex", "-1");
        modal.focus({ preventScroll: true });
    }

    function openModal() {

        const container =
            getModalContainer();

        if (!container) {
            return;
        }

        const modal =
            qs(
                ".ui-modal, dialog",
                container
            );

        if (!modal) {
            return;
        }

        const wasOpen = container.classList.contains("is-open");
        if (!wasOpen) {
            modalReturnFocus = document.activeElement;
        }

        if (modalCloseTimer) {
            clearTimeout(modalCloseTimer);
            modalCloseTimer = null;
            container.classList.remove("is-closing");
        }

        /*
         * Native dialog için open durumunu
         * manuel yönetiyoruz.
         */
        if (modal.tagName === "DIALOG") {
            modal.setAttribute("open", "");
        } else {
            modal.setAttribute("role", "dialog");
        }
        modal.setAttribute("aria-modal", "true");

        container.classList.add("is-open");

        container.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "modal-open"
        );

        initializeModal(container);
        focusModal(modal);
    }


    let modalCloseTimer = null;

    function closeModal() {

        const container =
            getModalContainer();

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
            () => {
                modalCloseTimer = null;
                container.classList.remove("is-closing");
                finishCloseModal(container);
            },
            reduceMotion ? 0 : 220
        );
    }


    function finishCloseModal(container) {

        const modal =
            qs(
                ".ui-modal, dialog",
                container
            );

        if (
            modal &&
            modal.tagName === "DIALOG"
        ) {
            modal.removeAttribute("open");
        }

        container.classList.remove(
            "is-open"
        );

        container.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.classList.remove(
            "modal-open"
        );

        if (
            modalReturnFocus &&
            modalReturnFocus.isConnected &&
            typeof modalReturnFocus.focus === "function"
        ) {
            modalReturnFocus.focus({ preventScroll: true });
        }
        modalReturnFocus = null;
    }

    document.body.addEventListener("closeModal", closeModal);

    // Eski modüle özel kapatma olayları da ortak modalı kapatır.
    [
        "closeTeamModal",
        "closeScheduleModal",
        "closeAthleteModal",
        "closeAthletePaymentModal",
        "closeAthleteStatusModal",
        "closeRegularExpenseModal",
        "closeExpenseModal",
        "closeEquipmentStockModal"
    ].forEach(function (name) {
        document.body.addEventListener(name, closeModal);
    });

    window.openModal = openModal;
    window.closeModal = closeModal;


    /* =========================================================
       MODAL EVENTS
       ========================================================= */

    document.addEventListener(
        "click",
        function (event) {

            /*
             * Modal kapatma butonu
             */
            const closeButton =
                event.target.closest(
                    "[data-modal-close]"
                );

            if (closeButton) {

                event.preventDefault();

                closeModal();

                return;
            }


            /*
             * Modal container dış alanı
             */
            const container =
                event.target.closest(
                    "#modal-container"
                );

            if (
                container &&
                event.target === container
            ) {

                closeModal();

                return;
            }


            /*
             * Modal kendi backdrop alanı
             */
            const modal =
                event.target.closest(
                    ".ui-modal"
                );

            if (
                modal &&
                event.target === modal &&
                modal.dataset.modalBackdropClose !== "false"
            ) {

                closeModal();
            }
        }
    );

    document.addEventListener(
        "click",
        function (event) {
            const addButton = event.target.closest(
                ".add-makeup-athlete"
            );

            if (addButton) {
                event.preventDefault();

                const form = addButton.closest("form");
                const list = form && qs("#attendance-athlete-list", form);
                const athleteId = addButton.dataset.athleteId;
                const athleteName = addButton.dataset.athleteName;

                if (!form || !list || !athleteId || !athleteName) {
                    return;
                }

                const alreadyAdded = qsa(
                    "[data-extra-athlete-id]",
                    list
                ).some(function (row) {
                    return row.dataset.extraAthleteId === athleteId;
                });

                if (alreadyAdded) {
                    addButton.closest(".ui-list-item").remove();
                    return;
                }

                const resultItem = addButton.closest(".ui-list-item");
                const isMakeup = Boolean(
                    resultItem && qs('input[type="radio"]', resultItem)?.checked
                );
                const hiddenInput = document.createElement("input");
                hiddenInput.type = "hidden";
                hiddenInput.name = isMakeup ? "makeup_athlete" : "extra_athlete";
                hiddenInput.value = athleteId;
                form.appendChild(hiddenInput);

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

                list.prepend(row);
                resultItem.remove();
                return;
            }

            const removeButton = event.target.closest(
                "#attendance-athlete-list [data-athlete-id]"
            );

            if (!removeButton) {
                return;
            }

            const row = removeButton.closest("[data-extra-athlete-id]");
            const form = removeButton.closest("form");

            if (!row || !form) {
                return;
            }

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
        }
    );

    document.addEventListener(
        "change",
        function (event) {
            const attendanceInput = event.target.closest(
                '#attendance-athlete-list input[type="radio"][name^="attendance_"]'
            );

            if (!attendanceInput) {
                return;
            }

            const athleteRow = attendanceInput.closest(".ui-list-item");

            if (!athleteRow) {
                return;
            }

            const attended = attendanceInput.value === "attended";
            athleteRow.classList.toggle("bg-ui-bg-success", attended);
            athleteRow.classList.toggle("bg-ui-bg-error", !attended);
        }
    );


    /* =========================================================
       HTMX → MODAL
       ========================================================= */

    /*
     * Modal formu hatalı gönderildiğinde sunucu yeniden modal döner.
     * Yanıt bir modalsa hedef ne olursa olsun ortak modal alanına yazılır.
     */
    document.body.addEventListener(
        "htmx:beforeSwap",
        function (event) {

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
        }
    );

    document.body.addEventListener(
        "htmx:afterSwap",
        function (event) {

            const target =
                event.detail.target;

            if (!target) {
                return;
            }


            /*
             * Modal container değiştirildiyse
             * modalı aç.
             */
            if (
                target.id ===
                "modal-container"
            ) {

                const modal =
                    qs(
                        ".ui-modal, dialog",
                        target
                    );

                if (!modal) {
                    return;
                }

                openModal();

                return;
            }


        }
    );


    /* =========================================================
       MODAL INITIALIZE
       ========================================================= */

    function initializeModal(
        root = document
    ) {

        const modal =
            qs(
                ".ui-modal, dialog",
                root
            );

        if (!modal) {
            return;
        }

        if (window.AlphaFormControls) {
            window.AlphaFormControls.initializeModal(modal);
        }
    }

    /* =========================================================
       HTMX REQUEST
       ========================================================= */

    document.body.addEventListener(
        "htmx:afterRequest",
        function (event) {

            const xhr =
                event.detail.xhr;

            const requestConfig =
                event.detail.requestConfig;

            if (
                !xhr ||
                !requestConfig
            ) {
                return;
            }


            /*
             * Başarılı modal formundan sonra
             * modalı kapat.
             */
            const trigger =
                requestConfig.elt;

            if (
                trigger &&
                trigger.matches(
                    "[data-close-modal-on-success]"
                ) &&
                xhr.status >= 200 &&
                xhr.status < 300
            ) {

                closeModal();
            }


            /*
             * Server tarafından gönderilen toast.
             */
            const toast =
                xhr.getResponseHeader(
                    "X-App-Toast"
                );

            if (toast) {
                showToast(decodeToastHeader(toast));
                return;
            }

            const method = String(requestConfig.verb || "").toLowerCase();
            const triggeringElement = requestConfig.elt;
            const modal = triggeringElement &&
                triggeringElement.closest(".ui-modal, dialog");
            const htmxTriggers = xhr.getResponseHeader("HX-Trigger") || "";

            if (
                modal &&
                ["post", "put", "patch"].includes(method) &&
                xhr.status >= 200 &&
                xhr.status < 300 &&
                /close[A-Z][A-Za-z]*/.test(htmxTriggers)
            ) {
                showToast("Değişiklikler kaydedildi.");
            }
        }
    );


    /* =========================================================
       TOAST
       ========================================================= */

function decodeToastHeader(value) {
    try {
        return decodeURIComponent(value);
    } catch (error) {
        console.warn("Unable to decode the toast response header.", error);
        return value;
    }
}

function showToast(message) {
    const container = qs("#toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const indicator = document.createElement("span");
    const text = document.createElement("span");

    toast.className = "app-toast";
    toast.setAttribute("role", "status");
    indicator.className = "app-toast-indicator";
    indicator.setAttribute("aria-hidden", "true");
    text.textContent = String(message);
    toast.append(indicator, text);
    container.appendChild(toast);

    window.setTimeout(function () {
        toast.classList.add("is-hiding");
        window.setTimeout(function () {
            toast.remove();
        }, 180);
    }, 2800);
}

    window.showToast = showToast;

    qsa("[data-server-toast]").forEach(function (message) {
        showToast(message.textContent.trim());
        message.remove();
    });


    /* =========================================================
       HTMX LOADING
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

    document.body.addEventListener(
        "htmx:beforeSend",
        function (event) {
            const xhr = event.detail && event.detail.xhr;
            if (!xhr) return;

            activeHtmxRequests.add(xhr);
            updateLoadingIndicator();
        }
    );

    document.body.addEventListener(
        "htmx:afterRequest",
        settleHtmxRequest
    );

    ["htmx:sendError", "htmx:sendAbort", "htmx:timeout"].forEach(
        function (eventName) {
            document.body.addEventListener(eventName, settleHtmxRequest);
        }
    );


    /* =========================================================
       DASHBOARD TABS
       ========================================================= */

    document.addEventListener("click", function (event) {
        const button = event.target.closest(
            "[data-dashboard-tab], [data-tab-button]"
        );
        if (!button) return;

        const group = button.closest("[data-tab-group]");
        if (!group) return;

        const tabName =
            button.dataset.dashboardTab ||
            button.dataset.tabButton;
        if (!tabName) return;

        const buttons = qsa(
            "[data-dashboard-tab], [data-tab-button]",
            group
        );
        const panels = qsa("[data-tab-panel]", group);
        const selectedPanel = panels.find(function (panel) {
            return panel.dataset.tabPanel === tabName;
        });
        if (!selectedPanel) return;

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
    });


    /* =========================================================
       ESC → MODAL CLOSE
       ========================================================= */

    document.addEventListener(
        "keydown",
        function (event) {
            const modal =
                getActiveModal();

            if (!modal) {
                return;
            }

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
                } else if (
                    !event.shiftKey &&
                    document.activeElement === last
                ) {
                    event.preventDefault();
                    first.focus();
                }
                return;
            }

            if (event.key !== "Escape") return;

            event.preventDefault();
            closeModal();
        }
    );


    /* =========================================================
       ACTIVE NAV
       ========================================================= */

    const currentPath =
        window.location.pathname;


    qsa(
        ".app-bottom-nav-item"
    ).forEach(
        function (item) {

            const href =
                item.getAttribute(
                    "href"
                );


            /*
             * Button olan "Daha Fazla"
             * gibi elemanları atla.
             */
            if (
                !href ||
                href === "#"
            ) {
                return;
            }


            if (
                href === currentPath
            ) {

                item.classList.add(
                    "active"
                );
            }
        }
    );


})();
