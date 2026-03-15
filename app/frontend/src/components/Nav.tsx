"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard", exact: true },
  { href: "/log", label: "Log", exact: false },
  { href: "/chat", label: "Copilot", exact: false },
] as const;

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
      <Link
        href="/"
        className="text-lg font-semibold text-zinc-900 dark:text-zinc-100"
      >
        Climbers Journal
      </Link>
      <nav className="flex gap-1">
        {links.map(({ href, label, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                  : "text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800/50"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
