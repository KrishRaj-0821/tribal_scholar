/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          deepBlue: '#1D0A69',
          ashokaBlue: '#0F4C81',
          earthBrown: '#150202',
          linen: '#EBEAEA',
          canvas: '#F4F6F8',
          slate: '#263238',
          muted: '#546E7A',
          border: '#CFD8DC',
          borderSubtle: '#ECEFF1',
          terracotta: '#C85A17',
          saffron: '#FF9933',
          green: '#138808',
          success: '#198754',
          warning: '#FFC107',
          danger: '#A71D2A',
          info: '#0288D1',
        }
      },
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        serif: ['"Noto Serif"', 'Georgia', '"Times New Roman"', 'serif'],
        mono: ['"JetBrains Mono"', '"Courier New"', 'monospace'],
      },
    },
  },
  plugins: [],
}
