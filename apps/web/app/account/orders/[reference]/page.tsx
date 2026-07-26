"use client";

import { use, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, ChefHat, Clock3, MapPin, MessageCircle, Navigation, RefreshCw, Send, ShoppingBag } from "lucide-react";
import { api } from "@/lib/api";

type Event = { id: string; stage: string; title: string; detail: string; occurred_at: string };
type Driver = { assignment_id: string; state: string; driver_name: string; vehicle?: string; estimated_arrival_at?: string; location?: { latitude: string; longitude: string; accuracy_meters?: string; recorded_at: string } };
type Message = { id: string; sender_role: string; body: string; created_at: string };
type Detail = { reference: string; state: string; total: string; currency: string; fulfilment: string; delivery_slot?: string; stages: string[]; timeline: Event[]; driver_tracking?: Driver; lines: { id: string; product_name: string; quantity: number; line_total: string; configuration: Record<string, unknown> }[] };
type Reorder = { available: { id: string; slug: string; name: string; price_kes: string; quantity: number; configuration: Record<string, unknown> }[]; unavailable: { product_name: string }[]; message: string };
const title = (stage: string) => stage.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());

export default function TrackingPage({ params }: { params: Promise<{ reference: string }> }) {
  const { reference } = use(params);
  const [order, setOrder] = useState<Detail | null>(null);
  const [status, setStatus] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [message, setMessage] = useState("");
  const load = useCallback(() => api<Detail>(`/v1/account/orders/${reference}`).then(setOrder).catch(error => setStatus(error.message)), [reference]);
  useEffect(() => { load(); const timer = window.setInterval(load, 15000); return () => clearInterval(timer); }, [load]);
  const loadMessages = useCallback(() => api<Message[]>(`/v1/account/orders/${reference}/delivery/messages`).then(setMessages).catch(() => undefined), [reference]);
  useEffect(() => { loadMessages(); const timer = window.setInterval(loadMessages, 15000); return () => clearInterval(timer); }, [loadMessages]);

  async function sendMessage() {
    if (!message.trim()) return;
    try { await api(`/v1/account/orders/${reference}/delivery/messages`, { method: "POST", body: JSON.stringify({ body: message.trim() }) }); setMessage(""); await loadMessages(); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Message could not be sent"); }
  }

  async function reorder() {
    setStatus("Refreshing current prices and availability…");
    try {
      const result = await api<Reorder>(`/v1/account/orders/${reference}/reorder`, { method: "POST" });
      const cart = result.available.map(item => {
        const configuration = item.configuration as { size?: "1kg" | "1.5kg" | "2kg"; message?: string; add_ons?: string[] };
        return { id: item.slug, name: item.name, note: "Reordered favourite", price: Number(item.price_kes), rating: 5, palette: "ruby", quantity: item.quantity, size: configuration.size ?? "1kg", message: configuration.message ?? "", addOns: configuration.add_ons ?? [], unitPrice: Number(item.price_kes) };
      });
      localStorage.setItem("cakecity-cart-v1", JSON.stringify(cart));
      setStatus(result.unavailable.length ? `${result.unavailable.length} unavailable item excluded. Your refreshed basket is ready.` : "Your refreshed basket is ready.");
      window.setTimeout(() => location.assign("/checkout"), 700);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not prepare this reorder"); }
  }

  if (!order) return <main className="post-page"><div className="post-empty"><Clock3 /><h2>{status || "Preparing live tracking…"}</h2><a href="/account/orders">Back to orders</a></div></main>;
  const current = Math.max(0, order.stages.indexOf(order.state));
  return <main className="post-page">
    <header className="account-header"><a className="back-link" href="/account/orders"><ArrowLeft /> All orders</a><button onClick={load}><RefreshCw /> Refresh</button></header>
    <section className="tracking-head"><div><p className="eyebrow">Live order journey</p><h1>{order.reference}</h1><p><span className="live-dot" /> Updates automatically every 15 seconds</p></div><div><small>Current stage</small><strong>{title(order.state)}</strong>{order.delivery_slot && <span>{order.delivery_slot}</span>}</div></section>
    <section className="tracking-layout">
      <div className="timeline">
        {order.stages.map((stage, index) => {
          const event = [...order.timeline].reverse().find(item => item.stage === stage);
          const complete = index <= current;
          return <div className={`timeline-step ${complete ? "complete" : ""} ${index === current ? "current" : ""}`} key={stage}><span>{complete ? <Check /> : index + 1}</span><div><h2>{event?.title ?? title(stage)}</h2><p>{event?.detail ?? "We’ll update you as your cake reaches this stage."}</p>{event && <small>{new Date(event.occurred_at).toLocaleString("en-KE")}</small>}</div></div>;
        })}
      </div>
      <aside className="tracking-side">
        {order.driver_tracking && <section className="driver-live"><div className="driver-title"><span><Navigation /></span><div><small>Your driver</small><h2>{order.driver_tracking.driver_name}</h2><p>{order.driver_tracking.vehicle}</p></div><i>LIVE</i></div>{order.driver_tracking.estimated_arrival_at && <p className="driver-eta"><Clock3 /><span><small>Estimated arrival</small><b>{new Date(order.driver_tracking.estimated_arrival_at).toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit" })}</b></span></p>}{order.driver_tracking.location && <a className="driver-map" target="_blank" href={`https://www.google.com/maps?q=${order.driver_tracking.location.latitude},${order.driver_tracking.location.longitude}`}><MapPin /> View live position<small>Updated {new Date(order.driver_tracking.location.recorded_at).toLocaleTimeString("en-KE")}</small></a>}<div className="driver-chat"><h3><MessageCircle /> Driver chat</h3><div>{messages.length ? messages.map(item => <p className={item.sender_role} key={item.id}><b>{item.sender_role === "customer" ? "You" : order.driver_tracking?.driver_name}</b>{item.body}</p>) : <small>No messages yet. Your driver can help with arrival details.</small>}</div><label><input value={message} onChange={event => setMessage(event.target.value)} placeholder="Message your driver" maxLength={500} /><button onClick={sendMessage} aria-label="Send message"><Send /></button></label></div></section>}
        <section className="order-recap"><ChefHat /><p className="eyebrow">Your order</p>{order.lines.map(line => <div key={line.id}><span><b>{line.product_name}</b><small>Quantity {line.quantity}</small></span><strong>KES {Number(line.line_total).toLocaleString()}</strong></div>)}<div className="recap-total"><span>Total</span><strong>{order.currency} {Number(order.total).toLocaleString()}</strong></div><button className="button primary full" onClick={reorder}><ShoppingBag /> Reorder with current prices</button>{status && <p className="form-status" role="status">{status}</p>}</section>
      </aside>
    </section>
  </main>;
}
