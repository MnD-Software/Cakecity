"use client";

import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { formatKES } from "@/lib/catalog";
import { type DiscoveryItem, type DiscoveryResponse, trackDiscovery } from "@/lib/discovery";

export function PersonalizedRail() {
  const [items, setItems] = useState<DiscoveryItem[]>([]);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (process.env.NODE_ENV === "production" && !process.env.NEXT_PUBLIC_API_URL) return;
    api<DiscoveryResponse>("/v1/discovery/recommendations?limit=4")
      .then(response => { setItems(response.items); setMessage(response.message); })
      .catch(() => undefined);
  }, []);
  if (!items.length) return null;
  return <section className="personalized-rail section"><div className="section-heading"><div><p className="eyebrow">Chosen with intention</p><h2>Your Cake City edit.</h2><p>{message}</p></div></div><div className="personalized-grid">{items.map(item => <a href={`/cakes/${item.slug}`} key={item.slug} onClick={() => void trackDiscovery("recommendation_click", { product_slug: item.slug, context: { surface: "homepage" } })}>{item.image_url ? <img src={item.image_url} alt={item.name} /> : <span>CC</span>}<div><small>{item.reason[0]}</small><h3>{item.name}</h3><b>{formatKES(Number(item.price_kes))}</b></div><ArrowRight /></a>)}</div></section>;
}
