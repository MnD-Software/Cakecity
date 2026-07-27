"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CalendarDays, Check, CheckCircle2, Clock3, CreditCard, LoaderCircle, MapPin, PackageCheck, ShieldCheck, Smartphone, Store, WalletCards } from "lucide-react";
import { api, type Customer } from "@/lib/api";
import { formatKES } from "@/lib/catalog";
import { usePersistentCart } from "@/lib/use-persistent-cart";

type Fulfilment = "delivery" | "pickup";
type Quote = { subtotal: string; delivery_fee: string; total: string; currency: string };
type PaymentMethod = "mpesa" | "card" | "wallet";
type PaymentIntent = {
  id: string; order_reference: string; state: string; client_secret: string;
  action: { type: string; redirect_url?: string; message?: string };
};
type PaymentStatus = { state: string; order_reference: string; failure_message?: string };
type SavedAddress = {
  id: string; label: string; recipient_name: string; phone: string; line1: string;
  line2: string | null; area: string; city: string; delivery_notes: string | null; is_default: boolean;
};

export default function CheckoutPage() {
  const { cart, hydrated, clear } = usePersistentCart();
  const [fulfilment, setFulfilment] = useState<Fulfilment>("delivery");
  const [slot, setSlot] = useState("Today · 3:30–4:00 PM");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [status, setStatus] = useState("");
  const [details, setDetails] = useState<Record<string, string>>({});
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("mpesa");
  const [payment, setPayment] = useState<PaymentIntent | null>(null);
  const [paymentState, setPaymentState] = useState("");
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const estimated = useMemo(() => cart.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0), [cart]);
  const selectedAddress = addresses.find(address => address.id === selectedAddressId);

  useEffect(() => {
    api<{ wallet: { balance: string } }>("/v1/account/rewards")
      .then(result => setWalletBalance(Number(result.wallet.balance))).catch(() => undefined);
    api<Customer>("/v1/auth/me").then(setCustomer).catch(() => undefined);
    api<SavedAddress[]>("/v1/account/addresses").then(result => {
      setAddresses(result);
      setSelectedAddressId(result.find(address => address.is_default)?.id ?? result[0]?.id ?? "");
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("recovered") === "1") {
      void api("/v1/cart/recovered", { method: "POST" }).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (!payment || paymentMethod !== "mpesa" || !["created", "pending"].includes(paymentState)) return;
    const timer = window.setInterval(async () => {
      try {
        const result = await api<PaymentStatus>(`/v1/payments/intents/${payment.id}`, {
          headers: { "X-Payment-Secret": payment.client_secret },
        });
        setPaymentState(result.state);
        if (["paid", "failed", "cancelled", "review_required"].includes(result.state)) window.clearInterval(timer);
        if (result.state === "paid") {
          await api("/v1/cart/complete", { method: "POST" }).catch(() => undefined);
          clear();
        }
      } catch {
        // Temporary connectivity errors are retried without losing the payment reference.
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [payment, paymentMethod, paymentState]);

  async function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Confirming today’s availability and price…");
    try {
      const form = new FormData(event.currentTarget);
      const captured = Object.fromEntries([...form.entries()].map(([key, value]) => [key, String(value)]));
      const response = await api<Quote>("/v1/checkout/quote", {
        method: "POST",
        body: JSON.stringify({
          items: cart.map(item => ({
            product_slug: item.id, quantity: item.quantity, size: item.size,
            message: item.message ?? "", add_ons: item.addOns,
          })),
          fulfilment, delivery_area: form.get("area"), delivery_slot: slot,
        }),
      });
      setDetails(captured);
      setQuote(response);
      await api("/v1/cart/checkout-started", { method: "POST" }).catch(() => undefined);
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "We could not prepare checkout");
    }
  }

  async function initiatePayment() {
    setStatus("Creating your secure payment…");
    let key = sessionStorage.getItem("cakecity-payment-idempotency");
    if (!key) {
      key = `web-${crypto.randomUUID()}`;
      sessionStorage.setItem("cakecity-payment-idempotency", key);
    }
    try {
      const created = await api<PaymentIntent>("/v1/payments/intents", {
        method: "POST",
        headers: { "Idempotency-Key": key },
        body: JSON.stringify({
          method: paymentMethod,
          checkout: {
            items: cart.map(item => ({
              product_slug: item.id, quantity: item.quantity, size: item.size,
              message: item.message ?? "", add_ons: item.addOns,
            })),
            fulfilment, delivery_area: details.area, delivery_slot: slot,
          },
          customer: { email: details.email, phone: details.phone, name: details.recipient_name },
          delivery_address: fulfilment === "delivery"
            ? { line1: details.line1, area: details.area, city: "Nairobi", notes: details.notes || null }
            : null,
        }),
      });
      setPayment(created);
      setPaymentState(created.state);
      setStatus("");
      sessionStorage.setItem("cakecity-active-payment", JSON.stringify(created));
      if (created.state === "paid") {
        await api("/v1/cart/complete", { method: "POST" }).catch(() => undefined);
        clear();
      }
      if (created.action.type === "redirect" && created.action.redirect_url) {
        window.location.assign(created.action.redirect_url);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Payment could not be started");
      sessionStorage.removeItem("cakecity-payment-idempotency");
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
          {addresses.length > 0 && <section className="saved-address-picker"><div><MapPin /><span><b>Deliver to a saved place</b><small>Choose once and we’ll fill the details below.</small></span></div><div>{addresses.map(address => <button type="button" key={address.id} className={selectedAddressId === address.id ? "active" : ""} onClick={() => { setSelectedAddressId(address.id); setQuote(null); }}><span>{address.label}</span><small>{address.area}</small>{selectedAddressId === address.id && <Check />}</button>)}</div><a href="/account/addresses">Manage addresses</a></section>}
          <section key={`contact-${selectedAddressId}`} className="checkout-block contact-block"><div className="block-title"><span>01</span><div><h2>Your details</h2><p>For the receipt and delivery updates.</p></div></div><div className="field-row"><label>Full name<input name="recipient_name" required autoComplete="name" defaultValue={selectedAddress?.recipient_name ?? (customer ? `${customer.first_name} ${customer.last_name}`.trim() : "")} /></label><label>Email address<input name="email" required type="email" autoComplete="email" defaultValue={customer?.email ?? ""} /></label></div><label>Phone number<input name="phone" required type="tel" autoComplete="tel" placeholder="0712 345 678" defaultValue={selectedAddress?.phone ?? customer?.phone ?? ""} /></label></section>
          <fieldset className="fulfilment"><legend>Fulfilment</legend><button type="button" className={fulfilment === "delivery" ? "active" : ""} onClick={() => setFulfilment("delivery")}><MapPin /><span><b>Delivery</b><small>To your door in a 30-minute window</small></span>{fulfilment === "delivery" && <Check />}</button><button type="button" className={fulfilment === "pickup" ? "active" : ""} onClick={() => setFulfilment("pickup")}><Store /><span><b>Pick up</b><small>Collect from your preferred Cake City</small></span>{fulfilment === "pickup" && <Check />}</button></fieldset>
          {fulfilment === "delivery" && <section key={`delivery-${selectedAddressId}`} className="checkout-block"><div className="block-title"><span>02</span><div><h2>Delivery details</h2><p>Where the celebration is happening.</p></div></div><label>Street / building<input name="line1" required autoComplete="street-address" defaultValue={selectedAddress ? `${selectedAddress.line1}${selectedAddress.line2 ? `, ${selectedAddress.line2}` : ""}` : ""} /></label><div className="field-row"><label>Area<select name="area" required defaultValue={selectedAddress?.area ?? ""}><option value="" disabled>Select area</option>{selectedAddress && !["Kilimani","Westlands","Karen","Runda","South B","CBD"].includes(selectedAddress.area) && <option>{selectedAddress.area}</option>}<option>Kilimani</option><option>Westlands</option><option>Karen</option><option>Runda</option><option>South B</option><option>CBD</option></select></label><label>Delivery notes<input name="notes" placeholder="Gate, floor or landmark" defaultValue={selectedAddress?.delivery_notes ?? ""} /></label></div></section>}
          <section className="checkout-block"><div className="block-title"><span>03</span><div><h2>Choose the moment</h2><p>Freshness timed around your plans.</p></div></div><div className="date-choice"><CalendarDays /><span><b>Today, 26 July</b><small>Earliest available day</small></span><Check /></div><div className="slot-grid">{["Today · 3:30–4:00 PM","Today · 4:30–5:00 PM","Today · 5:30–6:00 PM","Tomorrow · 9:00–9:30 AM"].map(value => <button type="button" key={value} className={slot === value ? "active" : ""} onClick={() => setSlot(value)}><Clock3 />{value.replace("Today · ","").replace("Tomorrow · ","")}</button>)}</div></section>
        </section>
        <aside className="order-summary">
          <p className="eyebrow">Your order</p><h2>A little joy,<br />on its way.</h2>
          <div className="summary-items">{cart.map(item => <div key={`${item.id}-${item.size}`}><span className={`mini-cake ${item.palette}`} /><span><b>{item.name}</b><small>{item.size} · Qty {item.quantity}</small><small>{item.message || "No cake message"}</small></span><strong>{formatKES(item.unitPrice * item.quantity)}</strong></div>)}</div>
          <div className="summary-totals"><span><small>{quote ? "Confirmed subtotal" : "Estimated subtotal"}</small><b>{formatKES(quote ? Number(quote.subtotal) : estimated)}</b></span>{quote && <span><small>Delivery</small><b>{formatKES(Number(quote.delivery_fee))}</b></span>}<span className="grand-total"><small>Total</small><b>{formatKES(quote ? Number(quote.total) : estimated)}</b></span></div>
          {quote && !payment ? <div className="payment-picker"><p>Pay securely with</p>
            <button type="button" className={paymentMethod === "mpesa" ? "active" : ""} onClick={() => setPaymentMethod("mpesa")}><Smartphone /><span><b>M-Pesa</b><small>Prompt sent to your phone</small></span>{paymentMethod === "mpesa" && <Check />}</button>
            <button type="button" className={paymentMethod === "card" ? "active" : ""} onClick={() => setPaymentMethod("card")}><CreditCard /><span><b>Card</b><small>Visa, Mastercard and Amex</small></span>{paymentMethod === "card" && <Check />}</button>
            {walletBalance !== null && <button type="button" disabled={walletBalance < Number(quote.total)} className={paymentMethod === "wallet" ? "active" : ""} onClick={() => setPaymentMethod("wallet")}><WalletCards /><span><b>Cake City credit</b><small>{formatKES(walletBalance)} available{walletBalance < Number(quote.total) ? " · balance too low" : ""}</small></span>{paymentMethod === "wallet" && <Check />}</button>}
            <button type="button" className="button primary full" onClick={initiatePayment}>Pay {formatKES(Number(quote.total))} <ArrowRight /></button>
          </div> : !quote ? <button className="button primary full">Review availability <ArrowRight /></button> : null}
          {payment && <PaymentProgress state={paymentState} reference={payment.order_reference} message={payment.action.message} />}{status && <p className="checkout-status" role="status">{status}</p>}<p className="summary-safe"><PackageCheck /> Stock is released only after verified payment.</p>
        </aside>
      </form>
    </main>
  );
}

function PaymentProgress({ state, reference, message }: { state: string; reference: string; message?: string }) {
  const paid = state === "paid";
  const failed = ["failed", "cancelled", "review_required"].includes(state);
  return <div className={`payment-progress ${paid ? "paid" : failed ? "failed" : ""}`}>{paid ? <CheckCircle2 /> : failed ? <ShieldCheck /> : <LoaderCircle className="spin" />}<div><b>{paid ? "Payment confirmed" : failed ? "Payment needs attention" : "Waiting for confirmation"}</b><small>{paid ? `Order ${reference} is confirmed.` : failed ? "Nothing was charged twice. You can safely try again." : message || "Complete the prompt on your phone."}</small><small>Reference: {reference}</small></div></div>;
}
