import type { Metadata, Viewport } from "next";
import "./styles.css";
import "./post.css";
import "./driver-tracking.css";
import "./loyalty.css";
import "./corporate.css";
import { PwaShell } from "@/components/pwa-shell";

export const metadata: Metadata = {
  metadataBase: new URL("https://cakecity.co.ke"),
  title: { default: "Cake City — Made for your moment", template: "%s · Cake City" },
  description: "Handcrafted cakes, delivered across Nairobi. Personalise your cake and choose the moment it arrives.",
  openGraph: { title: "Cake City", description: "Made for your moment.", type: "website" },
  robots: { index: true, follow: true }
};

export const viewport: Viewport = { themeColor: "#72153b", colorScheme: "light" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}<PwaShell /></body></html>;
}
