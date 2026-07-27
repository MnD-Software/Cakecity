"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

const STORAGE_KEY = "cakecity-saved-cakes-v1";
type SavedCake = { slug: string };

function readLocal(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value.filter(item => typeof item === "string").slice(0, 100) : [];
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

export function useSavedCakes() {
  const [slugs, setSlugs] = useState<string[]>([]);

  useEffect(() => {
    const local = readLocal();
    setSlugs(local);
    api<SavedCake[]>("/v1/account/saved/cakes")
      .then(async remote => {
        const remoteSlugs = remote.map(item => item.slug);
        const missing = local.filter(slug => !remoteSlugs.includes(slug));
        await Promise.all(missing.map(slug =>
          api(`/v1/account/saved/cakes/${encodeURIComponent(slug)}`, { method: "PUT" }).catch(() => undefined),
        ));
        const merged = [...new Set([...remoteSlugs, ...missing])];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
        setSlugs(merged);
      })
      .catch(() => undefined);
  }, []);

  const toggle = useCallback((slug: string) => {
    setSlugs(current => {
      const removing = current.includes(slug);
      const next = removing ? current.filter(item => item !== slug) : [...current, slug];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      void api(`/v1/account/saved/cakes/${encodeURIComponent(slug)}`, {
        method: removing ? "DELETE" : "PUT",
      }).catch(() => undefined);
      return next;
    });
  }, []);

  return { savedSlugs: slugs, isSaved: (slug: string) => slugs.includes(slug), toggle };
}
