"use client";

import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import {
  Activity, ArrowRight, BarChart3, BellRing, Building2, CheckCircle2, ChevronDown, CircleDollarSign,
  ContactRound, Crown, Gauge, LogOut, Megaphone, Menu, Plus, Search, ShieldCheck,
  Sparkles, UsersRound, X,
} from "lucide-react";
import { adminApi, staffLogin, staffLogout, type Staff } from "@/lib/api";

type View = "overview" | "customers" | "corporate" | "crm" | "campaigns" | "analytics" | "audit";
type Overview = {
  revenue_30d: string; revenue_change_percent: string; orders_30d: number;
  average_order_value: string; customers: number; repeat_purchase_rate: number;
  completed_referrals: number; open_pipeline_value: string;
};
type Lead = { id: string; name: string; email: string; phone?: string; source: string; stage: string; estimated_value: string; next_action_at?: string };
type Campaign = { id: string; name: string; channel: string; audience_segment: string; subject: string; state: string; scheduled_at?: string; audience_count: number; delivered_count: number };
type Customer = { id: string; name: string; email: string; phone?: string; tier: string; lifetime_spend: string; created_at: string };
type AuditItem = { id: string; action: string; target_type: string; target_id: string; changes: Record<string, unknown>; ip_address?: string; created_at: string };
type RevenuePoint = { date: string; revenue: string; orders: number };
type ProductPoint = { name: string; units: number; revenue: string };
type Retention = { tiers: Record<string, number>; points_issued: number; points_redeemed: number; referrals_total: number; referrals_completed: number; referral_conversion_rate: number; completed_campaigns: number; campaign_dispatches: number };
type CorporateAccount = { id: string; name: string; billing_email: string; credit_limit: string; outstanding: string; payment_terms_days: number; state: string; members: number };

