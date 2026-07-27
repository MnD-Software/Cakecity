"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, Search, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { formatKES } from "@/lib/catalog";
import { type DiscoveryItem, type DiscoveryResponse, trackDiscovery } from "@/lib/discovery";

export function NaturalSearchPanel({ close }: { close: () => void }) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<DiscoveryItem[]>([]);
  const [message, setMessage] = useState("Describe the person, moment, flavour or budget.");
  useEffect(() => {
    if (query.trim().length < 2) {
      setMatches([]);
      setMessage("Describe the person, moment, flavour or budget.");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await api<DiscoveryResponse>(
          `/v1/discovery/search?q=${encodeURIComponent(query)}&limit=8`,
          { signal: controller.signal },
        );
        setMatches(response.items);
        setMessage(response.message);
        void trackDiscovery("search", { query, context: { results: response.items.length } });
      } catch {
        if (!controller.signal.aborted) {
          setMatches([]);
          setMessage("Search is taking a moment. Try a flavour or occasion.");
        }
      }
    }, 350);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [query]);
  return <div className="overlay search-overlay" role="dialog" aria-modal="true" aria-label="Natural language cake search"><button className="close" onClick={close}><X /></button><div className="search-panel"><p className="eyebrow">What can we help you celebrate?</p><label><Search /><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Try “a chocolate birthday cake for a 6 year old under KES 4,000”" /></label><div className="search-prompts">{["Birthday cake for a child", "Elegant cake under KES 4,000", "Chocolate gift for her"].map(prompt => <button key={prompt} onClick={() => setQuery(prompt)}>{prompt}</button>)}</div><p className="search-message" role="status">{message}</p><div className="search-results discovery-results">{matches.map(item => <a href={`/cakes/${item.slug}`} key={item.slug} onClick={() => void trackDiscovery("recommendation_click", { product_slug: item.slug, query })}>{item.image_url ? <img src={item.image_url} alt="" /> : <span className="mini-cake ruby" />}<span><b>{item.name}</b><small>{item.reason.slice(0, 2).join(" · ")}</small></span><strong>{formatKES(Number(item.price_kes))}</strong></a>)}</div></div></div>;
}

export function PersonalizedRail() {
  const [items, setItems] = useState<DiscoveryItem[]>([]);
  const [message, setMessage] = useState("");
  useEffect(() => {
    api<DiscoveryResponse>("/v1/discovery/recommendations?limit=4")
      .then(response => { setItems(response.items); setMessage(response.message); })
      .catch(() => undefined);
  }, []);
  if (!items.length) return null;
  return <section className="personalized-rail section"><div className="section-heading"><div><p className="eyebrow">Chosen with intention</p><h2>Your Cake City edit.</h2><p>{message}</p></div></div><div className="personalized-grid">{items.map(item => <a href={`/cakes/${item.slug}`} key={item.slug} onClick={() => void trackDiscovery("recommendation_click", { product_slug: item.slug, context: { surface: "homepage" } })}>{item.image_url ? <img src={item.image_url} alt={item.name} /> : <span>CC</span>}<div><small>{item.reason[0]}</small><h3>{item.name}</h3><b>{formatKES(Number(item.price_kes))}</b></div><ArrowRight /></a>)}</div></section>;
}

export function ConciergePanel({ close }: { close: () => void }) {
  const [results, setResults] = useState<DiscoveryItem[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    const form = new FormData(event.currentTarget);
    const payload = {
      occasion: form.get("occasion"), recipient: form.get("recipient"),
      flavour: form.get("flavour"), style: form.get("style"),
      budget_kes: Number(form.get("budget")), servings: Number(form.get("servings")),
    };
    try {
      const response = await api<DiscoveryResponse>("/v1/discovery/concierge", {
        method: "POST", body: JSON.stringify(payload),
      });
      setResults(response.items);
      setMessage(response.message);
      void trackDiscovery("concierge", { query: response.query, context: { results: response.items.length } });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The concierge could not complete that request.");
    } finally {
      setLoading(false);
    }
  }
  return <div className="overlay concierge-overlay" role="dialog" aria-modal="true" aria-label="Cake recommendation concierge"><button className="close" onClick={close}><X /></button><div className="concierge-panel"><header><p className="eyebrow">Cake concierge</p><h2>A considered shortlist,<br /><em>just for them.</em></h2><p>Four details are enough. We’ll balance the moment, person, flavour and budget.</p></header><form onSubmit={submit}><label>What are you celebrating?<select name="occasion"><option>Birthday</option><option>Wedding</option><option>Anniversary</option><option>Graduation</option><option>Corporate</option><option>Just because</option></select></label><label>Who is it for?<input name="recipient" required placeholder="My six-year-old daughter" /></label><label>Preferred flavour<select name="flavour"><option>Chocolate</option><option>Vanilla</option><option>Caramel</option><option>Fruit</option><option>Surprise me</option></select></label><label>Style<select name="style"><option>Elegant</option><option>Playful</option><option>Romantic</option><option>Minimal</option></select></label><label>Budget (KES)<input name="budget" type="number" min="500" max="500000" defaultValue="4000" /></label><label>Guests<input name="servings" type="number" min="1" max="1000" defaultValue="10" /></label><button className="button primary full" disabled={loading}>{loading ? "Curating…" : <>Curate my shortlist <Sparkles /></>}</button></form>{message && <p className="concierge-status" role="status">{message}</p>}{results.length > 0 && <div className="concierge-results">{results.map(item => <a href={`/cakes/${item.slug}`} key={item.slug}><span>{item.image_url ? <img src={item.image_url} alt="" /> : "CC"}</span><div><small>{item.reason.slice(0, 2).join(" · ")}</small><b>{item.name}</b><strong>{formatKES(Number(item.price_kes))}</strong></div><ArrowRight /></a>)}</div>}</div></div>;
}
