"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Bell, CalendarHeart, Gift, Plus, RotateCcw, Sparkles, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

type Moment = { id: string; name: string; relationship: string; occasion: string; event_date: string; reminder_days: number[]; notes?: string };
type Memory = { order_reference: string; ordered_at: string; year: number; title: string; product_name: string; product_slug: string; image_url?: string; message?: string; reorder_url: string };
type Upcoming = Moment & { next_event_date: string; days_until: number; prompt: string; last_cake?: Memory };
type Timeline = { memories: Memory[]; upcoming: Upcoming[] };

export default function MomentsPage() {
  const [moments, setMoments] = useState<Moment[]>([]);
  const [timeline, setTimeline] = useState<Timeline>({ memories: [], upcoming: [] });
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("");
  const load = async () => {
    const [saved, history] = await Promise.all([
      api<Moment[]>("/v1/account/moments"),
      api<Timeline>("/v1/account/moments/timeline"),
    ]);
    setMoments(saved); setTimeline(history);
  };
  useEffect(() => { load().catch(error => setStatus(error.message)); }, []);
  const memoriesByYear = useMemo(() => timeline.memories.reduce<Record<string, Memory[]>>((groups, memory) => {
    (groups[memory.year] ||= []).push(memory); return groups;
  }, {}), [timeline.memories]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try {
      await api("/v1/account/moments", { method: "POST", body: JSON.stringify({
        name: form.get("name"), relationship: form.get("relationship"), occasion: form.get("occasion"),
        event_date: form.get("event_date"), reminder_days: [30, 7, 1, 0], notes: form.get("notes") || null,
      }) });
      await load(); setOpen(false); setStatus("Moment saved. We’ll remind you before the day.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Moment could not be saved"); }
  }

  async function remove(id: string) {
    await api(`/v1/account/moments/${id}`, { method: "DELETE" }); setMoments(current => current.filter(item => item.id !== id));
  }

  return <main className="post-page moments-page">
    <header className="account-header"><a className="back-link" href="/account"><ArrowLeft /> My account</a><button className="button primary" onClick={() => setOpen(true)}><Plus /> Add a moment</button></header>
    <section className="post-hero"><p className="eyebrow">Your cake memories</p><h1>Every celebration,<br /><em>beautifully remembered.</em></h1><p>Look back at the cakes you shared, remember important dates and bring a favourite design back whenever you need it.</p></section>
    {timeline.upcoming[0] && <section className="memory-reminder">
      <div><span className="memory-reminder-icon"><Bell /></span><p className="eyebrow">Coming up</p><h2>{timeline.upcoming[0].prompt}</h2><small>{new Date(`${timeline.upcoming[0].next_event_date}T12:00:00`).toLocaleDateString("en-KE", { day: "numeric", month: "long", year: "numeric" })}</small></div>
      <div className="memory-actions">{timeline.upcoming[0].last_cake && <a className="button primary" href={timeline.upcoming[0].last_cake.reorder_url}><RotateCcw /> Reorder last cake</a>}<a className="button memory-secondary" href="/#concierge"><Sparkles /> Create a new design</a></div>
    </section>}
    <section className="memory-timeline">
      <div className="memory-heading"><p className="eyebrow">The story so far</p><h2>Your cake timeline</h2></div>
      {timeline.memories.length === 0 && <div className="memory-empty"><Gift /><h3>Your first cake memory will appear here.</h3><p>Completed Cake City orders are added automatically.</p><a href="/#shop">Choose a cake <ArrowRight /></a></div>}
      {Object.entries(memoriesByYear).sort(([a], [b]) => Number(b) - Number(a)).map(([year, memories]) => <div className="memory-year" key={year}><time>{year}</time><div>{memories.map(memory => <article className="memory-card" key={`${memory.order_reference}-${memory.product_name}`}><a href={`/cakes/${memory.product_slug}`} className="memory-image">{memory.image_url ? <img src={memory.image_url} alt="" /> : <Gift />}</a><div><small>{new Date(memory.ordered_at).toLocaleDateString("en-KE", { day: "numeric", month: "long" })}</small><h3>{memory.title}</h3><p>{memory.product_name}{memory.message ? ` · “${memory.message}”` : ""}</p><a href={memory.reorder_url}>View and reorder <ArrowRight /></a></div></article>)}</div></div>)}
    </section>
    <section className="moments-grid">
      {moments.length === 0 && <div className="post-empty"><CalendarHeart /><h2>No important date should sneak up on you.</h2><button className="button primary" onClick={() => setOpen(true)}>Save your first moment</button></div>}
      {moments.map(moment => <article className="moment-card" key={moment.id}><span><CalendarHeart /></span><small>{moment.relationship}</small><h2>{moment.name}</h2><p>{moment.occasion} · {new Date(`${moment.event_date}T12:00:00`).toLocaleDateString("en-KE", { day: "numeric", month: "long" })}</p><div><Bell /> Reminders {moment.reminder_days.join(", ")} days before</div><button aria-label={`Delete ${moment.name}`} onClick={() => remove(moment.id)}><Trash2 /></button></article>)}
    </section>
    {open && <div className="moment-overlay" role="dialog" aria-modal="true" aria-label="Add a celebration moment"><button className="overlay-close" onClick={() => setOpen(false)} /><form className="moment-form" onSubmit={create}><Gift /><p className="eyebrow">A date worth keeping</p><h2>Who are we celebrating?</h2><label>Their name<input name="name" required autoFocus /></label><div className="field-row"><label>Relationship<input name="relationship" required placeholder="Self, Mum, friend…" /></label><label>Occasion<select name="occasion"><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option><option value="wedding">Wedding</option><option value="graduation">Graduation</option><option value="other">Other</option></select></label></div><label>Date<input name="event_date" type="date" required /></label><label>A note, if useful<input name="notes" placeholder="Favourite flavour, age, gift idea…" /></label><button className="button primary full">Save this moment</button><button type="button" className="text-link" onClick={() => setOpen(false)}>Cancel</button></form></div>}
    {status && <div className="reward-toast" role="status">{status}</div>}
  </main>;
}
