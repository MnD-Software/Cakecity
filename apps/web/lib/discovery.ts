import { api } from "./api";

const SESSION_KEY = "cakecity-discovery-session-v1";

export function discoverySession(): string {
  if (typeof window === "undefined") return "server";
  let value = localStorage.getItem(SESSION_KEY);
  if (!value) {
    value = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, value);
  }
  return value;
}

export type DiscoveryItem = {
  woo_id: number; slug: string; name: string; description: string; price_kes: string;
  regular_price_kes: string | null; in_stock: boolean; stock_quantity: number | null;
  image_url: string | null; average_rating: string; review_count: number;
  reason: string[]; relevance: number;
};

export type DiscoveryResponse = {
  query: string;
  intent: Record<string, string | number | string[] | null>;
  message: string;
  items: DiscoveryItem[];
};

export async function trackDiscovery(
  event_type: "view" | "search" | "recommendation_click" | "add_to_cart" | "concierge",
  detail: { product_slug?: string; query?: string; context?: Record<string, string | number | boolean> } = {},
) {
  try {
    await api("/v1/discovery/events", {
      method: "POST",
      headers: { "X-Discovery-Session": discoverySession() },
      body: JSON.stringify({ event_type, ...detail }),
    });
  } catch {
    // Analytics must never interrupt shopping.
  }
}
