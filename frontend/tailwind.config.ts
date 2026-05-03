import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f4ff",
          100: "#dde8ff",
          500: "#4f6ef7",
          600: "#3b57e8",
          700: "#2d44cc",
        },
      },
    },
  },
  plugins: [],
};
export default config;
