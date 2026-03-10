const TOKEN_KEY = "auth_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  // Also store in a cookie so Next.js middleware can read it
  document.cookie = `${TOKEN_KEY}=${token}; path=/; SameSite=Strict; max-age=${60 * 60 * 24 * 30}`;
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
