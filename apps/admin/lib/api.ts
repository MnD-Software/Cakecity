const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
let token: string | null = null;

export type Staff = { id: string; email: string; first_name: string; last_name: string; role: string };

export async function adminApi<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && retry) {
    const refresh = await fetch(`${API_URL}/v1/auth/refresh`, { method: "POST", credentials: "include" });
    if (refresh.ok) {
      const result = await refresh.json();
      token = result.access_token;
      return adminApi<T>(path, init, false);
    }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Cake City Command could not complete that request");
  }
  return response.status === 204 ? undefined as T : response.json();
}

export async function staffLogin(email: string, password: string): Promise<Staff> {
  const result = await adminApi<{ access_token: string; customer: Staff }>("/v1/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }, false);
  if (!["admin", "manager", "marketing", "support"].includes(result.customer.role)) {
    token = null;
    throw new Error("This account does not have staff access");
  }
  token = result.access_token;
  return result.customer;
}

export async function staffLogout() {
  await adminApi("/v1/auth/logout", { method: "POST" });
  token = null;
}
