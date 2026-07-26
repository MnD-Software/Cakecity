"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CakeSlice, Package } from "lucide-react";
import { api } from "@/lib/api";

type Order = { reference: string; state: string; total: string; currency: string; fulfilment: string; delivery_slot?: string; created_at: string };
const label = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Order[]>("/v1/account/orders").then(setOrders).catch(error => setError(error.message)); }, []);
  return <main className="post-page">
    <header className="account-header"><a className="back-link" href="/account"><ArrowLeft /> My account</a><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a></header>
    <section className="post-hero"><p className="eyebrow">Made for your moments</p><h1>Your orders,<br /><em>beautifully kept.</em></h1><p>Follow every cake from our kitchen to your celebration, then reorder whenever the moment calls.</p></section>
    <section className="orders-list">
      {error && <div className="post-empty"><Package /><h2>Sign in to see your orders</h2><p>{error}</p><a className="button primary" href="/account">Go to account</a></div>}
      {!orders && !error && <p className="loading-line">Gathering your celebrations…</p>}
      {orders?.length === 0 && <div className="post-empty"><CakeSlice /><h2>Your first celebration awaits.</h2><p>When you place an order, its live journey will appear here.</p><a className="button primary" href="/">Explore cakes</a></div>}
      {orders?.map(order => <a className="order-card" key={order.reference} href={`/account/orders/${order.reference}`}>
        <span className="order-mark"><Package /></span><span><small>{new Date(order.created_at).toLocaleDateString("en-KE", { day: "numeric", month: "long", year: "numeric" })}</small><b>{order.reference}</b><em>{label(order.state)}</em></span><span className="order-total">{order.currency} {Number(order.total).toLocaleString()}<ArrowRight /></span>
      </a>)}
    </section>
  </main>;
}
