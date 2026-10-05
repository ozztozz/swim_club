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
        }

        container.classList.add("is-open");

        container.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "modal-open"
        );

        initializeModal(container);
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


            /*
             * HTMX ile başka bir içerik geldiyse
             * dashboard tablarını tekrar initialize et.
             */
            initDashboardTabs(target);
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

        initializePrivateLesson(modal);
    }
/* =========================================================
   MONEY INPUT
   ========================================================= */

function formatMoneyInput(input) {
    if (!input) {
        return;
    }

    let value = input.value || "";

    // Sadece rakamları bırak.
    value = value.replace(/\D/g, "");

    if (!value) {
        input.value = "";
        return;
    }

    // Binlik ayırıcı: Türkçe format
    input.value = Number(value).toLocaleString("tr-TR");
}

function initializeMoneyInputs(root = document) {
    qsa(
        '[data-money-input="true"]',
        root
    ).forEach(function (input) {

        if (
            input.dataset.moneyInputInitialized === "true"
        ) {
            return;
        }

        input.dataset.moneyInputInitialized = "true";

        formatMoneyInput(input);
    });
}

document.addEventListener(
    "input",
    function (event) {

        const input =
            event.target.closest(
                '[data-money-input="true"]'
            );

        if (!input) {
            return;
        }

        formatMoneyInput(input);
    }
);

document.addEventListener(
    "focus",
    function (event) {

        const input =
            event.target.closest(
                '[data-money-input="true"]'
            );

        if (!input) {
            return;
        }

        // İmleci sona al.
        requestAnimationFrame(function () {
            input.setSelectionRange(
                input.value.length,
                input.value.length
            );
        });
    },
    true
);
/* =========================================================
   DJANGO İÇİN GÖNDERİM ÖNCESİ PARA TEMİZLEME
   ========================================================= */

// Standart form gönderimlerinde (submit)
document.addEventListener(
    "submit",
    function (event) {
        const form = event.target;
        const moneyInputs = form.querySelectorAll('[data-money-input="true"]');

        moneyInputs.forEach(function (input) {
            let val = input.value;
            if (val) {
                // "1.250,50" -> "1250.50" (Django DecimalField formatı)
                input.value = val.replace(/\./g, "").replace(",", ".");
            }
        });
    },
    true
);


// HTMX isteklerinde (hx-post, hx-get vb.)
document.body.addEventListener(
    "htmx:configRequest",
    function (event) {
        const parameters = event.detail.parameters;
        if (!parameters) {
            return;
        }

        const moneyInputs = document.querySelectorAll('[data-money-input="true"]');
        moneyInputs.forEach(function (input) {
            const name = input.name;
            if (name && parameters[name] !== undefined) {
                let val = String(parameters[name]);
                // Noktaları sil, virgülü noktaya çevir
                parameters[name] = val.replace(/\./g, "").replace(",", ".");
            }
        });
    }
);
initializeMoneyInputs();

    /* =========================================================
       PRIVATE LESSON
       ========================================================= */

    function getPrivateLessonTotal(
        modal
    ) {

        return qs(
            "[data-private-lesson-total]",
            modal
        );
    }


    function parseMoneyValue(value) {

        if (
            value === null ||
            value === undefined
        ) {
            return 0;
        }

        const raw =
            String(value)
                .trim()
                .replace(/\s/g, "");

        if (!raw) {
            return 0;
        }


        /*
         * 1.250,50
         */
        if (
            raw.includes(",") &&
            raw.includes(".")
        ) {

            return Number(
                raw
                    .replace(/\./g, "")
                    .replace(",", ".")
            );
        }


        /*
         * 1250,50
         */
        if (raw.includes(",")) {

            return Number(
                raw.replace(",", ".")
            );
        }


        /*
         * 1250.50
         *
         * Burada noktayı binlik
         * ayırıcı olarak silmiyoruz.
         */
        return Number(raw);
    }


    function updatePrivateLessonTotal(
        input
    ) {

        const modal =
            input.closest(
                ".ui-modal, dialog"
            );

        if (!modal) {
            return;
        }


        const total =
            getPrivateLessonTotal(
                modal
            );

        if (!total) {
            return;
        }


        const count =
            Math.max(
                1,
                Number(input.value) || 1
            );


        const unit =
            parseMoneyValue(
                input.dataset.privateLessonUnit
            );


        const amount =
            count * unit;


        total.textContent =
            `${amount.toLocaleString(
                "tr-TR",
                {
                    maximumFractionDigits: 2
                }
            )} TL`;
    }


    function initializePrivateLesson(
        modal
    ) {

        const input =
            qs(
                "[data-private-lesson-count]",
                modal
            );

        if (!input) {
            return;
        }

        updatePrivateLessonTotal(input);
    }


    document.addEventListener(
        "input",
        function (event) {

            const input =
                event.target.closest(
                    "[data-private-lesson-count]"
                );

            if (!input) {
                return;
            }

            updatePrivateLessonTotal(input);
        }
    );


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
                showToast(decodeURIComponent(toast));
            }
        }
    );


    /* =========================================================
       TOAST
       ========================================================= */

