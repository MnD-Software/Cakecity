"use client";

import { useCallback, useEffect, useState } from "react";
import type { CartItem, Product } from "./catalog";
import { api } from "./api";

const STORAGE_KEY = "cakecity-cart-v1";
const surcharges = { "1kg": 0, "1.5kg": 900, "2kg": 1700 } as const;
const addOnPrices: Record<string, number> = {
  candles: 250, "greeting-card": 350, "gift-wrap": 300, flowers: 1800,
};
type ServerLine = {
  product_slug: string; name: string; quantity: number; base_price_kes: number;
  configuration: { size?: CartItem["size"]; message?: string; add_ons?: string[] };
  description: string; image_url: string | null; average_rating: number;
};
type ServerCart = { items: ServerLine[] };

const itemKey = (item: Pick<CartItem, "id" | "size" | "message" | "addOns">) =>
  `${item.id}|${item.size}|${item.message ?? ""}|${[...item.addOns].sort().join(",")}`;

function fromServer(line: ServerLine): CartItem {
  const size = line.configuration.size ?? "1kg";
  const addOns = line.configuration.add_ons ?? [];
  const price = line.base_price_kes;
  return {
    id: line.product_slug, name: line.name,
    note: line.description.replace(/<[^>]*>/g, "").slice(0, 90),
    price, rating: line.average_rating, palette: "ruby",
    imageUrl: line.image_url ?? undefined, quantity: line.quantity, size,
    message: line.configuration.message ?? "", addOns,
    unitPrice: price + surcharges[size] + addOns.reduce((sum, item) => sum + (addOnPrices[item] ?? 0), 0),
  };
}

export function usePersistentCart() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [syncReady, setSyncReady] = useState(false);

  useEffect(() => {
    let local: CartItem[] = [];
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) local = parsed;
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    setCart(local);
    setHydrated(local.length > 0);
    api<ServerCart>("/v1/cart").then(server => {
      const merged = new Map(local.map(item => [itemKey(item), item]));
      for (const line of server.items) {
        const item = fromServer(line);
        if (!merged.has(itemKey(item))) merged.set(itemKey(item), item);
      }
      setCart([...merged.values()]);
    }).catch(() => undefined).finally(() => { setHydrated(true); setSyncReady(true); });
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    if (!syncReady) return;
    const timer = window.setTimeout(() => {
      void api("/v1/cart", {
        method: "PUT",
        body: JSON.stringify({ items: cart.map(item => ({
          product_slug: item.id, quantity: item.quantity,
          configuration: { size: item.size, message: item.message ?? "", add_ons: item.addOns },
        })) }),
      }).catch(() => undefined);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [cart, hydrated, syncReady]);

  const add = useCallback((product: Product, configuration?: {
    size?: CartItem["size"]; message?: string; addOns?: string[];
  }) => {
    const size = configuration?.size ?? "1kg";
    const message = configuration?.message?.trim() ?? "";
    const addOns = configuration?.addOns ?? [];
    const unitPrice = product.price + surcharges[size] +
      [...new Set(addOns)].reduce((total, item) => total + (addOnPrices[item] ?? 0), 0);
    setCart(current => {
      const existing = current.find(item =>
        item.id === product.id && item.size === size && item.message === message &&
        JSON.stringify(item.addOns) === JSON.stringify(addOns)
      );
      return existing
        ? current.map(item => item === existing ? { ...item, quantity: Math.min(20, item.quantity + 1) } : item)
        : [...current, { ...product, quantity: 1, size, message, addOns, unitPrice }];
    });
  }, []);

  const updateQuantity = useCallback((id: string, size: string, delta: number) => {
    setCart(current => current
      .map(item => item.id === id && item.size === size
        ? { ...item, quantity: Math.max(0, Math.min(20, item.quantity + delta)) } : item)
      .filter(item => item.quantity > 0));
  }, []);

  const clear = useCallback(() => setCart([]), []);
  return { cart, hydrated, add, updateQuantity, clear };
}
