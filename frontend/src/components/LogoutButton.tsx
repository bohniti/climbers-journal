"use client";

import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

export default function LogoutButton() {
  const router = useRouter();

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <button
      onClick={handleLogout}
      className="ml-auto text-sm text-slate-500 hover:text-slate-300 transition-colors"
    >
      Sign out
    </button>
  );
}
