"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft, ArrowRight, Check, ChevronDown, Clock3, Heart, MapPin, Maximize2,
  Minus, PackageCheck, Play, Plus, Rotate3D, ShieldCheck, ShoppingBag, Sparkles,
  Star, Truck, X,
} from "lucide-react";
import { formatKES, type CartItem, type Product } from "@/lib/catalog";
import { usePersistentCart } from "@/lib/use-persistent-cart";
import { trackDiscovery } from "@/lib/discovery";

type ProductSummary = {
  woo_id: number; slug: string; name: string; description: string; price_kes: string;
  regular_price_kes: string | null; in_stock: boolean; stock_quantity: number | null;
  image_url: string | null; average_rating: string; review_count: number;
};

export type ProductDetail = ProductSummary & {
  short_description: string;
  gallery: { src: string; alt: string }[];
  categories: string[];
  attributes: { name: string; options: string[] }[];
  ingredients: string | null;
  allergens: string[];
  nutrition: Record<string, string>;
  preparation_minutes: number;
  video_url: string | null;
  spin_image_urls: string[];
  recommendations: ProductSummary[];
};

const sizes: { id: CartItem["size"]; label: string; serves: string; extra: number }[] = [
  { id: "1kg", label: "1 kg", serves: "8–10 servings", extra: 0 },
  { id: "1.5kg", label: "1.5 kg", serves: "12–15 servings", extra: 900 },
  { id: "2kg", label: "2 kg", serves: "18–22 servings", extra: 1700 },
];
const extras = [
  { id: "candles", name: "Celebration candles", price: 250 },
  { id: "greeting-card", name: "Handwritten card", price: 350 },
  { id: "gift-wrap", name: "Signature gift wrap", price: 300 },
  { id: "flowers", name: "Seasonal flower bundle", price: 1800 },
];

function asCartProduct(product: ProductSummary): Product {
  return {
    id: product.slug,
    name: product.name,
    note: product.description.replace(/<[^>]*>/g, "").slice(0, 90),
    price: Number(product.price_kes),
    rating: Number(product.average_rating || 0),
    palette: "ruby",
    imageUrl: product.image_url ?? undefined,
  };
}

