/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/templates/**/*.html",
    "./app/blueprints/**/templates/**/*.html",
    // اگر فایل JS/TS یا ... داری، مسیرشان را هم اضافه کن
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

