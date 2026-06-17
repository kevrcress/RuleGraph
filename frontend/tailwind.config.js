/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface:        "var(--surface)",
        panel:          "var(--panel)",
        panel2:         "var(--panel2)",
        line:           "var(--line)",
        line2:          "var(--line2)",
        ink:            "var(--ink)",
        ink2:           "var(--ink2)",
        ink3:           "var(--ink3)",
        ink4:           "var(--ink4)",
        accent:         "var(--accent)",
        "accent-soft":  "var(--accent-soft)",
        "accent-deep":  "var(--accent-deep)",
        clay:           "var(--clay)",
        "clay-soft":    "var(--clay-soft)",
        ok:             "var(--ok)",
        "ok-soft":      "var(--ok-soft)",
        warn:           "var(--warn)",
        "warn-soft":    "var(--warn-soft)",
        danger:         "var(--danger)",
        "danger-soft":  "var(--danger-soft)",
        info:           "var(--info)",
        "info-soft":    "var(--info-soft)",
      },
      fontFamily: {
        sans: ["Public Sans", "Inter", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "ui-monospace", "Menlo", "monospace"],
      },
      borderRadius: {
        card: "10px",
      },
    },
  },
  plugins: [],
};
