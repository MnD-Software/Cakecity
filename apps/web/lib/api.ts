const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
let accessToken: string | null = null;

export type Customer = {
  id: string; email: string; first_name: string; last_name: string; phone?: string; role: string;
};

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && retry && path !== "/v1/auth/refresh") {
    const refreshed = await fetch(`${API_URL}/v1/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshed.ok) {
      const renewed = await refreshed.json();
      accessToken = renewed.access_token;
      return api<T>(path, init, false);
    }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Cake City could not complete that request");
  }
  return response.status === 204 ? undefined as T : response.json();
}

export async function authenticate(mode: "login" | "register", payload: Record<string, string>) {
  const authenticated = await api<{ access_token: string; customer: Customer }>(`/v1/auth/${mode}`, {
    method: "POST", body: JSON.stringify(payload),
  }, false);
  accessToken = authenticated.access_token;
  return authenticated.customer;
}

export async function logout() {
  await api("/v1/auth/logout", { method: "POST" });
  accessToken = null;
}
