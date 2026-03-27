import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--card)",
        panelAlt: "#1a1f27",
        text: "var(--text-primary)",
        muted: "var(--text-secondary)",
        accent: "var(--neon-green)",
        accentSoft: "var(--neon-green-soft)",
        borderSoft: "var(--border)",
        danger: "#fb7185",
      },
      boxShadow: {
        card: "0 12px 34px rgba(0, 0, 0, 0.42)",
        glow: "0 0 0 1px rgba(0,255,163,0.18), 0 0 26px rgba(0,255,163,0.14)",
      },
      borderRadius: {
        xl2: "1rem",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
