import Link from "next/link";
import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "light" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  href?: string;
  variant?: Variant;
  full?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-gradient-to-br from-kola-400 to-kola-500 text-white shadow-green hover:-translate-y-0.5 hover:shadow-glow",
  secondary: "border border-white/25 bg-white/5 text-white hover:border-white/60 hover:bg-white/10",
  light: "bg-white text-kola-700 shadow-soft hover:-translate-y-0.5",
  ghost: "border border-ink-200 bg-white text-ink-800 hover:border-kola-400 hover:shadow-green"
};

export function Button({ children, href, variant = "primary", full, className = "", ...props }: ButtonProps) {
  const classes = `${full ? "w-full" : ""} inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition duration-200 ${variants[variant]} ${className}`;
  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}
