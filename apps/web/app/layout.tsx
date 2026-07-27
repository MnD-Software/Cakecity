import type { Metadata, Viewport } from "next";
import "./styles.css";
import "./post.css";
import "./driver-tracking.css";
import "./loyalty.css";
import "./corporate.css";
import "./product.css";
import "./discovery.css";
import "./saved.css";
import "./addresses.css";
import "./subscriptions.css";
import { PwaShell } from "@/components/pwa-shell";

export const metadata: Metadata = {
  metadataBase: new URL("https://cakecity.co.ke"),
  title: { default: "Cake City — Made for your moment", template: "%s · Cake City" },
  description: "Handcrafted cakes, delivered across Nairobi. Personalise your cake and choose the moment it arrives.",
  applicationName: "Cake City",
  alternates: { canonical: "/" },
  keywords: ["cakes Nairobi", "birthday cakes Kenya", "wedding cakes Nairobi", "cake delivery Nairobi"],
  openGraph: {
    title: "Cake City — Made for your moment", description: "Handcrafted cakes, delivered across Nairobi.",
    type: "website", locale: "en_KE", siteName: "Cake City",
    images: [{ url: "/images/cake-city-hero.webp", width: 1600, height: 854, alt: "A handcrafted Cake City celebration cake" }],
  },
  twitter: {
    card: "summary_large_image", title: "Cake City — Made for your moment",
    description: "Handcrafted cakes, delivered across Nairobi.", images: ["/images/cake-city-hero.webp"],
  },
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = { themeColor: "#72153b", colorScheme: "light" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en-KE"><body>{children}<PwaShell /></body></html>;
}
