import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#00539f", // Tesco-ish blue
          dark: "#003d75",
        },
        accent: "#ee1c2e",
      },
    },
  },
  plugins: [],
};

export default config;
