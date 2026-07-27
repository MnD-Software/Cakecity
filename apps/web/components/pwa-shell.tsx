"use client";

import { useEffect, useState } from "react";
import { Download, Plus, RefreshCw, Share, WifiOff, X } from "lucide-react";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export function PwaShell() {
  const [installPrompt, setInstallPrompt] = useState<InstallPrompt | null>(null);
  const [online, setOnline] = useState(true);
  const [updateReady, setUpdateReady] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [iosInstall, setIosInstall] = useState<"safari" | "other" | null>(null);
  const [iosHelpOpen, setIosHelpOpen] = useState(false);

  useEffect(() => {
    setOnline(navigator.onLine);
    const appleMobile = /iphone|ipad|ipod/i.test(navigator.userAgent)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const standalone = window.matchMedia("(display-mode: standalone)").matches
      || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
    const safari = /safari/i.test(navigator.userAgent) && !/crios|fxios|edgios/i.test(navigator.userAgent);
    if (appleMobile && !standalone && localStorage.getItem("cakecity-ios-install-dismissed") !== "1") {
      setIosInstall(safari ? "safari" : "other");
    }
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

  const dismissIosInstall = () => {
    localStorage.setItem("cakecity-ios-install-dismissed", "1");
    setIosInstall(null);
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
      {iosInstall && (
        <aside className={`install-card ios-install-card ${iosHelpOpen ? "expanded" : ""}`} aria-label="Install Cake City on iPhone">
          <span className="install-icon"><img src="/icons/cake-city-icon.svg" alt="" /></span>
          <span>
            <b>Put Cake City on your iPhone</b>
            <small>{iosInstall === "safari" ? "Order faster, just like an app." : "Open this page in Safari to install it."}</small>
          </span>
          {iosInstall === "safari" && !iosHelpOpen && <button className="install-action" onClick={() => setIosHelpOpen(true)}>Show me how</button>}
          {iosInstall === "safari" && iosHelpOpen && (
            <ol className="ios-install-steps">
              <li><i><Share /></i><span><b>Tap Share</b><small>Use the Share button in Safari’s toolbar.</small></span></li>
              <li><i><Plus /></i><span><b>Add to Home Screen</b><small>Scroll the menu if you don’t see it immediately.</small></span></li>
              <li><i>CC</i><span><b>Tap Add</b><small>Cake City will appear with your other apps.</small></span></li>
            </ol>
          )}
          <button className="install-dismiss" onClick={dismissIosInstall} aria-label="Dismiss iPhone installation"><X /></button>
        </aside>
      )}
    </>
  );
}
