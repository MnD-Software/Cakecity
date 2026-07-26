import type { Metadata } from "next";
import "./styles.css";
import "./analytics.css";

export const metadata: Metadata = {
  title: "Cake City Command",
  description: "Cake City administration, growth and customer operations.",
  robots: { index: false, follow: false },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
