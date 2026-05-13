/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef0f6',
          100: '#d3d8eb',
          200: '#b3bddd',
          600: '#14193B',
          700: '#0e1229',
          800: '#080b1a',
        },
        accent: {
          50: '#fff2f1',
          100: '#ffdedd',
          400: '#fd7a70',
          500: '#FC5A4E',
          600: '#e84a3e',
          700: '#cf3b30',
        },
        brick: {
          50: '#f9f0f1',
          100: '#f0d9dc',
          400: '#b86970',
          500: '#A34F58',
          600: '#8f4450',
        },
        cream: '#FAF5EA',
      },
    },
  },
  plugins: [],
}
