"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  ArrowLeft, ArrowRight, Building2, CalendarClock, Check, ChevronRight,
  CircleDollarSign, Clock3, FileText, LogIn, PackagePlus, RefreshCw,
  ShieldCheck, Sparkles, Users2, X,
} from "lucide-react";
import { api } from "@/lib/api";

type Home = {
  account: { id: string; name: string; tax_pin?: string; credit_limit: string; outstanding: string; available_credit: string; payment_terms_days: number };
  membership: { role: string; spend_limit?: string; cost_center?: string };
  account_manager?: { name: string; email: string; phone?: string };
  pending_approvals: number;
};
type RequestItem = {
  id: string; reference: string; title: string; purchase_order_number?: string; cost_center?: string;
  state: string; total: string; fulfilment: string; delivery_slot?: string; submitted_at: string;
  rejection_reason?: string; quote: { lines: { name: string; quantity: number; line_total: string }[] };
};
type Invoice = { id: string; invoice_number: string; purchase_order_number?: string; amount: string; amount_paid: string; state: string; issued_at: string; due_at: string };
type Recurring = { id: string; name: string; cadence: string; next_run_at: string; is_active: boolean; last_run_at?: string };
type Product = { slug: string; name: string; price_kes: string };
type Catalog = { items: Product[] };
type View = "overview" | "requests" | "invoices" | "recurring";
const title = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const money = (value: string | number) => `KES ${Number(value).toLocaleString("en-KE")}`;

