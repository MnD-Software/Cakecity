import type { MetadataRoute } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const base = "https://cakecity.co.ke";
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: base, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${base}/#shop`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/#moments`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/#gifting`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/#rewards`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/corporate`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
  ];
  try {
    const response = await fetch(`${API_URL}/v1/catalog/products?page_size=60`, {
      next: { revalidate: 1800 },
    });
    if (!response.ok) return staticRoutes;
    const catalogue = await response.json() as { items: { slug: string }[] };
    return [
      ...staticRoutes,
      ...catalogue.items.map(item => ({
        url: `${base}/cakes/${item.slug}`,
        lastModified: now,
        changeFrequency: "daily" as const,
        priority: 0.8,
      })),
    ];
  } catch {
    return staticRoutes;
  }
}
