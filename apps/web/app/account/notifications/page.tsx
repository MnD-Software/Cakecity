"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Bell, BellRing, Check, Mail, MessageCircle, Smartphone } from "lucide-react";
import { api } from "@/lib/api";

type Notice = { id: string; title: string; body: string; data: { url?: string }; read_at?: string; created_at: string };
type Preferences = { in_app: boolean; email: boolean; push: boolean; sms: boolean; whatsapp: boolean };
const defaults: Preferences = { in_app: true, email: true, push: false, sms: false, whatsapp: false };

function urlBase64ToUint8Array(value: string) {
  const padding = "=".repeat((4 - value.length % 4) % 4);
  const raw = atob((value + padding).replaceAll("-", "+").replaceAll("_", "/"));
  return Uint8Array.from([...raw].map(character => character.charCodeAt(0)));
}

export default function NotificationsPage() {
  const [items, setItems] = useState<Notice[]>([]);
  const [prefs, setPrefs] = useState<Preferences>(defaults);
  const [status, setStatus] = useState("");
  useEffect(() => {
    Promise.all([api<Notice[]>("/v1/account/notifications"), api<Preferences>("/v1/account/notifications/preferences")])
      .then(([notices, preferences]) => { setItems(notices); setPrefs(preferences); })
      .catch(error => setStatus(error.message));
  }, []);

  async function save(next: Preferences) {
    setPrefs(next); setStatus("Saving your choices…");
    try { await api("/v1/account/notifications/preferences", { method: "PUT", body: JSON.stringify(next) }); setStatus("Preferences saved."); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Could not save preferences"); }
  }

  async function enablePush() {
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) throw new Error("Push notifications are not supported on this device.");
      const config = await api<{ enabled: boolean; public_key: string }>("/v1/account/notifications/push/config");
      if (!config.enabled) throw new Error("Device notifications will be available when the production VAPID key is configured.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("Notification permission was not granted.");
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(config.public_key) });
      await api("/v1/account/notifications/push/subscriptions", { method: "POST", body: JSON.stringify(subscription.toJSON()) });
      setPrefs(current => ({ ...current, push: true })); setStatus("Device notifications are on.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not enable device notifications"); }
  }

  async function open(item: Notice) {
    if (!item.read_at) {
      await api(`/v1/account/notifications/${item.id}/read`, { method: "POST" });
      setItems(current => current.map(value => value.id === item.id ? { ...value, read_at: new Date().toISOString() } : value));
    }
    if (item.data.url) location.assign(item.data.url);
  }

  return <main className="post-page">
    <header className="account-header"><a className="back-link" href="/account"><ArrowLeft /> My account</a><a className="brand" href="/"><span>CAKE</span><span>CITY</span></a></header>
    <section className="post-hero compact"><p className="eyebrow">Never miss the moment</p><h1>Your Cake City<br /><em>updates.</em></h1></section>
    <section className="notification-layout">
      <div className="notification-feed"><h2>Latest updates</h2>{items.length === 0 && <div className="notice-empty"><Bell /><p>Your order and celebration updates will appear here.</p></div>}{items.map(item => <button className={item.read_at ? "notice read" : "notice"} onClick={() => open(item)} key={item.id}><span><BellRing /></span><div><b>{item.title}</b><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString("en-KE")}</small></div>{!item.read_at && <i />}</button>)}</div>
      <aside className="preference-card"><p className="eyebrow">How we reach you</p><h2>Choose every channel.</h2>
        <Preference icon={<Bell />} label="In-app updates" checked={prefs.in_app} onChange={value => save({ ...prefs, in_app: value })} />
        <Preference icon={<Mail />} label="Email" checked={prefs.email} onChange={value => save({ ...prefs, email: value })} />
        <Preference icon={<MessageCircle />} label="SMS" note="Provider-ready" checked={prefs.sms} onChange={value => save({ ...prefs, sms: value })} />
        <Preference icon={<MessageCircle />} label="WhatsApp" note="Provider-ready" checked={prefs.whatsapp} onChange={value => save({ ...prefs, whatsapp: value })} />
        <button className="push-action" onClick={enablePush}><Smartphone /><span><b>{prefs.push ? "Device notifications on" : "Enable device notifications"}</b><small>Get live order updates even when the app is closed.</small></span>{prefs.push && <Check />}</button>
        {status && <p className="form-status" role="status">{status}</p>}
      </aside>
    </section>
  </main>;
}

function Preference({ icon, label, note, checked, onChange }: { icon: React.ReactNode; label: string; note?: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="preference-row"><span>{icon}</span><b>{label}{note && <small>{note}</small>}</b><input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} /><i /></label>;
}
