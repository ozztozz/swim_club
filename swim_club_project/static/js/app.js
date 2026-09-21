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


    function closeModal() {

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


    /* =========================================================
       HTMX → MODAL
       ========================================================= */

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
                trigger.closest(
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
                showToast(toast);
            }
        }
    );


    /* =========================================================
       TOAST
       ========================================================= */

    function showToast(message) {

        const container =
            qs("#toast-container");

        if (!container) {
            return;
        }


        const toast =
            document.createElement("div");

        toast.className =
            "app-toast";

        toast.textContent =
            message;


        container.appendChild(toast);


        window.setTimeout(
            function () {

                toast.style.opacity = "0";

                toast.style.transform =
                    "translateY(-6px)";


                window.setTimeout(
                    function () {
                        toast.remove();
                    },
                    180
                );

            },
            2800
        );
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