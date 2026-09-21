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
                    "Inter",
                    "ui-sans-serif",
                    "system-ui",
                    "-apple-system",
                    "BlinkMacSystemFont",
                    "Segoe UI",
                    "sans-serif"
                ]

            }

        }

    },

    plugins: []
};