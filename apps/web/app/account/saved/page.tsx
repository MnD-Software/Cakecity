"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Heart, MessageSquareText, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatKES } from "@/lib/catalog";

type SavedCake = { id: string; slug: string; name: string; image_url: string | null; price_kes: number; in_stock: boolean };
type SavedMessage = { id: string; label: string; message: string };

export default function SavedCelebrationsPage() {
  const [cakes, setCakes] = useState<SavedCake[]>([]);
  const [messages, setMessages] = useState<SavedMessage[]>([]);
  const [status, setStatus] = useState("Loading your saved celebrations…");

  async function refresh() {
    try {
      const [savedCakes, savedMessages] = await Promise.all([
        api<SavedCake[]>("/v1/account/saved/cakes"),
        api<SavedMessage[]>("/v1/account/saved/messages"),
      ]);
      setCakes(savedCakes); setMessages(savedMessages); setStatus("");
    } catch {
      setStatus("Sign in to keep favourites and messages securely across your devices.");
    }
  }
  useEffect(() => { void refresh(); }, []);

  async function addMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await api("/v1/account/saved/messages", { method: "POST", body: JSON.stringify({ label: data.get("label"), message: data.get("message") }) });
      form.reset(); await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save that message.");
    }
  }
  async function removeCake(slug: string) {
    await api(`/v1/account/saved/cakes/${encodeURIComponent(slug)}`, { method: "DELETE" });
    setCakes(current => current.filter(cake => cake.slug !== slug));
  }
  async function removeMessage(id: string) {
    await api(`/v1/account/saved/messages/${id}`, { method: "DELETE" });
    setMessages(current => current.filter(message => message.id !== id));
  }

  return <main className="saved-page">
    <header className="account-header"><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a><a className="back-link" href="/account"><ArrowLeft /> My account</a></header>
    <section className="saved-hero"><p className="eyebrow">Celebration library</p><h1>The cakes and words<br /><em>worth keeping.</em></h1><p>Saved to your private Cake City account and ready for the next beautiful moment.</p></section>
    {status && <p className="saved-status" role="status">{status}</p>}
    <section className="saved-layout">
      <div className="saved-cakes">
        <div className="saved-heading"><Heart /><div><p className="eyebrow">Favourite cakes</p><h2>Your considered edit.</h2></div></div>
        {cakes.length === 0 ? <div className="saved-empty"><Heart /><b>No account favourites yet.</b><p>Tap the heart on any cake, then it will be waiting here.</p><a href="/#shop">Explore cakes <ArrowRight /></a></div> :
          <div className="saved-cake-grid">{cakes.map(cake => <article key={cake.id}>
            {cake.image_url ? <img src={cake.image_url} alt={cake.name} /> : <span className="saved-cake-mark">CC</span>}
            <div><small>{cake.in_stock ? "Available to order" : "Currently unavailable"}</small><h3>{cake.name}</h3><b>{formatKES(cake.price_kes)}</b></div>
            <a href={`/cakes/${cake.slug}`}>Personalise <ArrowRight /></a>
            <button onClick={() => void removeCake(cake.slug)} aria-label={`Remove ${cake.name}`}><Trash2 /></button>
          </article>)}</div>}
      </div>
      <aside className="saved-messages">
        <div className="saved-heading"><MessageSquareText /><div><p className="eyebrow">Saved inscriptions</p><h2>Say it beautifully.</h2></div></div>
        <form onSubmit={addMessage}><label>Short label<input name="label" maxLength={80} required placeholder="Amani’s birthday" /></label><label>Your message<textarea name="message" maxLength={160} required placeholder="Happy birthday, Amani!" /></label><button className="button primary full"><Plus /> Save message</button></form>
        <div className="message-list">{messages.map(item => <div key={item.id}><span><small>{item.label}</small><q>{item.message}</q></span><button onClick={() => void removeMessage(item.id)} aria-label={`Delete ${item.label}`}><Trash2 /></button></div>)}</div>
      </aside>
    </section>
  </main>;
}
