import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: "https://cakecity.co.ke", lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: "https://cakecity.co.ke/#shop", lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: "https://cakecity.co.ke/#moments", lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: "https://cakecity.co.ke/#gifting", lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: "https://cakecity.co.ke/#rewards", lastModified: now, changeFrequency: "monthly", priority: 0.6 },
  ];
}
