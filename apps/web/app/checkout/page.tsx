"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CalendarDays, Check, Clock3, MapPin, PackageCheck, ShieldCheck, Store } from "lucide-react";
import { api } from "@/lib/api";
import { formatKES } from "@/lib/catalog";
import { usePersistentCart } from "@/lib/use-persistent-cart";

type Fulfilment = "delivery" | "pickup";
type Quote = { subtotal: string; delivery_fee: string; total: string; currency: string };

export default function CheckoutPage() {
  const { cart, hydrated } = usePersistentCart();
  const [fulfilment, setFulfilment] = useState<Fulfilment>("delivery");
  const [slot, setSlot] = useState("Today · 3:30–4:00 PM");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [status, setStatus] = useState("");
  const estimated = useMemo(() => cart.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0), [cart]);

  async function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Confirming today’s availability and price…");
    try {
      const response = await api<Quote>("/v1/checkout/quote", {
        method: "POST",
        body: JSON.stringify({
          items: cart.map(item => ({
            product_slug: item.id, quantity: item.quantity, size: item.size,
            message: item.message ?? "", add_ons: item.addOns,
          })),
          fulfilment, delivery_area: new FormData(event.currentTarget).get("area"), delivery_slot: slot,
        }),
      });
      setQuote(response);
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "We could not prepare checkout");
    }
  }

  if (!hydrated) return <main className="account-loading"><span className="offline-mark">CC</span><p>Preparing your bag…</p></main>;
  if (!cart.length) return <main className="empty-checkout"><span className="offline-mark">CC</span><h1>Your bag is waiting<br />for something beautiful.</h1><a className="button primary" href="/#shop">Explore cakes <ArrowRight /></a></main>;

  return (
    <main className="checkout-page">
      <header className="checkout-header"><a href="/" className="back-link"><ArrowLeft /> Continue shopping</a><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a><span><ShieldCheck /> Secure checkout</span></header>
      <form className="checkout-layout" onSubmit={review}>
        <section className="checkout-main">
          <div className="checkout-intro"><p className="eyebrow">Your moment, your way</p><h1>How should it<br /><em>reach you?</em></h1></div>
          <fieldset className="fulfilment"><legend>Fulfilment</legend><button type="button" className={fulfilment === "delivery" ? "active" : ""} onClick={() => setFulfilment("delivery")}><MapPin /><span><b>Delivery</b><small>To your door in a 30-minute window</small></span>{fulfilment === "delivery" && <Check />}</button><button type="button" className={fulfilment === "pickup" ? "active" : ""} onClick={() => setFulfilment("pickup")}><Store /><span><b>Pick up</b><small>Collect from your preferred Cake City</small></span>{fulfilment === "pickup" && <Check />}</button></fieldset>
          {fulfilment === "delivery" && <section className="checkout-block"><div className="block-title"><span>01</span><div><h2>Delivery details</h2><p>Where the celebration is happening.</p></div></div><div className="field-row"><label>Full name<input name="recipient_name" required autoComplete="name" /></label><label>Phone number<input name="phone" required type="tel" autoComplete="tel" /></label></div><label>Street / building<input name="line1" required autoComplete="street-address" /></label><div className="field-row"><label>Area<select name="area" required defaultValue=""><option value="" disabled>Select area</option><option>Kilimani</option><option>Westlands</option><option>Karen</option><option>Runda</option><option>South B</option><option>CBD</option></select></label><label>Delivery notes<input name="notes" placeholder="Gate, floor or landmark" /></label></div></section>}
          <section className="checkout-block"><div className="block-title"><span>02</span><div><h2>Choose the moment</h2><p>Freshness timed around your plans.</p></div></div><div className="date-choice"><CalendarDays /><span><b>Today, 26 July</b><small>Earliest available day</small></span><Check /></div><div className="slot-grid">{["Today · 3:30–4:00 PM","Today · 4:30–5:00 PM","Today · 5:30–6:00 PM","Tomorrow · 9:00–9:30 AM"].map(value => <button type="button" key={value} className={slot === value ? "active" : ""} onClick={() => setSlot(value)}><Clock3 />{value.replace("Today · ","").replace("Tomorrow · ","")}</button>)}</div></section>
          {status && <p className="checkout-status" role="status">{status}</p>}
        </section>
        <aside className="order-summary"><p className="eyebrow">Your order</p><h2>A little joy,<br />on its way.</h2><div className="summary-items">{cart.map(item => <div key={`${item.id}-${item.size}`}><span className={`mini-cake ${item.palette}`} /><span><b>{item.name}</b><small>{item.size} · Qty {item.quantity}</small><small>{item.message || "No cake message"}</small></span><strong>{formatKES(item.unitPrice * item.quantity)}</strong></div>)}</div><div className="summary-totals"><span><small>{quote ? "Confirmed subtotal" : "Estimated subtotal"}</small><b>{formatKES(quote ? Number(quote.subtotal) : estimated)}</b></span>{quote && <span><small>Delivery</small><b>{formatKES(Number(quote.delivery_fee))}</b></span>}<span className="grand-total"><small>Total</small><b>{formatKES(quote ? Number(quote.total) : estimated)}</b></span></div>{quote ? <button type="button" className="button primary full">Continue to secure payment <ArrowRight /></button> : <button className="button primary full">Review availability <ArrowRight /></button>}<p className="summary-safe"><PackageCheck /> We only reserve stock after price confirmation.</p></aside>
      </form>
    </main>
  );
}
