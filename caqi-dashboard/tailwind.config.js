/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#070a12',
          900: '#0d1322',
          800: '#151d33',
          700: '#1e2945',
          600: '#2b395b'
        }
      }
    },
  },
  plugins: [],
}