const nav: { id: View; label: string; icon: ReactNode }[] = [
  { id: "overview", label: "Command centre", icon: <Gauge /> },
  { id: "customers", label: "Customers", icon: <UsersRound /> },
  { id: "corporate", label: "Corporate", icon: <Building2 /> },
  { id: "crm", label: "CRM pipeline", icon: <ContactRound /> },
  { id: "campaigns", label: "Campaigns", icon: <Megaphone /> },
  { id: "analytics", label: "Analytics", icon: <BarChart3 /> },
  { id: "audit", label: "Audit trail", icon: <ShieldCheck /> },
];
const stages = ["new", "contacted", "qualified", "proposal", "won", "lost"];
const money = (value: string | number) => `KES ${Number(value).toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
const label = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());

export default function AdminPage() {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>("overview");
  const [menu, setMenu] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    adminApi<Staff>("/v1/auth/me").then(result => {
      if (["admin", "manager", "marketing", "support"].includes(result.role)) setStaff(result);
    }).catch(() => undefined).finally(() => setChecking(false));
  }, []);

  if (checking) return <main className="admin-loading"><span>CC</span><p>Securing Cake City Command…</p></main>;
  if (!staff) return <Login onSuccess={setStaff} />;
  const visibleNav = nav.filter(item =>
    (item.id !== "campaigns" || ["admin", "manager", "marketing"].includes(staff.role)) &&
    (item.id !== "audit" || ["admin", "manager"].includes(staff.role))
  );

  return <div className="admin-shell">
    <aside className={menu ? "admin-sidebar open" : "admin-sidebar"}>
      <button className="side-close" onClick={() => setMenu(false)} aria-label="Close navigation"><X /></button>
      <div className="command-brand"><span>CAKE CITY</span><b>COMMAND</b></div>
      <p className="side-label">Workspace</p>
      <nav>{visibleNav.map(item => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => { setView(item.id); setMenu(false); }}>{item.icon}<span>{item.label}</span></button>)}</nav>
      <div className="side-health"><i /><span><b>Systems operational</b><small>Commerce authority connected</small></span></div>
      <button className="staff-card" onClick={async () => { await staffLogout(); setStaff(null); }}><span>{staff.first_name[0]}</span><span><b>{staff.first_name} {staff.last_name}</b><small>{label(staff.role)}</small></span><LogOut /></button>
    </aside>
    <main className="admin-main">
      <header className="admin-topbar"><button className="menu-button" onClick={() => setMenu(true)}><Menu /></button><div><small>{new Date().toLocaleDateString("en-KE", { weekday: "long", day: "numeric", month: "long" })}</small><b>Good to see you, {staff.first_name}.</b></div><button className="admin-alert"><BellRing /><i /></button></header>
      {view === "overview" && <OverviewView setView={setView} />}
      {view === "customers" && <CustomersView />}
      {view === "corporate" && <CorporateView setStatus={setStatus} canManage={["admin", "manager"].includes(staff.role)} />}
      {view === "crm" && <CRMView status={status} setStatus={setStatus} />}
      {view === "campaigns" && <CampaignsView status={status} setStatus={setStatus} />}
      {view === "analytics" && <AnalyticsView />}
      {view === "audit" && <AuditView />}
      {status && <div className="admin-toast" role="status">{status}<button onClick={() => setStatus("")}><X /></button></div>}
    </main>
  </div>;
}

function Login({ onSuccess }: { onSuccess: (staff: Staff) => void }) {
  const [status, setStatus] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setStatus("Verifying staff access…");
    const form = new FormData(event.currentTarget);
    try { onSuccess(await staffLogin(String(form.get("email")), String(form.get("password")))); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Access could not be verified"); }
  }
  return <main className="admin-login"><section><div className="command-brand light"><span>CAKE CITY</span><b>COMMAND</b></div><div><p className="admin-eyebrow">The operating system for celebration</p><h1>Clarity for<br /><em>every decision.</em></h1><p>Customers, revenue, relationships and campaigns in one secure command centre.</p></div><div className="login-proof"><span><ShieldCheck /> Role-secured access</span><span><Activity /> Every change audited</span></div></section><section><form onSubmit={submit}><span className="login-mark">CC</span><p className="admin-eyebrow">Staff access</p><h2>Welcome back.</h2><label>Email address<input name="email" type="email" required autoComplete="email" /></label><label>Password<input name="password" type="password" required autoComplete="current-password" /></label>{status && <p className="login-status">{status}</p>}<button>Enter Cake City Command <ArrowRight /></button><small>Only authorised Cake City team members may continue.</small></form></section></main>;
}

function PageHeader({ eyebrow, title, action }: { eyebrow: string; title: string; action?: ReactNode }) {
  return <div className="page-heading"><div><p className="admin-eyebrow">{eyebrow}</p><h1>{title}</h1></div>{action}</div>;
}

function OverviewView({ setView }: { setView: (view: View) => void }) {
  const [data, setData] = useState<Overview | null>(null);
  useEffect(() => { adminApi<Overview>("/v1/admin/overview").then(setData); }, []);
  if (!data) return <Loading />;
  return <section className="admin-page"><PageHeader eyebrow="Live business pulse" title="Command centre" action={<button className="quiet-action" onClick={() => setView("analytics")}>Explore analytics <ArrowRight /></button>} />
    <div className="metric-grid">
      <Metric icon={<CircleDollarSign />} label="Revenue · 30 days" value={money(data.revenue_30d)} note={`${Number(data.revenue_change_percent) >= 0 ? "+" : ""}${data.revenue_change_percent}% vs previous`} featured />
      <Metric icon={<Sparkles />} label="Average order value" value={money(data.average_order_value)} note={`${data.orders_30d} paid orders`} />
      <Metric icon={<UsersRound />} label="Active customers" value={data.customers.toLocaleString()} note={`${data.repeat_purchase_rate}% repeat purchase`} />
      <Metric icon={<ContactRound />} label="Open CRM pipeline" value={money(data.open_pipeline_value)} note={`${data.completed_referrals} completed referrals`} />
    </div>
    <div className="command-grid"><article className="focus-card"><p className="admin-eyebrow">Today’s focus</p><h2>Turn customer intention<br />into the next celebration.</h2><div><span><b>01</b><small>Work qualified CRM opportunities</small></span><button onClick={() => setView("crm")}>Open pipeline <ArrowRight /></button></div><div><span><b>02</b><small>Reach customers with precise segments</small></span><button onClick={() => setView("campaigns")}>Build campaign <ArrowRight /></button></div></article><article className="north-star"><Crown /><p className="admin-eyebrow">Revenue ambition</p><h2>KES 70M</h2><p>Annual platform north star</p><div><i style={{ width: "48%" }} /></div><small>Technology, retention and remarkable service move this line.</small></article></div>
  </section>;
}

function Metric({ icon, label: name, value, note, featured }: { icon: ReactNode; label: string; value: string; note: string; featured?: boolean }) {
  return <article className={featured ? "metric featured" : "metric"}><span>{icon}</span><small>{name}</small><strong>{value}</strong><p>{note}</p></article>;
}

function CustomersView() {
  const [items, setItems] = useState<Customer[]>([]);
  const [segment, setSegment] = useState("all");
  const [search, setSearch] = useState("");
  const load = useCallback(() => adminApi<Customer[]>(`/v1/admin/customers?segment=${segment}&search=${encodeURIComponent(search)}`).then(setItems), [segment, search]);
  useEffect(() => { load(); }, [load]);
  return <section className="admin-page"><PageHeader eyebrow="Customer intelligence" title="Know every relationship" />
    <div className="table-tools"><div className="segment-tabs">{["all", "new", "repeat", "vip", "lapsed", "birthday_upcoming"].map(item => <button className={segment === item ? "active" : ""} key={item} onClick={() => setSegment(item)}>{label(item)}</button>)}</div><label className="admin-search"><Search /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search customer" /></label></div>
    <div className="data-table"><div className="table-row head"><span>Customer</span><span>Membership</span><span>Lifetime value</span><span>Joined</span></div>{items.map(item => <div className="table-row" key={item.id}><span><b>{item.name}</b><small>{item.email}</small></span><span><i className={`tier ${item.tier}`} />{label(item.tier)}</span><strong>{money(item.lifetime_spend)}</strong><span>{new Date(item.created_at).toLocaleDateString("en-KE")}</span></div>)}{items.length === 0 && <div className="empty-data">No customers match this segment.</div>}</div>
  </section>;
}

function CorporateView({ setStatus, canManage }: { setStatus: (value: string) => void; canManage: boolean }) {
  const [items, setItems] = useState<CorporateAccount[]>([]);
  const [creating, setCreating] = useState(false);
  const [memberAccount, setMemberAccount] = useState<CorporateAccount | null>(null);
  const load = () => adminApi<CorporateAccount[]>("/v1/corporate/admin/accounts").then(setItems);
  useEffect(() => { load(); }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    await adminApi("/v1/corporate/admin/accounts", { method: "POST", body: JSON.stringify({
      name: form.get("name"), billing_email: form.get("billing_email"), phone: form.get("phone") || null,
      tax_pin: form.get("tax_pin") || null, credit_limit: Number(form.get("credit_limit")),
      approval_threshold: Number(form.get("approval_threshold") || 0),
      payment_terms_days: Number(form.get("payment_terms_days")), billing_address: {},
    }) }); await load(); setCreating(false); setStatus("Corporate account created and audited.");
  }
  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!memberAccount) return; const form = new FormData(event.currentTarget);
    await adminApi(`/v1/corporate/admin/accounts/${memberAccount.id}/members`, { method: "POST", body: JSON.stringify({
      email: form.get("email"), role: form.get("role"),
      spend_limit: form.get("spend_limit") ? Number(form.get("spend_limit")) : null,
      cost_center: form.get("cost_center") || null,
    }) }); await load(); setMemberAccount(null); setStatus("Corporate member access granted and audited.");
  }
  return <section className="admin-page"><PageHeader eyebrow="Business accounts" title="Corporate partnerships" action={canManage && <button className="primary-action" onClick={() => setCreating(true)}><Plus /> New company</button>} />
    <div className="data-table"><div className="table-row head"><span>Company</span><span>Credit facility</span><span>Outstanding</span><span>Team</span></div>{items.map(item => <button className="table-row corporate-row" key={item.id} disabled={!canManage} onClick={() => canManage && setMemberAccount(item)}><span><b>{item.name}</b><small>{item.billing_email} · {item.payment_terms_days}-day terms</small></span><strong>{money(item.credit_limit)}</strong><span>{money(item.outstanding)}</span><span>{item.members} members {canManage && <Plus />}</span></button>)}{items.length === 0 && <div className="empty-data">Create the first managed corporate account.</div>}</div>
    {creating && <Modal title="Create a corporate account" onClose={() => setCreating(false)}><form className="admin-form" onSubmit={create}><label>Company name<input name="name" required autoFocus /></label><label>Billing email<input name="billing_email" type="email" required /></label><div className="form-row"><label>Phone<input name="phone" /></label><label>KRA PIN<input name="tax_pin" /></label></div><div className="form-row"><label>Credit limit (KES)<input name="credit_limit" type="number" min="0" required /></label><label>Approval threshold<input name="approval_threshold" type="number" min="0" defaultValue="0" /></label></div><label>Payment terms (days)<input name="payment_terms_days" type="number" min="0" max="120" defaultValue="30" /></label><button className="primary-action">Create managed account</button></form></Modal>}
    {memberAccount && <Modal title={`Add ${memberAccount.name} member`} onClose={() => setMemberAccount(null)}><form className="admin-form" onSubmit={addMember}><label>Existing customer email<input name="email" type="email" required autoFocus /></label><div className="form-row"><label>Access role<select name="role"><option value="requester">Requester</option><option value="approver">Approver</option><option value="admin">Company admin</option></select></label><label>Spend limit<input name="spend_limit" type="number" min="0" /></label></div><label>Cost centre<input name="cost_center" placeholder="Marketing, People, Executive…" /></label><button className="primary-action">Grant company access</button></form></Modal>}
  </section>;
}

function CRMView({ status, setStatus }: { status: string; setStatus: (value: string) => void }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [creating, setCreating] = useState(false);
  const load = () => adminApi<Lead[]>("/v1/admin/crm/leads").then(setLeads);
  useEffect(() => { load(); }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    await adminApi("/v1/admin/crm/leads", { method: "POST", body: JSON.stringify({
      name: form.get("name"), email: form.get("email"), phone: form.get("phone") || null,
      source: form.get("source"), estimated_value: Number(form.get("estimated_value") || 0),
    }) }); await load(); setCreating(false); setStatus("CRM opportunity created and audited.");
  }
  async function advance(lead: Lead) {
    const index = stages.indexOf(lead.stage); if (index < 0 || index >= stages.length - 2) return;
    const next = stages[index + 1];
    await adminApi(`/v1/admin/crm/leads/${lead.id}/stage`, { method: "PATCH", body: JSON.stringify({ stage: next, note: `Advanced to ${next} from Cake City Command` }) });
    await load(); setStatus(`${lead.name} moved to ${label(next)}.`);
  }
  return <section className="admin-page"><PageHeader eyebrow="Relationship pipeline" title="CRM opportunities" action={<button className="primary-action" onClick={() => setCreating(true)}><Plus /> New opportunity</button>} />
    <div className="pipeline">{stages.slice(0, 5).map(stage => <section className="pipeline-column" key={stage}><header><span>{label(stage)}</span><b>{leads.filter(item => item.stage === stage).length}</b></header>{leads.filter(item => item.stage === stage).map(lead => <article key={lead.id}><small>{lead.source}</small><h3>{lead.name}</h3><p>{lead.email}</p><strong>{money(lead.estimated_value)}</strong>{!["won", "lost"].includes(lead.stage) && <button onClick={() => advance(lead)}>Move forward <ArrowRight /></button>}</article>)}</section>)}</div>
    {creating && <Modal title="A new opportunity" onClose={() => setCreating(false)}><form className="admin-form" onSubmit={create}><label>Name<input name="name" required autoFocus /></label><label>Email<input name="email" type="email" required /></label><div className="form-row"><label>Phone<input name="phone" /></label><label>Source<select name="source"><option>manual</option><option>website</option><option>corporate</option><option>referral</option><option>instagram</option></select></label></div><label>Estimated value (KES)<input name="estimated_value" type="number" min="0" /></label><button className="primary-action">Create opportunity</button></form></Modal>}
  </section>;
}

function CampaignsView({ status, setStatus }: { status: string; setStatus: (value: string) => void }) {
  const [items, setItems] = useState<Campaign[]>([]);
  const [creating, setCreating] = useState(false);
  const load = () => adminApi<Campaign[]>("/v1/admin/campaigns").then(setItems);
  useEffect(() => { load(); }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const campaign = await adminApi<Campaign>("/v1/admin/campaigns", { method: "POST", body: JSON.stringify({
      name: form.get("name"), channel: form.get("channel"), audience_segment: form.get("audience_segment"),
      subject: form.get("subject"), message: form.get("message"), call_to_action_url: form.get("call_to_action_url") || "/",
    }) }); await adminApi(`/v1/admin/campaigns/${campaign.id}/schedule`, { method: "POST", body: JSON.stringify({ scheduled_at: new Date().toISOString() }) });
    await load(); setCreating(false); setStatus("Campaign approved, scheduled and recorded in the audit trail.");
  }
  return <section className="admin-page"><PageHeader eyebrow="Precision growth" title="Campaign studio" action={<button className="primary-action" onClick={() => setCreating(true)}><Plus /> Create campaign</button>} />
    <div className="campaign-list">{items.map(item => <article key={item.id}><span className={`channel ${item.channel}`}><Megaphone /></span><div><small>{label(item.audience_segment)} · {label(item.channel)}</small><h2>{item.name}</h2><p>{item.subject}</p></div><div className="campaign-progress"><span><b>{item.delivered_count}</b><small>Dispatched</small></span><span><b>{item.audience_count}</b><small>Audience</small></span></div><em className={`state ${item.state}`}>{label(item.state)}</em></article>)}{items.length === 0 && <div className="empty-data">No campaigns yet. Start with one precise customer segment.</div>}</div>
    {creating && <Modal title="Create a precise campaign" onClose={() => setCreating(false)}><form className="admin-form" onSubmit={create}><label>Campaign name<input name="name" required autoFocus /></label><div className="form-row"><label>Channel<select name="channel"><option value="in_app">In-app</option><option value="email">Email</option><option value="push">Push</option></select></label><label>Audience<select name="audience_segment"><option value="repeat">Repeat customers</option><option value="vip">VIP customers</option><option value="lapsed">Lapsed customers</option><option value="birthday_upcoming">Upcoming birthdays</option><option value="new">New customers</option><option value="all">All customers</option></select></label></div><label>Subject<input name="subject" required /></label><label>Message<textarea name="message" required rows={4} /></label><label>Call-to-action path<input name="call_to_action_url" defaultValue="/" /></label><button className="primary-action">Approve and launch</button></form></Modal>}
  </section>;
}

function AnalyticsView() {
  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [products, setProducts] = useState<ProductPoint[]>([]);
  const [retention, setRetention] = useState<Retention | null>(null);
  useEffect(() => { Promise.all([adminApi<RevenuePoint[]>("/v1/admin/analytics/revenue"), adminApi<ProductPoint[]>("/v1/admin/analytics/products"), adminApi<Retention>("/v1/admin/analytics/retention")]).then(([series, items, metrics]) => { setRevenue(series); setProducts(items); setRetention(metrics); }); }, []);
  const max = Math.max(1, ...revenue.map(item => Number(item.revenue)));
  return <section className="admin-page"><PageHeader eyebrow="Evidence over instinct" title="Performance analytics" />
    {retention && <div className="retention-strip"><div><small>Points issued</small><b>{retention.points_issued.toLocaleString()}</b></div><div><small>Points redeemed</small><b>{retention.points_redeemed.toLocaleString()}</b></div><div><small>Referral conversion</small><b>{retention.referral_conversion_rate}%</b></div><div><small>Campaign dispatches</small><b>{retention.campaign_dispatches.toLocaleString()}</b></div></div>}
    <div className="analytics-grid"><article className="revenue-chart"><header><div><small>Daily revenue</small><h2>Last 30 days</h2></div><BarChart3 /></header><div className="bars">{revenue.map(item => <span key={item.date} title={`${item.date}: ${money(item.revenue)}`}><i style={{ height: `${Math.max(4, Number(item.revenue) / max * 100)}%` }} /></span>)}</div></article><article className="product-ranking"><small>Product performance</small><h2>Revenue leaders</h2>{products.map((item, index) => <div key={item.name}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{item.name}</strong><small>{item.units} units</small></span><em>{money(item.revenue)}</em></div>)}</article></div>
  </section>;
}

function AuditView() {
  const [items, setItems] = useState<AuditItem[]>([]);
  useEffect(() => { adminApi<AuditItem[]>("/v1/admin/audit").then(setItems); }, []);
  return <section className="admin-page"><PageHeader eyebrow="Accountability by design" title="Audit trail" />
    <div className="audit-list">{items.map(item => <article key={item.id}><span><CheckCircle2 /></span><div><b>{label(item.action.replaceAll(".", " "))}</b><p>{label(item.target_type)} · {item.target_id}</p><small>{new Date(item.created_at).toLocaleString("en-KE")} {item.ip_address && `· ${item.ip_address}`}</small></div><button><ChevronDown /></button></article>)}{items.length === 0 && <div className="empty-data">Audited staff changes will appear here.</div>}</div>
  </section>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return <div className="admin-overlay" role="dialog" aria-modal="true" aria-label={title}><button className="overlay-dismiss" onClick={onClose} /><section><header><div><p className="admin-eyebrow">Cake City Command</p><h2>{title}</h2></div><button onClick={onClose}><X /></button></header>{children}</section></div>;
}

function Loading() {
  return <div className="admin-loading inline"><span>CC</span><p>Reading the live business pulse…</p></div>;
}
