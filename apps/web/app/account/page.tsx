"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, LogOut, MapPin, Package, ShieldCheck, Sparkles } from "lucide-react";
import { api, authenticate, logout, type Customer } from "@/lib/api";

type Mode = "login" | "register";

export default function AccountPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Customer>("/v1/auth/me").then(setCustomer).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Securing your account…");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries([...form.entries()].map(([key, value]) => [key, String(value)]));
    try {
      setCustomer(await authenticate(mode, payload));
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Please try again");
    }
  }

  if (loading) return <main className="account-loading"><span className="offline-mark">CC</span><p>Preparing your Cake City account…</p></main>;
  if (customer) return <AccountHome customer={customer} onLogout={async () => { await logout(); setCustomer(null); }} />;

  return (
    <main className="auth-page">
      <section className="auth-story">
        <a href="/" className="back-link"><ArrowLeft /> Back to Cake City</a>
        <div><p className="eyebrow light">Your celebrations, remembered</p><h1>Every moment.<br /><em>Beautifully kept.</em></h1><p>Reorder favourites, save delivery details and never miss the dates that matter.</p></div>
        <div className="auth-benefits"><span><Sparkles /> Personal recommendations</span><span><Package /> One-tap reorder</span><span><ShieldCheck /> Private and secure</span></div>
      </section>
      <section className="auth-form-wrap">
        <div className="auth-form">
          <p className="eyebrow">{mode === "login" ? "Welcome back" : "Join Cake City"}</p>
          <h2>{mode === "login" ? "Continue your story." : "Make every moment count."}</h2>
          <div className="auth-tabs"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create account</button></div>
          <form onSubmit={submit}>
            {mode === "register" && <div className="field-row"><label>First name<input name="first_name" required autoComplete="given-name" /></label><label>Last name<input name="last_name" autoComplete="family-name" /></label></div>}
            <label>Email address<input name="email" type="email" required autoComplete="email" placeholder="you@example.com" /></label>
            {mode === "register" && <label>Phone number<input name="phone" type="tel" autoComplete="tel" placeholder="+254 7…" /></label>}
            <label>Password<input name="password" type="password" minLength={10} required autoComplete={mode === "login" ? "current-password" : "new-password"} /><small>{mode === "register" && "At least 10 characters"}</small></label>
            {status && <p className="form-status" role="status">{status}</p>}
            <button className="button primary full" disabled={status === "Securing your account…"}>{mode === "login" ? "Sign in securely" : "Create my account"} <ArrowRight /></button>
          </form>
          <p className="privacy-note"><ShieldCheck /> Protected with secure, rotating sessions. We never sell your personal data.</p>
        </div>
      </section>
    </main>
  );
}

function AccountHome({ customer, onLogout }: { customer: Customer; onLogout: () => void }) {
  return <main className="account-home"><header className="account-header"><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a><button onClick={onLogout}><LogOut /> Sign out</button></header><section className="account-welcome"><p className="eyebrow">My Cake City</p><h1>Good to have you here,<br /><em>{customer.first_name}.</em></h1><p>Your next celebration starts right here.</p></section><section className="account-grid"><a href="#"><Package /><span><b>Orders</b><small>Track, reorder and download invoices</small></span><ArrowRight /></a><a href="#"><MapPin /><span><b>Delivery addresses</b><small>Save the places you celebrate</small></span><ArrowRight /></a><a href="#"><Sparkles /><span><b>My moments</b><small>Birthdays and anniversaries</small></span><ArrowRight /></a><a href="#"><span className="points">0</span><span><b>Cake City Rewards</b><small>Earn points with every celebration</small></span><ArrowRight /></a></section><div className="account-secure"><Check /> Signed in securely as {customer.email}</div></main>;
}
