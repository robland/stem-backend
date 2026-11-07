// Preset Tailwind partagé : les couleurs pointent vers les variables CSS de src/styles.css (clair / sombre).
const color = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: color("bg"),
        surface: color("surface"),
        "surface-2": color("surface-2"),
        border: color("border"),
        fg: color("fg"),
        muted: color("muted"),
        primary: { DEFAULT: color("primary"), fg: color("primary-fg"), soft: color("primary-soft") },
        accent: { DEFAULT: color("accent"), fg: color("accent-fg"), soft: color("accent-soft") },
        success: { DEFAULT: color("success"), soft: color("success-soft") },
        danger: { DEFAULT: color("danger"), soft: color("danger-soft") },
        ring: color("ring"),
      },
      fontFamily: {
        // Polices système : aucun téléchargement (data mobile chère). OpenDyslexic chargée à la demande.
        sans: ["var(--font-sans)"],
      },
      borderRadius: { lg: "0.875rem", xl: "1.25rem" },
      minHeight: { touch: "2.75rem" },
      minWidth: { touch: "2.75rem" },
      spacing: { "safe-b": "env(safe-area-inset-bottom)" },
      // Apparition sobre du feedback (désactivée par prefers-reduced-motion via `motion-safe:`).
      keyframes: {
        pop: { from: { opacity: "0", transform: "scale(0.98)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: { pop: "pop 200ms ease-out" },
    },
  },
};
