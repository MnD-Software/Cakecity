import "server-only";
import type { Product } from "./catalog";

const STORE_API = "https://cakecity.co.ke/wp-json/wc/store/v1";

type StoreProduct = {
  id: number;
  name: string;
  slug: string;
  short_description?: string;
  on_sale?: boolean;
  average_rating?: string;
  prices: { price: string; currency_minor_unit: number };
  images?: { src: string; alt?: string }[];
  categories?: { name: string }[];
};

const clean = (value: string) => value
  .replace(/<[^>]*>/g, " ")
  .replace(/&#8211;|&ndash;/g, "–")
  .replace(/&#8217;|&rsquo;/g, "’")
  .replace(/&amp;/g, "&")
  .replace(/\s+/g, " ")
  .trim();

export async function liveStorefrontProducts(limit = 12): Promise<Product[]> {
  try {
    const response = await fetch(`${STORE_API}/products?per_page=${limit}`, { next: { revalidate: 300 } });
    if (!response.ok) return [];
    const payload = await response.json() as StoreProduct[];
    return payload.map((item, index) => ({
      id: item.slug,
      name: clean(item.name),
      note: clean(item.short_description || item.categories?.[0]?.name || "Baked fresh by Cake City"),
      price: Number(item.prices.price) / (10 ** item.prices.currency_minor_unit),
      rating: Number(item.average_rating || 0),
      tag: item.on_sale ? "Offer" : undefined,
      palette: ["ruby", "caramel", "cocoa", "berry"][index % 4],
      imageUrl: item.images?.[0]?.src,
    }));
  } catch {
    return [];
  }
}
