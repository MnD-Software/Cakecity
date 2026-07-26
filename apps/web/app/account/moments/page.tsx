"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Bell, CalendarHeart, Gift, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

type Moment = { id: string; name: string; relationship: string; occasion: string; event_date: string; reminder_days: number[]; notes?: string };

export default function MomentsPage() {
  const [moments, setMoments] = useState<Moment[]>([]);
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("");
  const load = () => api<Moment[]>("/v1/account/moments").then(setMoments);
  useEffect(() => { load().catch(error => setStatus(error.message)); }, []);

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
    <section className="post-hero"><p className="eyebrow">Your celebration calendar</p><h1>Remember the people<br /><em>who matter.</em></h1><p>Keep birthdays, anniversaries and milestones together. Cake City will remind you at the right time.</p></section>
    <section className="moments-grid">
      {moments.length === 0 && <div className="post-empty"><CalendarHeart /><h2>No important date should sneak up on you.</h2><button className="button primary" onClick={() => setOpen(true)}>Save your first moment</button></div>}
      {moments.map(moment => <article className="moment-card" key={moment.id}><span><CalendarHeart /></span><small>{moment.relationship}</small><h2>{moment.name}</h2><p>{moment.occasion} · {new Date(`${moment.event_date}T12:00:00`).toLocaleDateString("en-KE", { day: "numeric", month: "long" })}</p><div><Bell /> Reminders {moment.reminder_days.join(", ")} days before</div><button aria-label={`Delete ${moment.name}`} onClick={() => remove(moment.id)}><Trash2 /></button></article>)}
    </section>
    {open && <div className="moment-overlay" role="dialog" aria-modal="true" aria-label="Add a celebration moment"><button className="overlay-close" onClick={() => setOpen(false)} /><form className="moment-form" onSubmit={create}><Gift /><p className="eyebrow">A date worth keeping</p><h2>Who are we celebrating?</h2><label>Their name<input name="name" required autoFocus /></label><div className="field-row"><label>Relationship<input name="relationship" required placeholder="Self, Mum, friend…" /></label><label>Occasion<select name="occasion"><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option><option value="wedding">Wedding</option><option value="graduation">Graduation</option><option value="other">Other</option></select></label></div><label>Date<input name="event_date" type="date" required /></label><label>A note, if useful<input name="notes" placeholder="Favourite flavour, age, gift idea…" /></label><button className="button primary full">Save this moment</button><button type="button" className="text-link" onClick={() => setOpen(false)}>Cancel</button></form></div>}
    {status && <div className="reward-toast" role="status">{status}</div>}
  </main>;
}
