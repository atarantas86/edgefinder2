export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "edge-bg": "#0a0b0f",
        "edge-green": "#00ff87",
        "edge-orange": "#ffb800",
        "edge-red": "#ff4757",
        "edge-surface": "#141620",
        "edge-card": "#171a26",
        "edge-muted": "#8c93a8"
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(0, 255, 135, 0.2), 0 10px 30px rgba(0, 0, 0, 0.45)"
      }
    }
  },
  plugins: []
};
