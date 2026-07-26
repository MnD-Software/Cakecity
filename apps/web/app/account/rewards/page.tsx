"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Award, Check, Copy, Crown, Gift, Sparkles, WalletCards } from "lucide-react";
import { api } from "@/lib/api";

type Overview = {
  points_balance: number; lifetime_points: number; lifetime_spend: string; tier: string; benefits: string[];
  next_tier?: { name: string; spend_required: string }; wallet: { balance: string; currency: string };
  referral: { code: string; completed: number; reward_points: number };
};
type Activity = { points: { id: string; points: number; description: string; created_at: string }[] };

export default function RewardsPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [activity, setActivity] = useState<Activity>({ points: [] });
  const [status, setStatus] = useState("");
  const load = () => Promise.all([api<Overview>("/v1/account/rewards"), api<Activity>("/v1/account/rewards/activity")]).then(([summary, history]) => { setOverview(summary); setActivity(history); });
  useEffect(() => { load().catch(error => setStatus(error.message)); }, []);

  async function redeem(points: number) {
    setStatus("Converting your points…");
    try {
      await api("/v1/account/rewards/redeem", { method: "POST", headers: { "Idempotency-Key": `rewards-${crypto.randomUUID()}` }, body: JSON.stringify({ points }) });
      await load(); setStatus("Cake City credit added to your wallet.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Redemption could not be completed"); }
  }

  async function applyReferral(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const code = String(new FormData(event.currentTarget).get("code") || "");
    try { const result = await api<{ message: string }>("/v1/account/rewards/referrals/apply", { method: "POST", body: JSON.stringify({ code }) }); setStatus(result.message); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Code could not be applied"); }
  }

  if (!overview) return <main className="post-page"><div className="post-empty"><Award /><h2>{status || "Opening your rewards…"}</h2><a href="/account">Back to account</a></div></main>;
  const tierProgress = overview.next_tier ? Math.min(100, Number(overview.lifetime_spend) / (Number(overview.lifetime_spend) + Number(overview.next_tier.spend_required)) * 100) : 100;
  return <main className="post-page rewards-page">
    <header className="account-header"><a className="back-link" href="/account"><ArrowLeft /> My account</a><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a></header>
    <section className="reward-hero"><div><p className="eyebrow light">Cake City Rewards</p><h1>Your celebrations<br /><em>give back.</em></h1><p>Every delivered order moves you closer to more beautiful benefits.</p></div><div className="tier-orbit"><Crown /><small>Current membership</small><strong>{overview.tier}</strong><span>{overview.points_balance.toLocaleString()} points</span></div></section>
    <section className="reward-grid">
      <article className="reward-card wallet-card"><WalletCards /><small>Available Cake City credit</small><h2>{overview.wallet.currency} {Number(overview.wallet.balance).toLocaleString()}</h2><p>Use your credit as a secure payment method at checkout.</p>{overview.points_balance >= 500 && <button className="button primary" onClick={() => redeem(Math.floor(overview.points_balance / 100) * 100)}>Convert eligible points</button>}</article>
      <article className="reward-card"><Sparkles /><small>Your progress</small><h2>{overview.next_tier ? `${overview.next_tier.name} is within reach` : "The highest tier is yours"}</h2><div className="tier-progress"><i style={{ width: `${tierProgress}%` }} /></div><p>{overview.next_tier ? `Spend KES ${Number(overview.next_tier.spend_required).toLocaleString()} more to unlock it.` : "Enjoy every Platinum benefit."}</p></article>
      <article className="reward-card benefit-card"><Gift /><small>{overview.tier} benefits</small>{overview.benefits.map(item => <p key={item}><Check /> {item}</p>)}</article>
      <article className="reward-card referral-card"><Award /><small>Invite a friend</small><h2>{overview.referral.code}</h2><button onClick={() => { navigator.clipboard.writeText(overview.referral.code); setStatus("Referral code copied."); }}><Copy /> Copy code</button><p>You receive {overview.referral.reward_points} points after their first delivered order. Completed referrals: {overview.referral.completed}.</p><form onSubmit={applyReferral}><input name="code" placeholder="Have a referral code?" /><button>Apply</button></form></article>
    </section>
    <section className="reward-history"><p className="eyebrow">Points activity</p><h2>Every reward, accounted for.</h2>{activity.points.length === 0 && <p>No activity yet. Your first delivered order starts the story.</p>}{activity.points.map(item => <div key={item.id}><span><b>{item.description}</b><small>{new Date(item.created_at).toLocaleDateString("en-KE")}</small></span><strong className={item.points > 0 ? "positive" : ""}>{item.points > 0 ? "+" : ""}{item.points}</strong></div>)}</section>
    {status && <div className="reward-toast" role="status">{status}</div>}
  </main>;
}
