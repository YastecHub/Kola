import { ReactNode } from "react";

export function Badge({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] ${dark ? "border-kola-300/40 bg-kola-400/15 text-kola-100" : "border-kola-400/30 bg-kola-50 text-kola-700"}`}>
      <span className="h-2 w-2 animate-pulse rounded-full bg-kola-400" />
      {children}
    </span>
  );
}
