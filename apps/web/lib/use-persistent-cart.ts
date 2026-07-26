"use client";

import { useCallback, useEffect, useState } from "react";
import type { CartItem, Product } from "./catalog";

const STORAGE_KEY = "cakecity-cart-v1";
const surcharges = { "1kg": 0, "1.5kg": 900, "2kg": 1700 } as const;

export function usePersistentCart() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) setCart(parsed);
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
  }, [cart, hydrated]);

  const add = useCallback((product: Product, configuration?: {
    size?: CartItem["size"]; message?: string; addOns?: string[];
  }) => {
    const size = configuration?.size ?? "1kg";
    const message = configuration?.message?.trim() ?? "";
    const addOns = configuration?.addOns ?? [];
    const unitPrice = product.price + surcharges[size];
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
