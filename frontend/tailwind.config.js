/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          0: "#fafaf8",
          1: "#f0ede8",
          2: "#e4ddd3",
          3: "#d8d0c5",
          4: "#ccc4b8",
        },
        bone: {
          0: "#1c1813",
          1: "#3a3530",
          2: "#5a554f",
          3: "#7a756e",
          4: "#b0aaa3",
        },
        brass: {
          0: "#7a5f1a",
          1: "#5a4512",
          2: "#3a2d0c",
        },
        ember: "#c0392b",
      },
      fontFamily: {
        serif: ["Newsreader", "Georgia", "serif"],
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
