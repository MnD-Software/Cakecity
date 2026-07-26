"use client";

import { useEffect, useState } from "react";
import { Download, RefreshCw, WifiOff, X } from "lucide-react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function PwaShell() {
  const [installPrompt, setInstallPrompt] = useState<InstallPrompt | null>(null);
  const [online, setOnline] = useState(true);
  const [updateReady, setUpdateReady] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setOnline(navigator.onLine);
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    const onInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPrompt);
    };
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("beforeinstallprompt", onInstall);

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").then(registration => {
        registration.addEventListener("updatefound", () => {
          const worker = registration.installing;
          worker?.addEventListener("statechange", () => {
            if (worker.state === "installed" && navigator.serviceWorker.controller) setUpdateReady(true);
          });
        });
      });
    }
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("beforeinstallprompt", onInstall);
    };
  }, []);

  const install = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const result = await installPrompt.userChoice;
    if (result.outcome === "accepted") setInstallPrompt(null);
  };

  return (
    <>
      {!online && <div className="network-status" role="status"><WifiOff /> You’re offline. Saved pages remain available.</div>}
      {updateReady && <button className="update-toast" onClick={() => location.reload()}><RefreshCw /> A fresh Cake City experience is ready. Update</button>}
      {installPrompt && !dismissed && (
        <aside className="install-card" aria-label="Install Cake City app">
          <span className="install-icon">CC</span>
          <span><b>Take Cake City with you</b><small>Install the app for faster ordering and timely updates.</small></span>
          <button className="install-action" onClick={install}><Download /> Install app</button>
          <button className="install-dismiss" onClick={() => setDismissed(true)} aria-label="Dismiss app installation"><X /></button>
        </aside>
      )}
    </>
  );
}