export function ProductExperience({ product }: { product: ProductDetail }) {
  const { cart, add } = usePersistentCart();
  const media = useMemo(() => product.gallery.length
    ? product.gallery
    : product.image_url ? [{ src: product.image_url, alt: product.name }] : [], [product]);
  const [activeImage, setActiveImage] = useState(0);
  const [size, setSize] = useState<CartItem["size"]>("1kg");
  const [message, setMessage] = useState("");
  const [addOns, setAddOns] = useState<string[]>([]);
  const [fulfilment, setFulfilment] = useState<"delivery" | "pickup">("delivery");
  const [slot, setSlot] = useState("Today · 3:30–4:00 PM");
  const [quantity, setQuantity] = useState(1);
  const [zoom, setZoom] = useState(false);
  const [favourite, setFavourite] = useState(false);
  const [added, setAdded] = useState(false);
  const [bundle, setBundle] = useState<string[]>([]);
  const [recentlyViewed, setRecentlyViewed] = useState<ProductSummary[]>([]);

  useEffect(() => {
    void trackDiscovery("view", { product_slug: product.slug, context: { surface: "product_page" } });
    try {
      const recent = JSON.parse(localStorage.getItem("cakecity-recent-v1") || "[]") as ProductSummary[];
      setRecentlyViewed(recent.filter(item => item.slug !== product.slug).slice(0, 4));
      localStorage.setItem("cakecity-recent-v1", JSON.stringify([
        product, ...recent.filter(item => item.slug !== product.slug),
      ].slice(0, 8)));
    } catch {
      localStorage.removeItem("cakecity-recent-v1");
    }
  }, [product]);

  const chosenSize = sizes.find(option => option.id === size)!;
  const extrasTotal = extras.filter(extra => addOns.includes(extra.id)).reduce((sum, item) => sum + item.price, 0);
  const unitPrice = Number(product.price_kes) + chosenSize.extra + extrasTotal;
  const total = unitPrice * quantity;
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  function addConfigured() {
    const item = asCartProduct(product);
    for (let index = 0; index < quantity; index += 1) add(item, { size, message, addOns });
    setAdded(true);
    void trackDiscovery("add_to_cart", {
      product_slug: product.slug,
      context: { quantity, size, add_ons: addOns.length },
    });
    window.setTimeout(() => setAdded(false), 3500);
  }

  function addBundle() {
    addConfigured();
    for (const recommendation of product.recommendations.filter(item => bundle.includes(item.slug))) {
      add(asCartProduct(recommendation));
    }
  }

  const description = (product.short_description || product.description)
    .replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

  return <main className="product-page">
    <header className="product-nav">
      <a href="/" className="product-brand" aria-label="Cake City home"><span>CAKE</span><span>CITY</span></a>
      <nav aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/#shop">Cakes</a><span>/</span><b>{product.name}</b></nav>
      <a href="/checkout" className="product-bag"><ShoppingBag /><span>{cartCount}</span></a>
    </header>

    <section className="product-stage">
      <div className="product-gallery">
        <div className="product-main-media">
          {media[activeImage] ? <img src={media[activeImage].src} alt={media[activeImage].alt} /> :
            <div className="product-media-fallback"><span>CC</span><b>{product.name}</b></div>}
          <button className="media-zoom" onClick={() => setZoom(true)} aria-label="Zoom product image"><Maximize2 /></button>
          {product.video_url && <a className="media-video" href={product.video_url} target="_blank" rel="noreferrer"><Play /> Watch the finish</a>}
          {product.spin_image_urls.length > 0 && <button className="media-spin" onClick={() => {
            const next = (activeImage + 1) % product.spin_image_urls.length;
            setActiveImage(next);
          }}><Rotate3D /> 360° view</button>}
        </div>
        {media.length > 1 && <div className="product-thumbnails" aria-label="Product gallery">
          {media.map((image, index) => <button key={`${image.src}-${index}`} className={activeImage === index ? "active" : ""} onClick={() => setActiveImage(index)}>
            <img src={image.src} alt="" />
          </button>)}
        </div>}
      </div>

      <div className="product-configurator">
        <a className="back-link" href="/#shop"><ArrowLeft /> Back to the collection</a>
        <div className="product-kicker"><span>{product.categories[0] || "Cake City signature"}</span><button onClick={() => setFavourite(value => !value)} aria-pressed={favourite}><Heart fill={favourite ? "currentColor" : "none"} /> {favourite ? "Saved" : "Save"}</button></div>
        <h1>{product.name}</h1>
        <div className="product-rating">
          <span><Star fill="currentColor" /> {Number(product.average_rating || 0).toFixed(1)}</span>
          <a href="#reviews">{product.review_count ? `${product.review_count} verified reviews` : "New Cake City creation"}</a>
        </div>
        <p className="product-description">{description || "Handcrafted in our Nairobi kitchen and finished for your moment."}</p>
        <div className="product-price"><strong>From {formatKES(Number(product.price_kes))}</strong>{product.regular_price_kes && Number(product.regular_price_kes) > Number(product.price_kes) && <del>{formatKES(Number(product.regular_price_kes))}</del>}</div>

        <fieldset className="config-group">
          <legend><span>01</span> Choose your size</legend>
          <div className="size-grid">{sizes.map(option => <button key={option.id} onClick={() => setSize(option.id)} className={size === option.id ? "active" : ""}>
            <span><b>{option.label}</b><small>{option.serves}</small></span>
            <strong>{option.extra ? `+ ${formatKES(option.extra)}` : "Included"}</strong>
            {size === option.id && <Check />}
          </button>)}</div>
        </fieldset>

        <fieldset className="config-group">
          <legend><span>02</span> Make it personal <small>Optional</small></legend>
          <label className="cake-message"><span>Writing on the cake <i>{message.length}/32</i></span><input maxLength={32} value={message} onChange={event => setMessage(event.target.value)} placeholder="Happy birthday, Amani!" /></label>
          <div className="extra-grid">{extras.map(extra => <button key={extra.id} onClick={() => setAddOns(items => items.includes(extra.id) ? items.filter(item => item !== extra.id) : [...items, extra.id])} className={addOns.includes(extra.id) ? "active" : ""}>
            <span>{addOns.includes(extra.id) ? <Check /> : <Plus />}</span><b>{extra.name}</b><small>+ {formatKES(extra.price)}</small>
          </button>)}</div>
        </fieldset>

        <fieldset className="config-group">
          <legend><span>03</span> Choose how it arrives</legend>
          <div className="fulfilment-tabs"><button className={fulfilment === "delivery" ? "active" : ""} onClick={() => setFulfilment("delivery")}><Truck /> Delivery</button><button className={fulfilment === "pickup" ? "active" : ""} onClick={() => setFulfilment("pickup")}><PackageCheck /> Pickup</button></div>
          <label className="slot-choice"><MapPin /><span><b>{fulfilment === "delivery" ? "Nairobi delivery window" : "Cake City collection"}</b><select value={slot} onChange={event => setSlot(event.target.value)}><option>Today · 3:30–4:00 PM</option><option>Today · 5:00–5:30 PM</option><option>Tomorrow · 10:00–10:30 AM</option></select></span><ChevronDown /></label>
        </fieldset>

        <div className="product-purchase">
          <div className="quantity-control"><button onClick={() => setQuantity(value => Math.max(1, value - 1))} aria-label="Decrease quantity"><Minus /></button><b>{quantity}</b><button onClick={() => setQuantity(value => Math.min(20, value + 1))} aria-label="Increase quantity"><Plus /></button></div>
          <button className="purchase-button" onClick={addConfigured} disabled={!product.in_stock}>{product.in_stock ? <>Add to bag <span>{formatKES(total)}</span><ArrowRight /></> : "Currently unavailable"}</button>
        </div>
        <div className="purchase-trust"><span><Clock3 /> Ready in about {Math.ceil(product.preparation_minutes / 60)} hours</span><span><ShieldCheck /> Secure M-Pesa & card checkout</span></div>
      </div>
    </section>

    <section className="product-story">
      <div><p className="product-eyebrow">Inside this creation</p><h2>Beautiful outside.<br /><em>Considered within.</em></h2><p>{description || "Thoughtfully layered, baked fresh and finished by hand."}</p></div>
      <div className="product-facts">
        <details open><summary>Ingredients <Plus /></summary><p>{product.ingredients || "Ingredient details are being completed by our pastry team. Contact us for a specific dietary need."}</p></details>
        <details><summary>Allergens <Plus /></summary><p>{product.allergens.length ? product.allergens.join(" · ") : "Please contact Cake City for the current allergen statement before ordering."}</p></details>
        <details><summary>Nutritional information <Plus /></summary><dl>{Object.entries(product.nutrition).length ? Object.entries(product.nutrition).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>) : <div><dt>Availability</dt><dd>On request</dd></div>}</dl></details>
        <details><summary>Preparation & care <Plus /></summary><p>Allow approximately {product.preparation_minutes} minutes. Keep chilled and bring to room temperature shortly before serving.</p></details>
      </div>
    </section>

    {product.recommendations.length > 0 && <section className="product-bundle">
      <div className="bundle-heading"><p className="product-eyebrow">Complete the celebration</p><h2>Often chosen together.</h2><p>Select a second creation and add the full pairing in one thoughtful gesture.</p></div>
      <div className="bundle-products">{product.recommendations.slice(0, 3).map(item => <article key={item.slug} className={bundle.includes(item.slug) ? "selected" : ""}>
        <button className="bundle-select" onClick={() => setBundle(items => items.includes(item.slug) ? items.filter(slug => slug !== item.slug) : [...items, item.slug])}>{bundle.includes(item.slug) ? <Check /> : <Plus />}</button>
        <a href={`/cakes/${item.slug}`}>{item.image_url ? <img src={item.image_url} alt={item.name} /> : <span className="bundle-fallback">CC</span>}<h3>{item.name}</h3><p>{formatKES(Number(item.price_kes))}</p></a>
      </article>)}</div>
      <button className="bundle-add" onClick={addBundle}><Sparkles /> Add selected pairing · {formatKES(total + product.recommendations.filter(item => bundle.includes(item.slug)).reduce((sum, item) => sum + Number(item.price_kes), 0))}</button>
    </section>}

    {recentlyViewed.length > 0 && <section className="recent-products">
      <div><p className="product-eyebrow">Continue your edit</p><h2>Recently viewed.</h2></div>
      <div>{recentlyViewed.map(item => <a href={`/cakes/${item.slug}`} key={item.slug}>
        {item.image_url ? <img src={item.image_url} alt={item.name} /> : <span>CC</span>}
        <b>{item.name}</b><small>{formatKES(Number(item.price_kes))}</small>
      </a>)}</div>
    </section>}

    <section className="product-reviews" id="reviews">
      <div><p className="product-eyebrow">The celebration verdict</p><h2>{product.review_count ? Number(product.average_rating).toFixed(1) : "Fresh"}<span><Star fill="currentColor" />{product.review_count ? `from ${product.review_count} verified orders` : "Awaiting its first verified review"}</span></h2></div>
      <blockquote>“Every Cake City order is linked to a verified purchase, so the stories here stay useful, honest and worthy of your moment.”</blockquote>
    </section>

    <footer className="product-footer"><a href="/" className="product-brand inverse"><span>CAKE</span><span>CITY</span></a><p>Joy, baked beautifully in Nairobi.</p></footer>

    {zoom && media[activeImage] && <div className="product-lightbox" role="dialog" aria-modal="true" aria-label={`Expanded image of ${product.name}`}><button onClick={() => setZoom(false)} aria-label="Close image"><X /></button><img src={media[activeImage].src} alt={media[activeImage].alt} /></div>}
    {added && <div className="product-toast" role="status"><Check /><span><b>Made yours.</b><small>{quantity} × {product.name} added to your bag for {slot}.</small></span><a href="/checkout">Checkout <ArrowRight /></a></div>}
  </main>;
}
