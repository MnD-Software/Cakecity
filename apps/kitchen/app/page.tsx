"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, ArrowRight, Check, ChefHat, Clock3, Flame,
  LogOut, PackageCheck, RefreshCw, Scale, Sparkles, X,
} from "lucide-react";
import { kitchenApi, kitchenLogin, kitchenLogout, type Staff } from "@/lib/api";

type Ticket = {
  id: string; reference: string; state: string; priority: number; fulfilment: string;
  delivery_slot?: string; customer_name: string; created_at: string; assigned_to?: string;
  checklist: Record<string, boolean>; recipe_snapshot: Record<string, RecipeLine>;
  lines: { name: string; quantity: number; configuration: Record<string, unknown> }[];
};
type RecipeLine = { product: string; quantity: number; configuration?: Record<string, unknown>; recipe?: { name: string; version: number; yield: string; preparation_minutes: number; instructions: string[]; allergens: string[]; ingredients: { name: string; quantity: string; unit: string }[] } };
type Ingredient = { id: string; name: string; unit: string; stock_on_hand: string; reorder_level: string; low_stock: boolean };
const lanes = ["confirmed", "baking", "decorating", "quality_check", "packaging"];
const next: Record<string, string> = { confirmed: "baking", baking: "decorating", decorating: "quality_check", quality_check: "packaging" };
const label = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, char => char.toUpperCase());

export default function KitchenPage() {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => { kitchenApi<Staff>("/v1/auth/me").then(value => { if (["admin", "manager", "kitchen"].includes(value.role)) setStaff(value); }).catch(() => undefined).finally(() => setChecking(false)); }, []);
  if (checking) return <Loading label="Opening today’s production board…" />;
  if (!staff) return <Login onSuccess={setStaff} />;
  return <Kitchen staff={staff} onLogout={async () => { await kitchenLogout(); setStaff(null); }} />;
}

