/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          0: "#0e0d0c",
          1: "#161513",
          2: "#1e1c19",
          3: "#2a2820",
          4: "#3a3830",
        },
        bone: {
          0: "#e8e0d0",
          1: "#c8c0b0",
          2: "#a8a090",
          3: "#787060",
          4: "#484038",
        },
        brass: {
          0: "#c9a84c",
          1: "#8a6f32",
          2: "#5a4820",
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