export default function CorporatePage() {
  const [home, setHome] = useState<Home | null>(null);
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [recurring, setRecurring] = useState<Recurring[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [view, setView] = useState<View>("overview");
  const [status, setStatus] = useState("Opening your company workspace…");
  const [accessDenied, setAccessDenied] = useState(false);
  const [composer, setComposer] = useState(false);
  const load = useCallback(async () => {
    try {
      const [workspace, requestRows, invoiceRows, recurringRows, catalog] = await Promise.all([
        api<Home>("/v1/corporate/me"), api<RequestItem[]>("/v1/corporate/requests"),
        api<Invoice[]>("/v1/corporate/invoices"), api<Recurring[]>("/v1/corporate/recurring"),
        api<Catalog>("/v1/catalog/products?page_size=60"),
      ]);
      setHome(workspace); setRequests(requestRows); setInvoices(invoiceRows);
      setRecurring(recurringRows); setProducts(catalog.items); setStatus("");
    } catch (error) {
      setAccessDenied(true);
      const message = error instanceof Error ? error.message : "";
      setStatus(message === "Failed to fetch"
        ? "Sign in with your invited company account to continue."
        : message || "Corporate access is unavailable");
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (!home) return <main className="corp-gate"><a href="/"><ArrowLeft /> Cake City</a><section><span><Building2 /></span><p className="corp-eyebrow">Cake City for Business</p><h1>{accessDenied ? <>Your company table<br />isn’t ready yet.</> : <>Opening your<br />company table.</>}</h1><p>{status}</p>{accessDenied && <><a className="corp-primary" href="/account"><LogIn /> Sign in with your invited account</a><a className="corp-contact" href="mailto:corporate@cakecity.co.ke">Apply for a corporate account <ArrowRight /></a></>}</section></main>;

  const awaiting = requests.filter(item => item.state === "pending_approval");
  return <main className="corp-shell">
    <aside className="corp-sidebar">
      <a className="corp-brand" href="/"><span>CAKE CITY</span><b>BUSINESS</b></a>
      <div className="corp-company"><span>{home.account.name[0]}</span><div><b>{home.account.name}</b><small>{title(home.membership.role)} access</small></div></div>
      <nav>
        <button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}><Sparkles /> Overview</button>
        <button className={view === "requests" ? "active" : ""} onClick={() => setView("requests")}><PackagePlus /> Orders {awaiting.length > 0 && <i>{awaiting.length}</i>}</button>
        <button className={view === "invoices" ? "active" : ""} onClick={() => setView("invoices")}><FileText /> Invoices</button>
        <button className={view === "recurring" ? "active" : ""} onClick={() => setView("recurring")}><CalendarClock /> Recurring</button>
      </nav>
      {home.account_manager && <div className="corp-manager"><small>Your Cake City partner</small><b>{home.account_manager.name}</b><a href={`mailto:${home.account_manager.email}`}>{home.account_manager.email}</a></div>}
      <a className="corp-back" href="/account"><ArrowLeft /> Personal account</a>
    </aside>
    <section className="corp-main">
      <header><div><p className="corp-eyebrow">Corporate workspace</p><h1>{view === "overview" ? `Good business, beautifully served.` : title(view)}</h1></div><button onClick={() => setComposer(true)}><PackagePlus /> New order request</button></header>
      {view === "overview" && <Overview home={home} requests={requests} invoices={invoices} choose={setView} />}
      {view === "requests" && <Requests items={requests} canApprove={["approver", "admin"].includes(home.membership.role)} refresh={load} />}
      {view === "invoices" && <Invoices items={invoices} />}
      {view === "recurring" && <RecurringOrders items={recurring} products={products} refresh={load} />}
    </section>
    {composer && <OrderComposer products={products} home={home} close={() => setComposer(false)} saved={async () => { setComposer(false); await load(); setView("requests"); }} />}
  </main>;
}

function Overview({ home, requests, invoices, choose }: { home: Home; requests: RequestItem[]; invoices: Invoice[]; choose: (view: View) => void }) {
  const utilization = Math.min(100, Number(home.account.outstanding) / Math.max(Number(home.account.credit_limit), 1) * 100);
  return <div className="corp-overview">
    <section className="corp-credit"><div><p className="corp-eyebrow light">Available purchasing power</p><h2>{money(home.account.available_credit)}</h2><span>of {money(home.account.credit_limit)} credit facility</span></div><CircleDollarSign /><footer><span><i style={{ width: `${utilization}%` }} /></span><small>{utilization.toFixed(0)}% currently utilized · {home.account.payment_terms_days}-day terms</small></footer></section>
    <section className="corp-metrics"><article><span><Clock3 /></span><small>Awaiting approval</small><b>{home.pending_approvals}</b><button onClick={() => choose("requests")}>Review queue <ChevronRight /></button></article><article><span><FileText /></span><small>Outstanding invoices</small><b>{money(home.account.outstanding)}</b><button onClick={() => choose("invoices")}>View ledger <ChevronRight /></button></article><article><span><PackagePlus /></span><small>Orders requested</small><b>{requests.length}</b><button onClick={() => choose("requests")}>Order history <ChevronRight /></button></article></section>
    <section className="corp-recent"><header><div><p className="corp-eyebrow">Latest activity</p><h2>Your company order desk</h2></div><button onClick={() => choose("requests")}>See everything</button></header>{requests.slice(0, 5).map(item => <div key={item.id}><span className={`corp-state ${item.state}`}>{item.state === "converted" ? <Check /> : <Clock3 />}</span><div><b>{item.title}</b><small>{item.reference} · {new Date(item.submitted_at).toLocaleDateString("en-KE")}</small></div><strong>{money(item.total)}</strong><em>{title(item.state)}</em></div>)}{requests.length === 0 && <p className="corp-empty">Your first company order will appear here.</p>}</section>
    <section className="corp-policy"><ShieldCheck /><div><b>Purchasing controls are active</b><p>Every request follows your organization’s approval and credit policy before it reaches the Cake City kitchen.</p></div><span>{home.membership.cost_center || "Company-wide"} cost centre</span></section>
  </div>;
}

function Requests({ items, canApprove, refresh }: { items: RequestItem[]; canApprove: boolean; refresh: () => Promise<void> }) {
  const [busy, setBusy] = useState("");
  async function decide(id: string, decision: "approve" | "reject") {
    const note = decision === "reject" ? window.prompt("Why is this request being returned?") : "";
    if (decision === "reject" && !note) return;
    setBusy(id);
    try { await api(`/v1/corporate/requests/${id}/${decision}`, { method: "POST", body: JSON.stringify({ note }) }); await refresh(); }
    finally { setBusy(""); }
  }
  return <section className="corp-list"><div className="corp-list-head"><p>{items.length} order requests</p><button onClick={refresh}><RefreshCw /> Refresh</button></div>{items.map(item => <article key={item.id}><header><span className={`request-status ${item.state}`}>{title(item.state)}</span><small>{item.reference}</small><time>{new Date(item.submitted_at).toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric" })}</time></header><div><h2>{item.title}</h2><p>{item.quote.lines.map(line => `${line.quantity}× ${line.name}`).join(" · ")}</p><span>{item.purchase_order_number ? `PO ${item.purchase_order_number}` : "No PO supplied"} · {item.cost_center || "General"}</span></div><strong>{money(item.total)}</strong>{item.rejection_reason && <p className="request-reason">{item.rejection_reason}</p>}{canApprove && item.state === "pending_approval" && <footer><button disabled={busy === item.id} onClick={() => decide(item.id, "reject")}><X /> Return</button><button disabled={busy === item.id} onClick={() => decide(item.id, "approve")}><Check /> Approve & invoice</button></footer>}</article>)}</section>;
}

function Invoices({ items }: { items: Invoice[] }) {
  return <section className="invoice-ledger"><div className="ledger-head"><span>Invoice</span><span>Issued</span><span>Due</span><span>Amount</span><span>Status</span></div>{items.map(item => <article key={item.id}><div><FileText /><span><b>{item.invoice_number}</b><small>{item.purchase_order_number ? `PO ${item.purchase_order_number}` : "Cake City invoice"}</small></span></div><time>{new Date(item.issued_at).toLocaleDateString("en-KE")}</time><time>{new Date(item.due_at).toLocaleDateString("en-KE")}</time><strong>{money(item.amount)}</strong><em className={item.state}>{title(item.state)}</em></article>)}{items.length === 0 && <p className="corp-empty">Approved orders will create invoices here automatically.</p>}</section>;
}

function RecurringOrders({ items, products, refresh }: { items: Recurring[]; products: Product[]; refresh: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    await api("/v1/corporate/recurring", { method: "POST", body: JSON.stringify({
      name: form.get("name"), cadence: form.get("cadence"), next_run_at: new Date(String(form.get("next_run_at"))).toISOString(),
      order: { title: form.get("name"), purchase_order_number: form.get("po") || null,
        items: [{ product_slug: form.get("product"), quantity: Number(form.get("quantity")), size: "1kg", message: "", add_ons: [] }],
        fulfilment: "delivery", delivery_slot: form.get("slot"), delivery_address: { line1: form.get("address"), city: "Nairobi" } },
    }) }); setOpen(false); await refresh();
  }
  return <section className="recurring-page"><header><div><p>Automate weekly team moments, client birthdays and monthly celebrations.</p></div><button onClick={() => setOpen(!open)}><CalendarClock /> Schedule an order</button></header>{open && <form onSubmit={create}><label>Schedule name<input name="name" required placeholder="Friday team celebration" /></label><label>Cake<select name="product">{products.map(product => <option value={product.slug} key={product.slug}>{product.name}</option>)}</select></label><label>Quantity<input name="quantity" type="number" min="1" max="500" defaultValue="1" /></label><label>Cadence<select name="cadence"><option value="weekly">Every week</option><option value="monthly">Every month</option></select></label><label>First run<input name="next_run_at" type="datetime-local" required /></label><label>Delivery time<input name="slot" required placeholder="Friday, 3:00 PM" /></label><label className="wide">Delivery address<input name="address" required /></label><label>Purchase order<input name="po" /></label><button className="corp-primary">Activate schedule <ArrowRight /></button></form>}<div className="schedule-grid">{items.map(item => <article key={item.id}><span><CalendarClock /></span><small>{item.cadence}</small><h2>{item.name}</h2><p>Next request</p><b>{new Date(item.next_run_at).toLocaleString("en-KE")}</b><footer><i className={item.is_active ? "active" : ""} />{item.is_active ? "Active" : "Paused"}</footer></article>)}</div></section>;
}

function OrderComposer({ products, home, close, saved }: { products: Product[]; home: Home; close: () => void; saved: () => Promise<void> }) {
  const [status, setStatus] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); setStatus("Confirming live stock and pricing…");
    try {
      await api("/v1/corporate/requests", { method: "POST", headers: { "Idempotency-Key": `corporate-${crypto.randomUUID()}` }, body: JSON.stringify({
        title: form.get("title"), purchase_order_number: form.get("po") || null,
        cost_center: form.get("cost_center") || home.membership.cost_center || null,
        items: [{ product_slug: form.get("product"), quantity: Number(form.get("quantity")), size: form.get("size"), message: form.get("message"), add_ons: [] }],
        fulfilment: form.get("fulfilment"), delivery_slot: form.get("slot"),
        delivery_address: { line1: form.get("address"), city: "Nairobi" },
      }) }); await saved();
    } catch (error) { setStatus(error instanceof Error ? error.message : "Request could not be submitted"); }
  }
  return <div className="corp-modal" role="dialog" aria-modal="true"><button className="corp-dismiss" onClick={close} /><section><header><div><p className="corp-eyebrow">New company order</p><h1>Make work feel<br /><em>worth celebrating.</em></h1></div><button onClick={close}><X /></button></header><form onSubmit={submit}><label>Request title<input name="title" required placeholder="Client launch celebration" /></label><label>Purchase order<input name="po" placeholder="PO-2026-001" /></label><label>Cake<select name="product" required>{products.map(product => <option key={product.slug} value={product.slug}>{product.name} · {money(product.price_kes)}</option>)}</select></label><div className="field-pair"><label>Quantity<input name="quantity" type="number" min="1" max="500" defaultValue="1" required /></label><label>Size<select name="size"><option value="1kg">1kg</option><option value="1.5kg">1.5kg</option><option value="2kg">2kg</option></select></label></div><label>Cake message<input name="message" maxLength={32} placeholder="Congratulations, team!" /></label><label>Cost centre<input name="cost_center" defaultValue={home.membership.cost_center} /></label><div className="field-pair"><label>Fulfilment<select name="fulfilment"><option value="delivery">Delivery</option><option value="pickup">Pickup</option></select></label><label>Required time<input name="slot" required placeholder="28 July, 2:00 PM" /></label></div><label>Delivery address<input name="address" required /></label>{status && <p className="corp-form-status">{status}</p>}<button className="corp-primary">Submit for approval <ArrowRight /></button></form></section></div>;
}
