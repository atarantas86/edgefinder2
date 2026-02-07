export default function Header() {
  return (
    <header className="border-b border-white/5 bg-edge-bg/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-edge-muted">EdgeFinder</p>
          <h1 className="text-2xl font-semibold sm:text-3xl">Dashboard de signals</h1>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="rounded-full border border-edge-green/40 bg-edge-green/10 px-3 py-1 text-edge-green">
            Live
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-edge-muted">
            Backend: localhost:8000
          </span>
        </div>
      </div>
    </header>
  );
}