function Kitchen({ staff, onLogout }: { staff: Staff; onLogout: () => void }) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [inventory, setInventory] = useState<Ingredient[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [view, setView] = useState<"queue" | "inventory">("queue");
  const [status, setStatus] = useState("");
  const load = useCallback(async () => {
    const [queue, stock] = await Promise.all([kitchenApi<Ticket[]>("/v1/kitchen/queue"), kitchenApi<Ingredient[]>("/v1/kitchen/inventory")]);
    setTickets(queue); setInventory(stock);
  }, []);
  useEffect(() => { load().catch(error => setStatus(error.message)); const timer = window.setInterval(() => load(), 12000); return () => clearInterval(timer); }, [load]);
  const lowStock = inventory.filter(item => item.low_stock).length;

  async function claim(ticket: Ticket) {
    try { const updated = await kitchenApi<Ticket>(`/v1/kitchen/tickets/${ticket.id}/claim`, { method: "POST" }); setSelected(updated); await load(); setStatus("Ticket is now assigned to you."); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Ticket could not be claimed"); }
  }
  async function saveChecklist(ticket: Ticket, key: string, checked: boolean) {
    const checklist = { ...ticket.checklist, [key]: checked };
    try { await kitchenApi(`/v1/kitchen/tickets/${ticket.id}/checklist`, { method: "PUT", body: JSON.stringify(checklist) }); setSelected({ ...ticket, checklist }); setTickets(current => current.map(item => item.id === ticket.id ? { ...item, checklist } : item)); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Checklist could not be saved"); }
  }
  async function advance(ticket: Ticket) {
    const stage = next[ticket.state]; if (!stage) return;
    try {
      await kitchenApi(`/v1/kitchen/tickets/${ticket.id}/transition`, {
        method: "POST", headers: { "Idempotency-Key": `kitchen-${ticket.id}-${stage}-${crypto.randomUUID()}` },
        body: JSON.stringify({ stage }),
      });
      setStatus(`${ticket.reference} is waiting for WooCommerce to confirm ${label(stage)}.`);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Stage update could not be requested"); }
  }

  return <main className="kitchen-shell">
    <header className="kitchen-header"><div className="kitchen-brand"><span>CAKE CITY</span><b>KITCHEN</b></div><nav><button className={view === "queue" ? "active" : ""} onClick={() => setView("queue")}>Production queue</button><button className={view === "inventory" ? "active" : ""} onClick={() => setView("inventory")}>Inventory {lowStock > 0 && <i>{lowStock}</i>}</button></nav><button className="refresh" onClick={load}><RefreshCw /> Live</button><button className="kitchen-user" onClick={onLogout}><span>{staff.first_name[0]}</span><b>{staff.first_name}</b><LogOut /></button></header>
    {view === "queue" ? <section className="kitchen-page"><div className="kitchen-intro"><div><p className="k-eyebrow">Monday’s production</p><h1>Every cake,<br /><em>beautifully timed.</em></h1></div><div className="queue-pulse"><i /><span><b>{tickets.length} active tickets</b><small>Refreshes every 12 seconds</small></span></div></div>
      <div className="kitchen-board">{lanes.map((lane, laneIndex) => <section className={`kitchen-lane lane-${lane}`} key={lane}><header><span>{String(laneIndex + 1).padStart(2, "0")}</span><div><b>{label(lane)}</b><small>{tickets.filter(item => item.state === lane).length} tickets</small></div></header><div>{tickets.filter(item => item.state === lane).map(ticket => <button className="ticket-card" key={ticket.id} onClick={() => setSelected(ticket)}><div><span className={`priority p${ticket.priority}`}>P{ticket.priority}</span><small>{ticket.reference}</small></div><h2>{ticket.lines.map(line => line.name).join(", ")}</h2><p>{ticket.lines.reduce((sum, line) => sum + line.quantity, 0)} cake{ticket.lines.reduce((sum, line) => sum + line.quantity, 0) === 1 ? "" : "s"} · {ticket.fulfilment}</p><footer><Clock3 /><span>{ticket.delivery_slot || "Time to be confirmed"}</span><ArrowRight /></footer></button>)}</div></section>)}</div>
    </section> : <InventoryView items={inventory} />}
    {selected && <TicketDrawer ticket={selected} mine={selected.assigned_to === staff.id} onClose={() => setSelected(null)} onClaim={() => claim(selected)} onCheck={(key, value) => saveChecklist(selected, key, value)} onAdvance={() => advance(selected)} />}
    {status && <div className="kitchen-toast" role="status">{status}<button onClick={() => setStatus("")}><X /></button></div>}
  </main>;
}

function TicketDrawer({ ticket, mine, onClose, onClaim, onCheck, onAdvance }: { ticket: Ticket; mine: boolean; onClose: () => void; onClaim: () => void; onCheck: (key: string, value: boolean) => void; onAdvance: () => void }) {
  const recipes = Object.values(ticket.recipe_snapshot);
  const allChecked = Object.values(ticket.checklist).every(Boolean);
  return <div className="ticket-overlay" role="dialog" aria-modal="true" aria-label={`Production ticket ${ticket.reference}`}><button className="overlay-dismiss" onClick={onClose} /><aside><header><div><p className="k-eyebrow">Production ticket</p><h1>{ticket.reference}</h1></div><button onClick={onClose}><X /></button></header><div className="ticket-summary"><span><small>Customer</small><b>{ticket.customer_name}</b></span><span><small>Due</small><b>{ticket.delivery_slot || "Confirm time"}</b></span><span><small>Status</small><b>{label(ticket.state)}</b></span></div>
    <section className="order-spec"><p className="k-eyebrow">Order specification</p>{ticket.lines.map(line => <div key={line.name}><span><b>{line.quantity}× {line.name}</b><small>{Object.entries(line.configuration).map(([key, value]) => `${label(key)}: ${String(value)}`).join(" · ")}</small></span></div>)}</section>
    <section className="recipe-reference"><p className="k-eyebrow">Recipe reference</p>{recipes.map(line => <article key={line.product}><ChefHat /><div><h2>{line.recipe?.name || `${line.product} recipe missing`}</h2>{line.recipe ? <><p>Version {line.recipe.version} · {line.recipe.yield} · {line.recipe.preparation_minutes} min</p><div className="ingredient-chips">{line.recipe.ingredients.map(item => <span key={item.name}>{item.quantity} {item.unit} {item.name}</span>)}</div><ol>{line.recipe.instructions.map(step => <li key={step}>{step}</li>)}</ol>{line.recipe.allergens.length > 0 && <small className="allergens"><AlertTriangle /> Allergens: {line.recipe.allergens.join(", ")}</small>}</> : <p className="missing-recipe"><AlertTriangle /> Escalate before production.</p>}</div></article>)}</section>
    <section className="quality-list"><p className="k-eyebrow">Quality controls</p>{Object.entries(ticket.checklist).map(([key, checked]) => <label key={key}><input type="checkbox" checked={checked} onChange={event => onCheck(key, event.target.checked)} /><span>{checked ? <Check /> : null}</span>{label(key)}</label>)}</section>
    <footer className="drawer-actions">{!ticket.assigned_to && <button className="claim-action" onClick={onClaim}>Claim this ticket</button>}{ticket.assigned_to && next[ticket.state] && <button className="advance-action" disabled={!mine || (next[ticket.state] === "packaging" && !allChecked)} onClick={onAdvance}>{next[ticket.state] === "packaging" ? <PackageCheck /> : <Sparkles />} Move to {label(next[ticket.state])}<ArrowRight /></button>}</footer>
  </aside></div>;
}

function InventoryView({ items }: { items: Ingredient[] }) {
  const low = items.filter(item => item.low_stock);
  return <section className="inventory-page"><div className="kitchen-intro"><div><p className="k-eyebrow">Ingredient control</p><h1>Stock with<br /><em>no surprises.</em></h1></div><div className={low.length ? "stock-alert danger" : "stock-alert"}>{low.length ? <AlertTriangle /> : <Check />}<span><b>{low.length ? `${low.length} ingredients need attention` : "Every level looks healthy"}</b><small>Based on live reorder thresholds</small></span></div></div><div className="inventory-grid">{items.map(item => { const percent = Math.min(100, Number(item.stock_on_hand) / Math.max(Number(item.reorder_level) * 2, 1) * 100); return <article className={item.low_stock ? "low" : ""} key={item.id}><span>{item.low_stock ? <AlertTriangle /> : <Scale />}</span><small>{item.unit}</small><h2>{item.name}</h2><strong>{Number(item.stock_on_hand).toLocaleString()} <em>{item.unit}</em></strong><div><i style={{ width: `${percent}%` }} /></div><p>Reorder at {Number(item.reorder_level).toLocaleString()} {item.unit}</p></article>; })}</div></section>;
}

function Login({ onSuccess }: { onSuccess: (staff: Staff) => void }) {
  const [status, setStatus] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); setStatus("Opening today’s kitchen…"); try { onSuccess(await kitchenLogin(String(form.get("email")), String(form.get("password")))); } catch (error) { setStatus(error instanceof Error ? error.message : "Access denied"); } }
  return <main className="kitchen-login"><section><div className="kitchen-brand light"><span>CAKE CITY</span><b>KITCHEN</b></div><Flame /><h1>Craft,<br /><em>in perfect rhythm.</em></h1><p>One calm production board from confirmation to the final quality check.</p></section><section><form onSubmit={submit}><span className="login-icon"><ChefHat /></span><p className="k-eyebrow">Team access</p><h2>Ready to create?</h2><label>Email<input name="email" type="email" required /></label><label>Password<input name="password" type="password" required /></label>{status && <p className="login-status">{status}</p>}<button>Enter the kitchen <ArrowRight /></button></form></section></main>;
}

function Loading({ label: text }: { label: string }) { return <main className="kitchen-loading"><span><ChefHat /></span><p>{text}</p></main>; }
