const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: [
    "./app/**/*.{html,js}",
    // Include the forge package templates (in development and production)
    "./{.venv,.heroku/python}/lib/python*/site-packages/forge*/**/*.{html,js}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
}
