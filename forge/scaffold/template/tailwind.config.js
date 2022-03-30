const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: [
    "./app/**/*.{html,js}",
    // Include the forge templates too
    ".venv/lib/python*/site-packages/forge/**/*.{html,js}"
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
}