function showToast(message) {
    const container = qs("#toast-container");

    if (!container) {
        return;
    }

    const toast = document.createElement("div");

    toast.className = "app-toast";

    toast.innerHTML = `
        <span class="app-toast-indicator"></span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    window.setTimeout(function () {
        toast.classList.add("is-hiding");

        window.setTimeout(function () {
            toast.remove();
        }, 180);

    }, 2800);
}

    window.showToast = showToast;


    /* =========================================================
       HTMX LOADING
       ========================================================= */

    document.body.addEventListener(
        "htmx:beforeRequest",
        function () {

            const loading =
                qs("#global-loading");

            if (!loading) {
                return;
            }

            loading.classList.add(
                "is-visible"
            );
        }
    );


    document.body.addEventListener(
        "htmx:afterRequest",
        function () {

            const loading =
                qs("#global-loading");

            if (!loading) {
                return;
            }

            loading.classList.remove(
                "is-visible"
            );
        }
    );


    /* =========================================================
       DASHBOARD TABS
       ========================================================= */

    function switchDashboardTab(
        tabName
    ) {

        const collectionsTab =
            qs("#collections-tab");

        const expensesTab =
            qs("#expenses-tab");


        const collectionsButton =
            qs("#collections-tab-button");

        const expensesButton =
            qs("#expenses-tab-button");


        /*
         * Dashboard sayfasında değilsek
         * hiçbir şey yapma.
         */
        if (
            !collectionsTab ||
            !expensesTab ||
            !collectionsButton ||
            !expensesButton
        ) {
            return;
        }


        const showExpenses =
            tabName === "expenses";


        /*
         * Paneller
         */
        collectionsTab.classList.toggle(
            "hidden",
            showExpenses
        );

        expensesTab.classList.toggle(
            "hidden",
            !showExpenses
        );


        /*
         * Butonlar
         */
        collectionsButton.classList.toggle(
            "active",
            !showExpenses
        );

        expensesButton.classList.toggle(
            "active",
            showExpenses
        );


        /*
         * ARIA
         */
        collectionsButton.setAttribute(
            "aria-selected",
            showExpenses
                ? "false"
                : "true"
        );

        expensesButton.setAttribute(
            "aria-selected",
            showExpenses
                ? "true"
                : "false"
        );
    }


    function initDashboardTabs(
        root = document
    ) {

        const buttons =
            qsa(
                "[data-dashboard-tab]",
                root
            );

        if (!buttons.length) {
            return;
        }


        buttons.forEach(
            function (button) {

                /*
                 * Aynı butona ikinci kez
                 * listener bağlama.
                 */
                if (
                    button.dataset
                        .dashboardTabBound === "true"
                ) {
                    return;
                }


                button.dataset
                    .dashboardTabBound = "true";


                button.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();


                        const tabName =
                            button.dataset
                                .dashboardTab;


                        if (!tabName) {
                            return;
                        }


                        switchDashboardTab(
                            tabName
                        );
                    }
                );
            }
        );
    }


    /*
     * İlk sayfa yüklemesi
     */
    initDashboardTabs();


    /* =========================================================
       ESC → MODAL CLOSE
       ========================================================= */

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key !==
                "Escape"
            ) {
                return;
            }


            const modal =
                getActiveModal();


            if (!modal) {
                return;
            }


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

document.addEventListener("DOMContentLoaded", () => {

    const section = document.querySelector(
        ".dashboard-search-section"
    );

    const searchForm = document.querySelector(
        "#dashboard-athlete-search-form"
    );

    const searchInput = document.querySelector(
        "#dashboard-athlete-search"
    );

    const backdrop = document.querySelector(
        ".dashboard-search-backdrop"
    );


    if (
        !section ||
        !searchForm ||
        !searchInput ||
        !backdrop
    ) {
        return;
    }


    let isAnimating = false;

    let originalPosition = null;


    /* =====================================================
       OPEN SEARCH
    ====================================================== */

    function openSearch() {

        if (
            isAnimating ||
            section.classList.contains("search-focus")
        ) {
            return;
        }


        isAnimating = true;


        /* -------------------------------------------------
           1. Gerçek başlangıç koordinatını al
        -------------------------------------------------- */

        const rect =
            searchForm.getBoundingClientRect();


        originalPosition = {

            centerX:
                rect.left +
                rect.width / 2,

            centerY:
                rect.top +
                rect.height / 2,

            width:
                rect.width,

            height:
                rect.height
        };


        /* -------------------------------------------------
           2. Hedef boyut
        -------------------------------------------------- */

        const targetWidth =
            Math.min(
                window.innerWidth - 24,
                680
            );


        const targetHeight =
            rect.height;


        /* -------------------------------------------------
           3. Ekran merkezi
        -------------------------------------------------- */

        const targetCenterX =
            window.innerWidth / 2;


        const targetCenterY =
            window.innerHeight / 2;


        /* -------------------------------------------------
           4. Başlangıç → merkez farkı
        -------------------------------------------------- */

        const translateX =
            originalPosition.centerX -
            targetCenterX;


        const translateY =
            originalPosition.centerY -
            targetCenterY;


        /* -------------------------------------------------
           5. Başlangıç → hedef ölçek
        -------------------------------------------------- */

        const scaleX =
            originalPosition.width /
            targetWidth;


        const scaleY =
            originalPosition.height /
            targetHeight;


        /* -------------------------------------------------
           6. CSS değişkenleri
        -------------------------------------------------- */

        searchForm.style.setProperty(
            "--search-flip-width",
            `${targetWidth}px`
        );


        searchForm.style.setProperty(
            "--search-flip-height",
            `${targetHeight}px`
        );


        searchForm.style.setProperty(
            "--search-flip-left",
            `${targetCenterX - targetWidth / 2}px`
        );


        searchForm.style.setProperty(
            "--search-flip-top",
            `${targetCenterY - targetHeight / 2}px`
        );


        searchForm.style.setProperty(
            "--search-flip-x",
            `${translateX}px`
        );


        searchForm.style.setProperty(
            "--search-flip-y",
            `${translateY}px`
        );


        searchForm.style.setProperty(
            "--search-flip-scale-x",
            scaleX
        );


        searchForm.style.setProperty(
            "--search-flip-scale-y",
            scaleY
        );


        /* -------------------------------------------------
           7. Focus state
        -------------------------------------------------- */

        section.classList.add(
            "search-focus"
        );


        searchForm.classList.add(
            "search-flip"
        );


        /* -------------------------------------------------
           8. İlk frame
        -------------------------------------------------- */

        requestAnimationFrame(() => {

            requestAnimationFrame(() => {

                /*
                 * Şimdi merkez pozisyona hareket et.
                 */

                searchForm.classList.add(
                    "is-centered"
                );


                /*
                 * Input'a focus.
                 */

                searchInput.focus({
                    preventScroll: true
                });

            });

        });


        /* -------------------------------------------------
           9. Animasyon bitişi
        -------------------------------------------------- */

        searchForm.addEventListener(
            "transitionend",
            handleOpenTransition,
            {
                once: true
            }
        );
    }


    function handleOpenTransition(event) {

        if (
            event.propertyName !== "transform"
        ) {
            return;
        }


        isAnimating = false;
    }


    /* =====================================================
       CLOSE SEARCH
    ====================================================== */

    function closeSearch() {

        if (
            isAnimating ||
            !section.classList.contains(
                "search-focus"
            )
        ) {
            return;
        }


        if (!originalPosition) {
            return;
        }


        isAnimating = true;


        /* -------------------------------------------------
           Mevcut merkez konumu
        -------------------------------------------------- */

        const currentRect =
            searchForm.getBoundingClientRect();


        const currentCenterX =
            currentRect.left +
            currentRect.width / 2;


        const currentCenterY =
            currentRect.top +
            currentRect.height / 2;


        /* -------------------------------------------------
           Merkez → başlangıç farkı
        -------------------------------------------------- */

        const translateX =
            originalPosition.centerX -
            currentCenterX;


        const translateY =
            originalPosition.centerY -
            currentCenterY;


        /* -------------------------------------------------
           İlk olarak mevcut transform'u kaldır
           ve başlangıç yönünü hazırla
        -------------------------------------------------- */

        searchForm.style.setProperty(
            "--search-flip-x",
            `${translateX}px`
        );


        searchForm.style.setProperty(
            "--search-flip-y",
            `${translateY}px`
        );


        searchForm.style.setProperty(
            "--search-flip-scale-x",
            1
        );


        searchForm.style.setProperty(
            "--search-flip-scale-y",
            1
        );


        /*
         * Merkez state'ini kaldır.
         */

        searchForm.classList.remove(
            "is-centered"
        );


        /* -------------------------------------------------
           Animasyon tamamlandığında temizle
        -------------------------------------------------- */

        searchForm.addEventListener(
            "transitionend",
            handleCloseTransition,
            {
                once: true
            }
        );
    }


    function handleCloseTransition(event) {

        if (
            event.propertyName !== "transform"
        ) {
            return;
        }


        searchForm.classList.remove(
            "search-flip"
        );


        section.classList.remove(
            "search-focus"
        );


        /* -------------------------------------------------
           CSS değişkenlerini temizle
        -------------------------------------------------- */

        const variables = [

            "--search-flip-width",

            "--search-flip-height",

            "--search-flip-left",

            "--search-flip-top",

            "--search-flip-x",

            "--search-flip-y",

            "--search-flip-scale-x",

            "--search-flip-scale-y"
        ];


        variables.forEach(
            (variable) => {

                searchForm.style.removeProperty(
                    variable
                );

            }
        );


        searchInput.blur();


        originalPosition = null;

        isAnimating = false;
    }


    /* =====================================================
       INPUT FOCUS
    ====================================================== */

    searchInput.addEventListener(
        "focus",
        () => {

            if (
                !section.classList.contains(
                    "search-focus"
                )
            ) {

                openSearch();

            }

        }
    );


    /* =====================================================
       BACKDROP CLICK
    ====================================================== */

    backdrop.addEventListener(
        "click",
        closeSearch
    );


    /* =====================================================
       ESC
    ====================================================== */

    document.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Escape"
            ) {

                closeSearch();

            }

        }
    );

});
document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab-button]");
    if (!button) return;

    const tabs = button.closest("[data-tabs]");
    if (!tabs) return;

    const name = button.dataset.tabButton;
    tabs.querySelectorAll("[data-tab-button]").forEach((item) => {
        item.classList.toggle("is-active", item === button);
    });
    document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.tabPanel !== name;
    });
});