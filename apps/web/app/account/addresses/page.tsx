"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Check, Edit3, MapPin, Plus, Star, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";

export type SavedAddress = {
  id: string; label: string; recipient_name: string; phone: string;
  line1: string; line2: string | null; area: string; city: string;
  delivery_notes: string | null; is_default: boolean;
};

const emptyAddress = {
  label: "Home", recipient_name: "", phone: "", line1: "", line2: "",
  area: "", city: "Nairobi", delivery_notes: "", is_default: false,
};

export default function AddressBookPage() {
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [editing, setEditing] = useState<SavedAddress | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [status, setStatus] = useState("Loading your address book…");

  async function refresh() {
    try {
      setAddresses(await api<SavedAddress[]>("/v1/account/addresses")); setStatus("");
    } catch {
      setStatus("Sign in to manage delivery addresses securely.");
    }
  }
  useEffect(() => { void refresh(); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setStatus("Saving your delivery details…");
    const form = new FormData(event.currentTarget);
    const payload = {
      label: form.get("label"), recipient_name: form.get("recipient_name"), phone: form.get("phone"),
      line1: form.get("line1"), line2: form.get("line2") || null, area: form.get("area"),
      city: "Nairobi", delivery_notes: form.get("delivery_notes") || null,
      is_default: form.get("is_default") === "on",
    };
    try {
      await api(editing ? `/v1/account/addresses/${editing.id}` : "/v1/account/addresses", {
        method: editing ? "PUT" : "POST", body: JSON.stringify(payload),
      });
      setEditing(null); setFormOpen(false); await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save that address.");
    }
  }
  async function makeDefault(id: string) {
    await api(`/v1/account/addresses/${id}/default`, { method: "PUT" }); await refresh();
  }
  async function remove(id: string) {
    await api(`/v1/account/addresses/${id}`, { method: "DELETE" }); await refresh();
  }

  const values = editing ?? emptyAddress;
  return <main className="address-page">
    <header className="account-header"><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a><a className="back-link" href="/account"><ArrowLeft /> My account</a></header>
    <section className="address-hero"><div><p className="eyebrow">Your places</p><h1>Delivery,<br /><em>remembered.</em></h1><p>Keep the homes, offices and celebration venues you use most.</p></div><button className="button primary" onClick={() => { setEditing(null); setFormOpen(true); }}><Plus /> Add an address</button></section>
    {status && <p className="address-status" role="status">{status}</p>}
    <section className="address-grid">
      {addresses.map(address => <article key={address.id} className={address.is_default ? "default" : ""}>
        <div className="address-card-head"><span><MapPin /></span>{address.is_default && <b><Star fill="currentColor" /> Default</b>}</div>
        <p className="eyebrow">{address.label}</p><h2>{address.recipient_name}</h2>
        <address>{address.line1}{address.line2 && <>, {address.line2}</>}<br />{address.area}, {address.city}<br />{address.phone}</address>
        {address.delivery_notes && <p className="address-notes">{address.delivery_notes}</p>}
        <footer><button onClick={() => { setEditing(address); setFormOpen(true); }}><Edit3 /> Edit</button>{!address.is_default && <button onClick={() => void makeDefault(address.id)}><Star /> Make default</button>}<button className="danger" onClick={() => void remove(address.id)}><Trash2 /> Remove</button></footer>
      </article>)}
      {!addresses.length && !status && <div className="address-empty"><MapPin /><h2>No saved places yet.</h2><p>Add an address once and checkout becomes beautifully quick.</p></div>}
    </section>
    {formOpen && <div className="address-overlay" role="dialog" aria-modal="true" aria-label={editing ? "Edit address" : "Add address"}>
      <form key={editing?.id ?? "new"} onSubmit={save}>
        <button type="button" className="address-close" onClick={() => setFormOpen(false)} aria-label="Close"><X /></button>
        <p className="eyebrow">{editing ? "Update this place" : "A new celebration place"}</p><h2>{editing ? "Keep it current." : "We’ll remember it."}</h2>
        <div className="field-row"><label>Label<input name="label" required maxLength={80} defaultValue={values.label} /></label><label>Recipient<input name="recipient_name" required defaultValue={values.recipient_name} autoComplete="name" /></label></div>
        <label>Phone<input name="phone" required minLength={9} defaultValue={values.phone} autoComplete="tel" /></label>
        <label>Street / building<input name="line1" required defaultValue={values.line1} autoComplete="address-line1" /></label>
        <div className="field-row"><label>Apartment / floor<input name="line2" defaultValue={values.line2 ?? ""} autoComplete="address-line2" /></label><label>Area<input name="area" required defaultValue={values.area} placeholder="Kilimani" /></label></div>
        <label>Delivery notes<textarea name="delivery_notes" maxLength={500} defaultValue={values.delivery_notes ?? ""} placeholder="Gate, floor or landmark" /></label>
        <label className="default-check"><input name="is_default" type="checkbox" defaultChecked={values.is_default} /><span><Check /> Use first at checkout</span></label>
        <button className="button primary full">Save address</button>
      </form>
    </div>}
  </main>;
}
