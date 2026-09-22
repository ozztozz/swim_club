/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./templates/**/*.html",
        "./**/templates/**/*.html",
        "./static/js/**/*.js"
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: [
                    "Inter", "ui-sans-serif", "system-ui", "-apple-system",
                    "BlinkMacSystemFont", "Segoe UI", "sans-serif"
                ]
            },
            // Renk taglarınızı buraya ekliyoruz:
            colors: {
                'ui-bg': 'var(--ui-bg)',
                'ui-bg-soft': 'var(--ui-bg-soft)',
                'ui-surface': 'var(--ui-surface)',
                'ui-surface-2': 'var(--ui-surface-2)',
                'ui-surface-3': 'var(--ui-surface-3)',
                'ui-white': 'var(--ui-white)',
                'ui-dark': 'var(--ui-dark)',
                'ui-dark-2': 'var(--ui-dark-2)',
                'ui-dark-3': 'var(--ui-dark-3)',
                'ui-text': 'var(--ui-text)',
                'ui-text-soft': 'var(--ui-text-soft)',
                'ui-muted': 'var(--ui-muted)',
                'ui-subtle': 'var(--ui-subtle)',
                'ui-border': 'var(--ui-border)',
                'ui-border-dark': 'var(--ui-border-dark)',
                'ui-primary': 'var(--ui-primary)',
                'ui-primary-strong': 'var(--ui-primary-strong)',
                'ui-primary-text': 'var(--ui-primary-text)',
                'ui-success': 'var(--ui-success)',
                'ui-bg-success': 'var(--ui-bg-success)',
                'ui-success-text': 'var(--ui-success-text)',
                'ui-warning': 'var(--ui-warning)',
                'ui-warning-text': 'var(--ui-warning-text)',
                'ui-danger': 'var(--ui-danger)',
                'ui-danger-text': 'var(--ui-danger-text)',
                'ui-bg-error': 'var(--ui-bg-error)',
            }
        }
    },
    plugins: []
};
