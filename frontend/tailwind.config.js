/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        finBg: '#030008',
        finSide: '#070112',
        finCard: '#0c021c',
        finAccent1: '#a855f7',
        finAccent2: '#d946ef',
        zinc: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7e22ce',
          800: '#3b0764',   // Very dark purple
          900: '#28044a',   // Ultra dark purple
          950: '#110126',   // Blackish purple
        }
      }
    },
  },
  plugins: [],
}
