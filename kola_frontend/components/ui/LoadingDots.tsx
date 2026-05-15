export function LoadingDots() {
  return (
    <span aria-label="Loading" className="inline-flex items-center gap-1">
      <span className="loading-dot h-2 w-2 rounded-full bg-current" />
      <span className="loading-dot h-2 w-2 rounded-full bg-current" />
      <span className="loading-dot h-2 w-2 rounded-full bg-current" />
    </span>
  );
}
