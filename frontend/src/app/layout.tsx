import type { Metadata } from "next";
import "./globals.css";
import LogoutButton from "@/components/LogoutButton";

export const metadata: Metadata = {
  title: "Climbers Journal",
  description: "Log your climbs, hikes, and adventures",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <nav className="border-b border-slate-800 px-6 py-3 flex items-center gap-6">
          <a href="/" className="text-xl font-bold text-emerald-400">
            ⛰ Climbers Journal
          </a>
          <a href="/" className="text-sm text-slate-400 hover:text-slate-100 transition-colors">
            Dashboard
          </a>
          <a href="/activities" className="text-sm text-slate-400 hover:text-slate-100 transition-colors">
            Activities
          </a>
          <a href="/chat" className="text-sm text-slate-400 hover:text-slate-100 transition-colors">
            Log Activity
          </a>
          <LogoutButton />
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
