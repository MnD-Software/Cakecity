"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, CalendarClock, Check, Pause, Play, Plus, RefreshCw, ShoppingBag, X } from "lucide-react";
import { api } from "@/lib/api";
import { formatKES, type Product } from "@/lib/catalog";
import { usePersistentCart } from "@/lib/use-persistent-cart";

type CatalogProduct = { slug: string; name: string; description: string; price_kes: string; image_url: string | null; average_rating: string };
type Address = { id: string; label: string; area: string; is_default: boolean };
type Run = { id: string; scheduled_for: string; state: "ready" | "ordered" | "skipped" };
type Plan = {
  id: string; name: string; cadence: string; configuration: {
    size: "1kg" | "1.5kg" | "2kg"; message: string; add_ons: string[]; quantity: number;
  }; fulfilment: "delivery" | "pickup"; delivery_slot: string; state: string;
  next_run_at: string; last_run_at: string | null;
  product: CatalogProduct & { in_stock: boolean }; address: Address | null; runs: Run[];
};

export default function SubscriptionManagerPage() {
  const { add } = usePersistentCart();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [status, setStatus] = useState("Preparing your cake plans…");
  const [initialSlug, setInitialSlug] = useState("");

  async function refresh() {
    try {
      const [savedPlans, catalogue, savedAddresses] = await Promise.all([
        api<Plan[]>("/v1/account/subscriptions"),
        api<{ items: CatalogProduct[] }>("/v1/catalog/products?page_size=60"),
        api<Address[]>("/v1/account/addresses"),
      ]);
      setPlans(savedPlans); setProducts(catalogue.items); setAddresses(savedAddresses); setStatus("");
    } catch {
      setStatus("Sign in to create and manage recurring cake plans.");
    }
  }
  useEffect(() => {
    const slug = new URLSearchParams(window.location.search).get("product") ?? "";
    setInitialSlug(slug); if (slug) setFormOpen(true);
    void refresh();
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setStatus("Creating your cake plan…");
    const form = new FormData(event.currentTarget);
    const localDate = new Date(String(form.get("next_run_at")));
    try {
      await api("/v1/account/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"), product_slug: form.get("product_slug"), cadence: form.get("cadence"),
          configuration: { size: form.get("size"), message: form.get("message"), add_ons: [], quantity: Number(form.get("quantity")) },
          fulfilment: form.get("fulfilment"), address_id: form.get("address_id") || null,
          delivery_slot: form.get("delivery_slot"), next_run_at: localDate.toISOString(),
        }),
      });
      setFormOpen(false); setInitialSlug(""); await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not create that plan.");
    }
  }

  async function changeState(plan: Plan, state: "active" | "paused" | "cancelled") {
    const payload: Record<string, string> = { state };
    if (state === "active" && new Date(plan.next_run_at) <= new Date()) {
      const next = new Date(); next.setDate(next.getDate() + 1); payload.next_run_at = next.toISOString();
    }
    await api(`/v1/account/subscriptions/${plan.id}`, { method: "PATCH", body: JSON.stringify(payload) }); await refresh();
  }

  async function orderPlan(plan: Plan) {
    const product: Product = {
      id: plan.product.slug, name: plan.product.name,
      note: plan.product.description.replace(/<[^>]*>/g, "").slice(0, 90),
      price: Number(plan.product.price_kes), rating: Number(plan.product.average_rating || 0),
      palette: "ruby", imageUrl: plan.product.image_url ?? undefined,
    };
    for (let count = 0; count < plan.configuration.quantity; count += 1) {
      add(product, { size: plan.configuration.size, message: plan.configuration.message, addOns: plan.configuration.add_ons });
    }
    const readyRun = plan.runs.find(run => run.state === "ready");
    if (readyRun) await api(`/v1/account/subscriptions/runs/${readyRun.id}/ordered`, { method: "POST" });
    window.location.assign("/checkout");
  }

  const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 16);
  return <main className="subscriptions-page">
    <header className="account-header"><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a><a className="back-link" href="/account"><ArrowLeft /> My account</a></header>
    <section className="subscriptions-hero"><div><p className="eyebrow">Cake plans</p><h1>Joy,<br /><em>on repeat.</em></h1><p>Schedule it once or make it a tradition. Every renewal waits for your secure confirmation.</p></div><button className="button primary" onClick={() => setFormOpen(true)}><Plus /> Create a plan</button></section>
    {status && <p className="subscription-status" role="status">{status}</p>}
    <section className="plan-grid">{plans.map(plan => <article key={plan.id} className={`plan-card ${plan.state}`}>
      <div className="plan-media">{plan.product.image_url ? <img src={plan.product.image_url} alt={plan.product.name} /> : <span>CC</span>}<b>{plan.cadence}</b></div>
      <div className="plan-copy"><p className="eyebrow">{plan.state}</p><h2>{plan.name}</h2><p>{plan.product.name} · {plan.configuration.size} · Qty {plan.configuration.quantity}</p>
        <dl><div><dt>Next renewal</dt><dd>{new Date(plan.next_run_at).toLocaleString("en-KE", { dateStyle: "medium", timeStyle: "short" })}</dd></div><div><dt>Arrival</dt><dd>{plan.fulfilment === "delivery" ? plan.address?.label ?? "Address needed" : "Cake City pickup"} · {plan.delivery_slot}</dd></div></dl>
        {plan.runs.some(run => run.state === "ready") && <p className="renewal-ready"><Check /> A renewal is ready for confirmation.</p>}
        <div className="plan-actions"><button className="order-plan" disabled={!plan.product.in_stock} onClick={() => void orderPlan(plan)}><ShoppingBag /> Order this delivery</button>{plan.state === "active" ? <button onClick={() => void changeState(plan, "paused")}><Pause /> Pause</button> : plan.state === "paused" ? <button onClick={() => void changeState(plan, "active")}><Play /> Resume</button> : null}{!["cancelled","completed"].includes(plan.state) && <button onClick={() => void changeState(plan, "cancelled")}><X /> Cancel</button>}</div>
      </div>
    </article>)}
    {!plans.length && !status && <div className="plan-empty"><RefreshCw /><h2>No cake plans yet.</h2><p>Perfect for office Fridays, monthly birthdays and annual traditions.</p></div>}</section>
    {formOpen && <div className="subscription-overlay" role="dialog" aria-modal="true" aria-label="Create a cake plan"><form onSubmit={create}>
      <button type="button" className="subscription-close" onClick={() => setFormOpen(false)}><X /></button><p className="eyebrow">A future worth remembering</p><h2>Plan the next joy.</h2>
      <label>Plan name<input name="name" required maxLength={120} placeholder="Office Friday cake" /></label>
      <label>Cake<select name="product_slug" required defaultValue={initialSlug}><option value="" disabled>Choose a cake</option>{products.map(product => <option key={product.slug} value={product.slug}>{product.name} · {formatKES(Number(product.price_kes))}</option>)}</select></label>
      <div className="field-row"><label>Cadence<select name="cadence"><option value="once">One scheduled order</option><option value="weekly">Every week</option><option value="monthly">Every month</option><option value="quarterly">Every 3 months</option><option value="yearly">Every year</option></select></label><label>First renewal<input name="next_run_at" type="datetime-local" required min={tomorrow} defaultValue={tomorrow} /></label></div>
      <div className="field-row"><label>Size<select name="size"><option>1kg</option><option>1.5kg</option><option>2kg</option></select></label><label>Quantity<input name="quantity" type="number" min="1" max="20" defaultValue="1" /></label></div>
      <label>Cake inscription<input name="message" maxLength={32} placeholder="Optional message" /></label>
      <div className="field-row"><label>Fulfilment<select name="fulfilment"><option value="delivery">Delivery</option><option value="pickup">Pickup</option></select></label><label>Saved address<select name="address_id" defaultValue={addresses.find(address => address.is_default)?.id ?? ""}><option value="">Pickup / choose later</option>{addresses.map(address => <option key={address.id} value={address.id}>{address.label} · {address.area}</option>)}</select></label></div>
      <label>Preferred window<input name="delivery_slot" required defaultValue="10:00–10:30 AM" /></label>
      <p className="plan-consent"><CalendarClock /> We notify you when each renewal is ready. Payment always uses secure checkout; Cake City never stores raw card details.</p>
      <button className="button primary full">Create cake plan</button>
    </form></div>}
  </main>;
}
