"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard", exact: true, tourStep: undefined },
  { href: "/calendar", label: "Calendar", exact: false, tourStep: "calendar" },
  { href: "/log", label: "Log", exact: false, tourStep: undefined },
  { href: "/import", label: "Import", exact: false, tourStep: "import" },
  { href: "/chat", label: "Copilot", exact: false, tourStep: "copilot" },
] as const;

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  function handleShowTutorial() {
    if (pathname !== "/") {
      router.push("/");
    }
    // Dispatch event after a tick so the dashboard page can pick it up
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent("start-onboarding-tour"));
    }, pathname === "/" ? 0 : 300);
  }

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-slate-700 px-6 py-3">
      <Link
        href="/"
        className="text-lg font-semibold text-emerald-400"
      >
        Climbers Journal
      </Link>
      <nav className="flex items-center gap-1">
        {links.map(({ href, label, exact, tourStep }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              {...(tourStep ? { "data-tour-step": tourStep } : {})}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-slate-800 text-slate-100"
                  : "text-slate-400 hover:bg-slate-800/50"
              }`}
            >
              {label}
            </Link>
          );
        })}
        <button
          onClick={handleShowTutorial}
          className="ml-2 rounded-md px-2 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-800/50 hover:text-slate-300"
          title="Show tutorial"
        >
          ?
        </button>
      </nav>
    </header>
  );
}
