import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ProductExperience, type ProductDetail } from "@/components/product-experience";
import { liveProductDetail } from "@/lib/server-catalog";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const developmentPreview: ProductDetail = {
  woo_id: 901,
  slug: "red-velvet",
  name: "The Red Velvet",
  description: "Velvet cocoa crumb layered with vanilla bean cream and finished by hand.",
  short_description: "Our signature velvet crumb, vanilla bean cream and a finish worthy of the moment.",
  price_kes: "3200.00",
  regular_price_kes: "3500.00",
  in_stock: true,
  stock_quantity: 8,
  image_url: "/images/cake-city-hero.webp",
  average_rating: "4.90",
  review_count: 186,
  gallery: [
    { src: "/images/cake-city-hero.webp", alt: "Cake City signature red velvet celebration cake" },
    { src: "/images/cake-city-hero.png", alt: "Hand-finished Cake City celebration cake" },
  ],
  categories: ["Birthday Cakes"],
  attributes: [{ name: "Flavour", options: ["Red velvet", "Vanilla bean"] }],
  ingredients: "Wheat flour, cocoa, cultured milk, eggs, vanilla bean, butter and cream.",
  allergens: ["Gluten", "Milk", "Eggs"],
  nutrition: { serving: "100 g", energy: "382 kcal", protein: "5.4 g", carbohydrates: "48 g" },
  preparation_minutes: 180,
  video_url: null,
  spin_image_urls: [],
  recommendations: [
    { woo_id: 902, slug: "salted-caramel", name: "Salted Caramel Muse", description: "Caramel sponge and sea salt.", price_kes: "3600.00", regular_price_kes: null, in_stock: true, stock_quantity: 6, image_url: "/images/cake-city-hero.webp", average_rating: "4.80", review_count: 92 },
    { woo_id: 903, slug: "chocolate", name: "Midnight Chocolate", description: "Dark cocoa and ganache.", price_kes: "3400.00", regular_price_kes: null, in_stock: true, stock_quantity: 5, image_url: "/images/cake-city-hero.webp", average_rating: "4.90", review_count: 144 },
    { woo_id: 904, slug: "berry", name: "Berry Chantilly", description: "Vanilla bean and fresh berries.", price_kes: "3900.00", regular_price_kes: null, in_stock: true, stock_quantity: 4, image_url: "/images/cake-city-hero.webp", average_rating: "4.70", review_count: 71 },
  ],
};

async function loadProduct(slug: string): Promise<ProductDetail | null> {
  const response = await fetch(`${API_URL}/v1/catalog/products/${encodeURIComponent(slug)}`, {
    next: { revalidate: 300 },
  }).catch(() => null);
  if (!response?.ok) {
    const liveProduct = await liveProductDetail(slug);
    if (liveProduct) return liveProduct;
    return process.env.NODE_ENV === "development" && slug === developmentPreview.slug ? developmentPreview : null;
  }
  return response.json();
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> },
): Promise<Metadata> {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) return { title: "Cake not found" };
  const description = product.short_description || product.description || `Order ${product.name} from Cake City Nairobi.`;
  const image = product.gallery[0]?.src || product.image_url || "/images/cake-city-hero.webp";
  return {
    title: product.name,
    description: description.replace(/<[^>]*>/g, "").slice(0, 160),
    alternates: { canonical: `/cakes/${product.slug}` },
    openGraph: {
      title: `${product.name} | Cake City`,
      description: description.replace(/<[^>]*>/g, "").slice(0, 160),
      images: [{ url: image, alt: product.name }],
      type: "website",
    },
    twitter: { card: "summary_large_image", images: [image] },
  };
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) notFound();
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description: (product.short_description || product.description).replace(/<[^>]*>/g, ""),
    image: product.gallery.map(image => image.src),
    sku: `WC-${product.woo_id}`,
    offers: {
      "@type": "Offer",
      priceCurrency: "KES",
      price: product.price_kes,
      availability: product.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
      url: `https://cakecity.co.ke/cakes/${product.slug}`,
    },
    ...(product.review_count > 0 ? {
      aggregateRating: {
        "@type": "AggregateRating",
        ratingValue: product.average_rating,
        reviewCount: product.review_count,
      },
    } : {}),
  };
  return <>
    <script type="application/ld+json" dangerouslySetInnerHTML={{
      __html: JSON.stringify(structuredData).replace(/</g, "\\u003c"),
    }} />
    <ProductExperience product={product} />
  </>;
}
