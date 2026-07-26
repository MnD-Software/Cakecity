const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
let token: string | null = null;
export type Staff = { id: string; email: string; first_name: string; last_name: string; role: string };
export async function kitchenApi<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && retry) {
    const refreshed = await fetch(`${API_URL}/v1/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshed.ok) { const value = await refreshed.json(); token = value.access_token; return kitchenApi<T>(path, init, false); }
  }
  if (!response.ok) { const value = await response.json().catch(() => ({})); throw new Error(value.detail ?? "Kitchen request could not be completed"); }
  return response.status === 204 ? undefined as T : response.json();
}
export async function kitchenLogin(email: string, password: string) {
  const result = await kitchenApi<{ access_token: string; customer: Staff }>("/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
  if (!["admin", "manager", "kitchen"].includes(result.customer.role)) throw new Error("This account does not have kitchen access");
  token = result.access_token; return result.customer;
}
export async function kitchenLogout() { await kitchenApi("/v1/auth/logout", { method: "POST" }); token = null; }
