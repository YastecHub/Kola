import { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id, className = "", ...props }: InputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="block" htmlFor={inputId}>
      <span className="mb-2 block text-sm font-medium text-ink-700">{label}</span>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        className={`min-h-12 w-full rounded-md border border-ink-200 bg-white px-4 text-base text-ink-900 transition focus:border-kola-500 focus:outline-none focus:ring-4 focus:ring-kola-500/10 ${error ? "border-error ring-4 ring-red-500/10" : ""} ${className}`}
        {...props}
      />
      {error ? <span id={`${inputId}-error`} className="mt-2 block text-sm text-error section-reveal">{error}</span> : null}
    </label>
  );
}
