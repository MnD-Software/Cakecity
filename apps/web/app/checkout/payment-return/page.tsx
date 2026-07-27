"use client";

import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, LoaderCircle, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

type StoredIntent = { id: string; client_secret: string; order_reference: string };

export default function PaymentReturnPage() {
  const [state, setState] = useState("checking");
  const [reference, setReference] = useState("");

  useEffect(() => {
    const raw = sessionStorage.getItem("cakecity-active-payment");
    if (!raw) {
      setState("missing");
      return;
    }
    const intent = JSON.parse(raw) as StoredIntent;
    setReference(intent.order_reference);
    let attempts = 0;
    const check = async () => {
      try {
        const result = await api<{ state: string }>(`/v1/payments/intents/${intent.id}`, {
          headers: { "X-Payment-Secret": intent.client_secret },
        });
        setState(result.state);
        if (result.state === "paid") {
          await api("/v1/cart/complete", { method: "POST" }).catch(() => undefined);
          localStorage.removeItem("cakecity-cart-v1");
          sessionStorage.removeItem("cakecity-payment-idempotency");
          return;
        }
        if (!["failed", "cancelled", "review_required"].includes(result.state) && attempts++ < 20) {
          window.setTimeout(check, 3000);
        }
      } catch {
        if (attempts++ < 20) window.setTimeout(check, 3000);
        else setState("unavailable");
      }
    };
    void check();
  }, []);

  const paid = state === "paid";
  const waiting = ["checking", "created", "pending"].includes(state);
  return <main className="payment-return"><span className={`return-icon ${paid ? "success" : ""}`}>{paid ? <CheckCircle2 /> : waiting ? <LoaderCircle className="spin" /> : <ShieldAlert />}</span><p className="eyebrow">{reference || "Cake City payment"}</p><h1>{paid ? <>Your celebration<br /><em>is confirmed.</em></> : waiting ? <>Confirming your<br /><em>payment.</em></> : <>We need one<br /><em>more moment.</em></>}</h1><p>{paid ? "We’re sending your order to the Cake City kitchen now." : waiting ? "Please keep this page open while the provider confirms your payment." : "Your order has not been released. Contact support with the reference above if you completed payment."}</p><a className="button primary" href={paid ? "/account" : "/checkout"}>{paid ? "View my order" : "Return to checkout"} <ArrowRight /></a></main>;
}
