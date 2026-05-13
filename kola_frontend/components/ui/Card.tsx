import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: "light" | "dark" | "green";
}

export function Card({ tone = "light", className = "", ...props }: CardProps) {
  const toneClass = tone === "dark" ? "glass-card-dark text-white" : tone === "green" ? "glass-card-green" : "rounded-2xl border border-ink-200 bg-white shadow-soft";
  return <div className={`${toneClass} ${className}`} {...props} />;
}
