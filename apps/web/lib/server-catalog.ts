import "server-only";
import type { Product } from "./catalog";
import type { ProductDetail } from "@/components/product-experience";

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
  description?: string;
  is_in_stock?: boolean;
  stock_quantity?: number | null;
  review_count?: number;
  attributes?: { name: string; terms?: { name: string }[] }[];
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
      note: clean(item.categories?.[0]?.name || "Baked fresh by Cake City"),
      price: Number(item.prices.price) / (10 ** item.prices.currency_minor_unit),
      rating: Number(item.average_rating || 0),
      tag: item.on_sale ? "Offer" : undefined,
      palette: ["ruby", "caramel", "cocoa", "berry"][index % 4],
      imageUrl: item.images?.[0]?.src,
      category: clean(item.categories?.[0]?.name || "Cakes"),
    }));
  } catch {
    return [];
  }
}

export async function liveProductDetail(slug: string): Promise<ProductDetail | null> {
  try {
    const response = await fetch(`${STORE_API}/products?slug=${encodeURIComponent(slug)}`, { next: { revalidate: 300 } });
    if (!response.ok) return null;
    const [item] = await response.json() as StoreProduct[];
    if (!item) return null;
    const price = Number(item.prices.price) / (10 ** item.prices.currency_minor_unit);
    return {
      woo_id: item.id,
      slug: item.slug,
      name: clean(item.name),
      description: clean(item.description || item.short_description || ""),
      short_description: clean(item.short_description || ""),
      price_kes: price.toFixed(2),
      regular_price_kes: null,
      in_stock: item.is_in_stock !== false,
      stock_quantity: item.stock_quantity ?? null,
      image_url: item.images?.[0]?.src || null,
      average_rating: item.average_rating || "0",
      review_count: item.review_count || 0,
      gallery: (item.images || []).map(image => ({ src: image.src, alt: clean(image.alt || item.name) })),
      categories: (item.categories || []).map(category => clean(category.name)),
      attributes: (item.attributes || []).map(attribute => ({ name: clean(attribute.name), options: (attribute.terms || []).map(term => clean(term.name)) })),
      ingredients: null,
      allergens: [],
      nutrition: {},
      preparation_minutes: 0,
      video_url: null,
      spin_image_urls: [],
      recommendations: [],
    };
  } catch {
    return null;
  }
}
