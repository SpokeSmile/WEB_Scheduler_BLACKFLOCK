/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bf: {
          bg: '#151B26',
          bg2: '#1A2230',
          orange: '#D86D38',
          cream: '#E8EDF5',
          steel: '#303A50',
        },
      },
      boxShadow: {
        glow: '0 0 16px rgba(104, 114, 152, 0.16)',
        panel: '0 12px 34px rgba(0, 0, 0, 0.22)',
      },
    },
  },
  plugins: [],
};
