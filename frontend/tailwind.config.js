/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "Segoe UI", "sans-serif"],
        alt: ["Roboto", "Arial", "sans-serif"],
      },
      colors: {
        primary: {
          DEFAULT: "#714B67",
          hover: "#5B3B54",
        },
        sidebar: "#25232B",
        canvas: "#F8F9FA",
        ink: "#212529",
        muted: "#6C757D",
        line: "#DEE2E6",
        success: "#198754",
        warning: "#F59E0B",
        danger: "#DC3545",
        info: "#0D6EFD",
        coral: "#DC3545",
        mint: "#E8F5EE",
        sky: "#F3EDF1",
      },
      borderRadius: {
        xl: "10px",
      },
      boxShadow: {
        card: "0 1px 3px rgba(33, 37, 41, 0.08), 0 6px 16px rgba(33, 37, 41, 0.04)",
        lift: "0 10px 24px rgba(33, 37, 41, 0.12)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
