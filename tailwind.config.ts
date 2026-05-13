import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        kola: {
          50: "#EBF8F2",
          100: "#C5EED8",
          200: "#8FDDB5",
          300: "#4DC28A",
          400: "#2BA36A",
          500: "#1F8450",
          600: "#1A6B40",
          700: "#145230",
          800: "#0F3D24",
          900: "#0A2E1A",
          950: "#051A0F"
        },
        ink: {
          50: "#FAFAF9",
          100: "#F5F5F4",
          200: "#E7E5E4",
          300: "#D6D3D1",
          400: "#ABA29E",
          500: "#78716C",
          600: "#57534E",
          700: "#44403C",
          800: "#292524",
          900: "#1C1917",
          950: "#0C0A09"
        },
        amber: {
          50: "#FFF8EB",
          100: "#FEF3C7",
          300: "#FCD34D",
          400: "#F59E0B",
          500: "#D97706",
          600: "#B45309"
        },
        success: "#1A934A",
        warning: "#D97706",
        error: "#DC2626",
        info: "#0284C7"
      },
      fontFamily: {
        fraunces: ["Fraunces", "serif"],
        "dm-serif": ["DM Serif Display", "serif"],
        sans: ["General Sans", "DM Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
        "2xl": "32px"
      },
      boxShadow: {
        green: "0 0 0 1px rgba(31,132,80,.3), 0 8px 30px rgba(31,132,80,.2)",
        glow: "0 0 40px rgba(31,132,80,.35)",
        soft: "0 20px 60px -28px rgba(12,10,9,.4)"
      },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0) translateX(0)" },
          "33%": { transform: "translateY(-30px) translateX(10px)" },
          "66%": { transform: "translateY(20px) translateX(-10px)" }
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" }
        },
        pulseGreen: {
          "0%": { boxShadow: "0 0 0 rgba(31,132,80,.7)" },
          "70%": { boxShadow: "0 0 0 12px rgba(31,132,80,0)" },
          "100%": { boxShadow: "0 0 0 rgba(31,132,80,0)" }
        },
        drawLine: {
          from: { height: "0" },
          to: { height: "100%" }
        }
      },
      animation: {
        float: "float 20s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        "pulse-green": "pulseGreen 1s ease-out",
        "draw-line": "drawLine 1s cubic-bezier(.16,1,.3,1) forwards"
      }
    }
  },
  plugins: []
};

export default config;
