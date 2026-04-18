import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        legal: {
          50: "#eef3f9",
          100: "#d4e1f0",
          200: "#a9c3e1",
          300: "#7ea5d2",
          400: "#5387c3",
          500: "#2d6aaf",
          600: "#1e3a5f",
          700: "#182e4c",
          800: "#122339",
          900: "#0c1726",
          950: "#060c14",
        },
        gold: {
          50: "#fdf8eb",
          100: "#f9edcc",
          200: "#f3db99",
          300: "#edc966",
          400: "#d4ad2e",
          500: "#c49b1a",
          600: "#a37d15",
          700: "#7d5f10",
          800: "#57420b",
          900: "#312506",
        },
        risco: {
          baixo: "#22c55e",
          medio: "#eab308",
          alto: "#f97316",
          critico: "#ef4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
