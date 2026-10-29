import { Settings } from "lucide-react";
import { Link } from "react-router-dom";

export default function TopBar() {
  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 bg-brand-dark px-6 text-white">
      <Link to="/" className="flex items-center gap-3 rounded-[var(--radius)]">
        <img src="/pie_logo.webp" alt="PIE" className="h-9 w-auto" />
        <span className="h-6 w-px bg-white/25" aria-hidden />
        <span className="text-[15px] font-semibold tracking-wide">Automation Portal</span>
      </Link>
      <div className="flex items-center gap-4 text-sm text-white/80">
        <span className="hidden sm:inline">{today}</span>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white">Finance</span>
        <Link
          to="/settings"
          aria-label="Settings"
          title="Settings"
          className="inline-flex size-11 items-center justify-center rounded-full text-white/80 transition-colors duration-150 hover:bg-white/10 hover:text-white"
        >
          <Settings className="size-5" aria-hidden />
        </Link>
      </div>
    </header>
  );
}
