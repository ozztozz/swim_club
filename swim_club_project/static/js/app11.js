(function () {
    'use strict';

    function formatMoneyInput(input) {
        const raw = input.value.replace(/\s/g, '');
        if (!raw) return;

        const separator = Math.max(raw.lastIndexOf(','), raw.lastIndexOf('.'));
        const hasDecimal = separator >= 0 && raw.length - separator - 1 <= 2;
        const integerPart = (hasDecimal ? raw.slice(0, separator) : raw)
            .replace(/\D/g, '') || '0';
        const decimalPart = hasDecimal
            ? raw.slice(separator + 1).replace(/\D/g, '').slice(0, 2)
            : '';
        const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');

        input.value = hasDecimal
            ? `${formattedInteger},${decimalPart}`
            : formattedInteger;
    }

    function normalizeMoneyValue(value) {
        const raw = value.replace(/\s/g, '');
        if (!raw) return '';

        const separator = Math.max(raw.lastIndexOf(','), raw.lastIndexOf('.'));
        const hasDecimal = separator >= 0 && raw.length - separator - 1 <= 2;
        const integerPart = (hasDecimal ? raw.slice(0, separator) : raw)
            .replace(/\D/g, '') || '0';
        const decimalPart = hasDecimal
            ? raw.slice(separator + 1).replace(/\D/g, '').slice(0, 2).padEnd(2, '0')
            : '00';

        return `${integerPart}.${decimalPart}`;
    }

    function prepareMoneyInputs(root) {
        if (!root || !root.querySelectorAll) return;

        root.querySelectorAll('[data-money-input="true"]').forEach((input) => {
            if (input.dataset.moneyReady) return;
            input.dataset.moneyReady = 'true';
            formatMoneyInput(input);

            input.addEventListener('input', () => {
                const cursorAtEnd = input.selectionStart === input.value.length;
                formatMoneyInput(input);
                if (cursorAtEnd) {
                    input.setSelectionRange(input.value.length, input.value.length);
                }
            });
            input.addEventListener('blur', () => {
                if (input.value) formatMoneyInput(input);
            });
        });
    }

    function clearModal(modalId, containerId) {
        document.getElementById(modalId)?.remove();
        document.getElementById(containerId)?.replaceChildren();
    }

    window.showPaymentTab = function (tab) {
        const tabs = {
            monthly: document.getElementById('monthly-payments-tab'),
            other: document.getElementById('other-payments-tab'),
            equipment: document.getElementById('equipment-payments-tab'),
            training: document.getElementById('training-payments-tab'),
        };
        Object.entries(tabs).forEach(([key, element]) => {
            element?.classList.toggle('hidden', key !== tab);
        });
        document.querySelectorAll('[data-payment-tab]').forEach((button) => {
            const active = button.dataset.paymentTab === tab;
            button.classList.toggle('bg-primary', active);
            button.classList.toggle('text-primary-content', active);
            button.classList.toggle('shadow-sm', active);
            button.classList.toggle('text-base-content/55', !active);
        });
    };

    window.showDashboardTab = function (tab) {
        const showCollections = tab === 'collections';
        document.getElementById('collections-tab')?.classList.toggle('hidden', !showCollections);
        document.getElementById('expenses-tab')?.classList.toggle('hidden', showCollections);
        document.querySelectorAll('[data-dashboard-tab]').forEach((button) => {
            const active = button.dataset.dashboardTab === tab;
            button.classList.toggle('bg-base-100', active);
            button.classList.toggle('text-base-content', active);
            button.classList.toggle('shadow-sm', active);
            button.classList.toggle('text-base-content/45', !active);
        });
    };

    window.switchFeeTab = function (tab) {
        const teams = document.getElementById('fee-tab-teams');
        const athletes = document.getElementById('fee-tab-athletes');
        const isTeams = tab === 'teams';
        teams?.classList.toggle('hidden', !isTeams);
        athletes?.classList.toggle('hidden', isTeams);
        document.querySelectorAll('[data-tab-button]').forEach((button) => {
            const active = button.dataset.tabButton === tab;
            button.classList.toggle('bg-base-100', active);
            button.classList.toggle('shadow-sm', active);
            button.classList.toggle('text-base-content', active);
            button.classList.toggle('text-base-content/50', !active);
        });
    };

    window.closeAthleteModal = () => {
        document.getElementById('athlete_modal')?.remove();
        document.getElementById('edit_athlete_modal')?.remove();
        document.getElementById('athlete-modal-container')?.replaceChildren();
        document.getElementById('modal-container')?.replaceChildren();
    };
    window.closeExpenseModal = () => {
        document.getElementById('expense_modal')?.remove();
        document.querySelector('.app-content')?.classList.remove('modal-active');
        document.getElementById('modal-container')?.replaceChildren();
    };
    window.closePaymentModal = () => clearModal('payment_modal', 'modal-container');
    window.closeAthletePaymentModal = () => clearModal('athlete_payment_modal', 'athlete-payment-modal-container');
    window.closeRegularExpenseModal = () => {
        document.getElementById('regular_expense_modal')?.remove();
        document.getElementById('regular-expense-modal-container')?.replaceChildren();
        document.getElementById('modal-container')?.replaceChildren();
    };
    window.closeAthleteEquipmentSaleModal = () => clearModal('athlete_equipment_sale_modal', 'athlete-equipment-sale-modal-container');

    document.addEventListener('DOMContentLoaded', () => prepareMoneyInputs(document));
    document.addEventListener('htmx:afterSwap', (event) => prepareMoneyInputs(event.target));
    document.addEventListener('submit', (event) => {
        event.target.querySelectorAll?.('[data-money-input="true"]').forEach((input) => {
            input.value = normalizeMoneyValue(input.value);
        });
    }, true);

    document.body.addEventListener('closeAthleteModal', window.closeAthleteModal);
    document.body.addEventListener('closeExpenseModal', window.closeExpenseModal);
    document.body.addEventListener('closeAthletePaymentModal', window.closeAthletePaymentModal);
    document.body.addEventListener('closeRegularExpenseModal', window.closeRegularExpenseModal);
    document.body.addEventListener('closeAthleteEquipmentSaleModal', window.closeAthleteEquipmentSaleModal);
    document.body.addEventListener('htmx:responseError', (event) => console.error('HTMX response error:', event.detail));
    document.body.addEventListener('htmx:sendError', (event) => console.error('HTMX request error:', event.detail));

    document.addEventListener('DOMContentLoaded', () => {
        if (document.querySelector('.app-content')) {
            document.querySelector('.app-content').classList.add('athlete-detail-no-scroll');
        }
        if (document.getElementById('training-payments-tab')) {
            window.showPaymentTab('training');
        }
    });

    window.addEventListener('load', () => {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js', { scope: '/' });
        }
    });
})();
