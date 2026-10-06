(function () {
    "use strict";

    function parseMoneyValue(value) {
        if (value === null || value === undefined) return 0;

        const raw = String(value).trim().replace(/\s/g, "");
        if (!raw) return 0;

        if (raw.includes(",") && raw.includes(".")) {
            return Number(raw.replace(/\./g, "").replace(",", "."));
        }
        if (raw.includes(",")) return Number(raw.replace(",", "."));
        return Number(raw);
    }

    function formatMoneyInput(input) {
        let value = (input.value || "").replace(/\D/g, "");
        input.value = value ? Number(value).toLocaleString("tr-TR") : "";
    }

    function initializeMoneyInputs(root) {
        const inputs = [];
        if (root.matches && root.matches('[data-money-input="true"]')) {
            inputs.push(root);
        }
        inputs.push(...root.querySelectorAll('[data-money-input="true"]'));

        inputs.forEach(function (input) {
            if (input.dataset.moneyInputInitialized === "true") return;
            input.dataset.moneyInputInitialized = "true";
            formatMoneyInput(input);
        });
    }

    function updatePrivateLessonTotal(input) {
        const modal = input.closest(".ui-modal, dialog");
        const total = modal && modal.querySelector("[data-private-lesson-total]");
        if (!total) return;

        const count = Math.max(1, Number(input.value) || 1);
        const amount = count * parseMoneyValue(input.dataset.privateLessonUnit);
        total.textContent =
            `${amount.toLocaleString("tr-TR", { maximumFractionDigits: 2 })} TL`;
    }

    function initializeModal(root) {
        const modal = root.matches && root.matches(".ui-modal, dialog")
            ? root
            : root.querySelector(".ui-modal, dialog");
        if (!modal) return;

        initializeMoneyInputs(modal);
        const privateLessonInput = modal.querySelector("[data-private-lesson-count]");
        if (privateLessonInput) updatePrivateLessonTotal(privateLessonInput);
    }

    function normalizeMoneyInputs(form, parameters) {
        if (!form || !parameters) return;

        form.querySelectorAll('[data-money-input="true"]').forEach(function (input) {
            const name = input.name;
            if (!name || parameters[name] === undefined) return;

            const values = Array.isArray(parameters[name])
                ? parameters[name]
                : [parameters[name]];
            parameters[name] = values.map(function (value) {
                return String(value).replace(/\./g, "").replace(",", ".");
            });
        });
    }

    document.addEventListener("input", function (event) {
        const input = event.target.closest('[data-money-input="true"]');
        if (input) {
            formatMoneyInput(input);
            return;
        }

        const privateLessonInput = event.target.closest("[data-private-lesson-count]");
        if (privateLessonInput) updatePrivateLessonTotal(privateLessonInput);
    });

    document.addEventListener("focus", function (event) {
        const input = event.target.closest('[data-money-input="true"]');
        if (!input) return;

        requestAnimationFrame(function () {
            input.setSelectionRange(input.value.length, input.value.length);
        });
    }, true);

    document.addEventListener("submit", function (event) {
        const form = event.target;
        form.querySelectorAll('[data-money-input="true"]').forEach(function (input) {
            if (input.value) {
                input.value = input.value.replace(/\./g, "").replace(",", ".");
            }
        });
    }, true);

    document.body.addEventListener("htmx:configRequest", function (event) {
        const requestElement = event.detail && event.detail.elt;
        const form = requestElement && requestElement.closest("form");
        normalizeMoneyInputs(form, event.detail && event.detail.parameters);
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        const target = event.detail && event.detail.target;
        if (target) initializeModal(target);
    });

    initializeMoneyInputs(document);
    window.AlphaFormControls = { initializeModal: initializeModal };
})();
