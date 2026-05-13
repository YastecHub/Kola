export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <span className="inline-flex items-center gap-3" aria-label="KOLA">
      <span className="relative h-8 w-9">
        <span className={`absolute left-0 top-1 h-6 w-6 rounded-full border ${dark ? "border-kola-800 bg-kola-400/30" : "border-white/60 bg-white/15"}`} />
        <span className={`absolute right-0 top-1 h-6 w-6 rounded-full border ${dark ? "border-kola-700 bg-kola-300/40" : "border-kola-200/70 bg-kola-300/20"}`} />
      </span>
      <span className={`font-fraunces text-2xl font-bold tracking-tight ${dark ? "text-kola-800" : "text-white"}`}>KOLA</span>
    </span>
  );
}
