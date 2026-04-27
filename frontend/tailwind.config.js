/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bf: {
          bg: '#0B0F1A',
          bg2: '#0F172A',
          orange: '#FF7A00',
          cream: '#E8D8C9',
          steel: '#4B607F',
        },
      },
      boxShadow: {
        glow: '0 0 32px rgba(255, 122, 0, 0.22)',
        panel: '0 26px 80px rgba(0, 0, 0, 0.42)',
      },
    },
  },
  plugins: [],
};
