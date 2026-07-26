import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/account/", "/checkout/", "/corporate/"] }],
    sitemap: "https://cakecity.co.ke/sitemap.xml",
    host: "https://cakecity.co.ke",
  };
}
