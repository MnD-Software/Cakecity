"use client";

import { lazy, Suspense, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Bell, Check, ChevronRight, Gift, Heart, Home, MapPin, Menu, Minus, Plus, Search, ShoppingBag, Sparkles, Star, UserRound, WandSparkles, X, Zap } from "lucide-react";
import { formatKES, products, type CartItem, type Product } from "@/lib/catalog";
import { usePersistentCart } from "@/lib/use-persistent-cart";
import { useSavedCakes } from "@/lib/use-saved-cakes";
const NaturalSearchPanel = lazy(() =>
  import("@/components/discovery-experience").then(module => ({ default: module.NaturalSearchPanel })),
);
const ConciergePanel = lazy(() =>
  import("@/components/discovery-experience").then(module => ({ default: module.ConciergePanel })),
);
const PersonalizedRail = lazy(() =>
  import("@/components/personalized-rail").then(module => ({ default: module.PersonalizedRail })),
);

export function Storefront() {
  const { cart, add, updateQuantity } = usePersistentCart();
  const { isSaved, toggle: toggleSaved } = useSavedCakes();
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [conciergeOpen, setConciergeOpen] = useState(false);
  const [offerIndex, setOfferIndex] = useState(0);
  const hasDiscoveryApi = process.env.NODE_ENV !== "production" || Boolean(process.env.NEXT_PUBLIC_API_URL);

  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = cart.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  const offers = [
    { kicker: "Cake of the month", title: "Butterscotch 1.5kg offer", copy: "A Cake City favourite sized for the whole table.", price: "KES 3,500", tone: "butterscotch" },
    { kicker: "Limited drop", title: "Midnight Fantasy 1.5kg", copy: "Deep chocolate, glossy ganache and a celebratory finish.", price: "KES 3,500", tone: "midnight" },
    { kicker: "Party ready", title: "Pink Simba birthday set", copy: "Cake, colour and school-party energy in one easy order.", price: "KES 12,000", tone: "simba" },
  ];

  useEffect(() => {
    const timer = window.setInterval(() => setOfferIndex(current => (current + 1) % offers.length), 6500);
    return () => window.clearInterval(timer);
  }, [offers.length]);

  const addConfigured = (product: Product, configuration: { size: CartItem["size"]; message: string }) => {
    add(product, configuration);
    setActiveProduct(null);
    setCartOpen(true);
  };

  return (
    <main>
      <div className="announcement">
        <span>Complimentary delivery in Nairobi on orders over KES 5,000</span>
        <button>Discover Cake City Rewards <ArrowRight size={14} /></button>
      </div>

      <header className="header">
        <button className="icon-button mobile-menu" aria-label="Open menu"><Menu /></button>
        <a className="brand" href="#" aria-label="Cake City home"><span>CAKE</span><span>CITY</span></a>
        <nav aria-label="Primary navigation">
          <a href="#shop">Cakes</a><a href="#moments">Occasions</a><a href="#gifting">Gifting</a><a href="#rewards">Rewards</a>
        </nav>
        <div className="header-actions">
          <button className="location"><MapPin size={17} /> Nairobi <ChevronRight size={14} /></button>
          <button className="icon-button" onClick={() => setSearchOpen(true)} aria-label="Search"><Search /></button>
          <a className="icon-button" href="/account" aria-label="Customer account"><UserRound /></a>
          <button className="bag-button" onClick={() => setCartOpen(true)} aria-label={`Shopping bag with ${count} items`}><ShoppingBag /><span>{count}</span></button>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">The celebration edit · 2026</p>
          <h1>Made for<br />your <em>moment.</em></h1>
          <p>Thoughtfully crafted cakes for the people and milestones that deserve something extraordinary.</p>
          <div className="hero-actions">
            <a className="button primary" href="#shop">Find your cake <ArrowRight /></a>
            <a className="text-link" href="#concierge">Create something custom</a>
          </div>
          <div className="hero-proof"><span className="avatars">CC</span><span><b>Loved by 50,000+ celebrations</b><small><Star size={13} fill="currentColor" /> 4.9 from verified customers</small></span></div>
        </div>
        <div className="hero-art" role="img" aria-label="Burgundy celebration cake with cream piping and roses">
          <div className="floating-card"><Sparkles size={18} /><span><b>Made today</b><small>Delivered at your perfect time</small></span></div>
        </div>
      </section>

      <section className="promise-strip" aria-label="Service promises">
        <span><Check /> Baked fresh daily</span><span><Check /> Delivered in a 30-min window</span><span><Check /> Happiness guaranteed</span><span><Check /> Secure M-Pesa checkout</span>
      </section>

      <section className="offer-carousel" aria-roledescription="carousel" aria-label="Cake City offers">
        <div className={`offer-visual ${offers[offerIndex].tone}`} aria-hidden="true">
          <span className="offer-orbit orbit-one" /><span className="offer-orbit orbit-two" />
          <span className="cake offer-cake"><i /><b /><i /></span>
          <span className="offer-badge">1.5KG</span>
        </div>
        <div className="offer-copy" aria-live="polite">
          <p className="eyebrow">{offers[offerIndex].kicker}</p>
          <span className="offer-count">0{offerIndex + 1} / 0{offers.length}</span>
          <h2>{offers[offerIndex].title}</h2>
          <p>{offers[offerIndex].copy}</p>
          <div className="offer-action-row"><strong>{offers[offerIndex].price}</strong><a className="button primary" href="#shop">Shop this offer <ArrowRight /></a></div>
          <div className="offer-controls">
            <button onClick={() => setOfferIndex(current => (current - 1 + offers.length) % offers.length)} aria-label="Previous offer"><ArrowLeft /></button>
            <div>{offers.map((offer, index) => <button key={offer.title} className={index === offerIndex ? "active" : ""} onClick={() => setOfferIndex(index)} aria-label={`Show ${offer.title}`} aria-current={index === offerIndex ? "true" : undefined} />)}</div>
            <button onClick={() => setOfferIndex(current => (current + 1) % offers.length)} aria-label="Next offer"><ArrowRight /></button>
          </div>
        </div>
      </section>

      <section className="section" id="shop">
        <div className="section-heading">
          <div><p className="eyebrow">Curated for you</p><h2>The cakes everyone<br />is talking about.</h2></div>
          <a className="text-link" href="#all">Explore all cakes <ArrowRight /></a>
        </div>
        <div className="product-grid">
          {products.map((product, index) => (
            <article className="product-card" key={product.id} style={{ animationDelay: `${index * 80}ms` }}>
              <button className={`heart ${isSaved(product.id) ? "selected" : ""}`} onClick={() => toggleSaved(product.id)} aria-pressed={isSaved(product.id)} aria-label={`Save ${product.name}`}><Heart fill="currentColor" /></button>
              {product.tag && <span className="product-tag">{product.tag}</span>}
              <button className={`cake-visual ${product.palette}`} onClick={() => setActiveProduct(product)} aria-label={`View ${product.name}`}>
                <span className="cake"><i /><b /><i /></span>
              </button>
              <div className="product-info">
                <div><h3>{product.name}</h3><p>{product.note}</p></div><span className="rating"><Star size={13} fill="currentColor" /> {product.rating}</span>
                <strong>From {formatKES(product.price)}</strong>
                <a className="product-details-link" href={`/cakes/${product.id}`}>View cake details <ArrowRight /></a>
                <button className="quick-add" onClick={() => setActiveProduct(product)}>Personalise <Plus /></button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {hasDiscoveryApi && <Suspense fallback={null}><PersonalizedRail /></Suspense>}

      <section className="smart-studio section" id="smart-studio">
        <div className="smart-heading"><p className="eyebrow">Celebration OS</p><h2>Your moment,<br /><em>beautifully orchestrated.</em></h2><p>A faster, app-like way to plan, personalise and follow every celebration.</p></div>
        <div className="smart-grid">
          <button className="smart-card featured" onClick={() => setConciergeOpen(true)}><span className="smart-icon"><WandSparkles /></span><small>AI cake concierge</small><b>Describe the moment.<br />Meet your perfect cake.</b><span>Start a recommendation <ArrowRight /></span></button>
          <a className="smart-card" href="/account/moments"><span className="smart-icon"><Bell /></span><small>Moment memory</small><b>Never miss a birthday again.</b><span>Save a celebration <ArrowRight /></span></a>
          <a className="smart-card dark" href="/account/orders"><span className="delivery-pulse"><i /></span><small>Live delivery</small><b>Kitchen to doorstep, tracked.</b><span>Track an order <ArrowRight /></span></a>
          <a className="smart-card" href="/account/rewards"><span className="smart-icon"><Zap /></span><small>City rewards</small><b>Turn every celebration into your next.</b><span>See your rewards <ArrowRight /></span></a>
        </div>
      </section>

      <section className="occasion" id="moments">
        <div className="occasion-copy"><p className="eyebrow light">Find your perfect cake</p><h2>What are we<br /><em>celebrating?</em></h2><p>Tell us the moment. We’ll help with the magic.</p></div>
        <div className="occasion-grid">
          {["Birthday", "Wedding", "Just because", "Corporate"].map((name, i) => <button key={name} className={`occasion-card oc-${i}`}><span>0{i + 1}</span><b>{name}</b><ArrowRight /></button>)}
        </div>
      </section>

      <section className="concierge section" id="concierge">
        <div><span className="concierge-mark">CC</span><p className="eyebrow">Cake concierge</p><h2>Not sure what to choose?</h2><p>Share the occasion, who it’s for and your budget. Our cake concierge will curate a few perfect options in under a minute.</p></div>
        <button className="button primary" onClick={() => setConciergeOpen(true)}>Help me choose <Sparkles /></button>
      </section>

      <footer><a className="brand inverse" href="#"><span>CAKE</span><span>CITY</span></a><p>Joy, baked beautifully in Nairobi.</p><span>© 2026 Cake City Kenya</span></footer>

      <nav className="mobile-tabbar" aria-label="Mobile app navigation">
        <a className="active" href="#"><Home /><span>Home</span></a>
        <a href="#shop"><Search /><span>Explore</span></a>
        <button className="tabbar-order" onClick={() => setCartOpen(true)}><ShoppingBag /><i>{count}</i><span>Bag</span></button>
        <a href="/account/moments"><Gift /><span>Moments</span></a>
        <a href="/account"><UserRound /><span>Account</span></a>
      </nav>

      {searchOpen && <Suspense fallback={null}><NaturalSearchPanel close={() => setSearchOpen(false)} /></Suspense>}
      {conciergeOpen && <Suspense fallback={null}><ConciergePanel close={() => setConciergeOpen(false)} /></Suspense>}
      {activeProduct && <ProductPanel product={activeProduct} close={() => setActiveProduct(null)} add={configuration => addConfigured(activeProduct, configuration)} />}
      <CartPanel open={cartOpen} close={() => setCartOpen(false)} cart={cart} subtotal={subtotal} update={updateQuantity} />
    </main>
  );
}

function ProductPanel({ product, close, add }: { product: Product; close: () => void; add: (configuration: { size: CartItem["size"]; message: string }) => void }) {
  const [size, setSize] = useState<CartItem["size"]>("1kg");
  const [message, setMessage] = useState("");
  const options: { id: CartItem["size"]; label: string; extra: number }[] = [
    { id: "1kg", label: "1kg · 8–10", extra: 0 },
    { id: "1.5kg", label: "1.5kg · 12–15", extra: 900 },
    { id: "2kg", label: "2kg · 18–22", extra: 1700 },
  ];
  const extra = options.find(option => option.id === size)?.extra ?? 0;
  return <div className="overlay" role="dialog" aria-modal="true" aria-label={`Personalise ${product.name}`}><div className="drawer product-drawer"><button className="close" onClick={close}><X /></button><div className={`product-hero ${product.palette}`}><span className="cake large"><i /><b /><i /></span></div><div className="drawer-content"><p className="eyebrow">Made yours</p><h2>{product.name}</h2><p>{product.note}. Baked today and hand-finished by our Nairobi kitchen.</p><fieldset><legend>Choose a size</legend>{options.map(option => <button key={option.id} className={size === option.id ? "choice active" : "choice"} onClick={() => setSize(option.id)}>{option.label}<span>{option.extra ? `+ ${formatKES(option.extra)}` : formatKES(product.price)}</span></button>)}</fieldset><label className="message-label">Write on the cake <span>{message.length}/32</span><input maxLength={32} value={message} onChange={event => setMessage(event.target.value)} placeholder="e.g. Happy birthday, Amani!" /></label><div className="delivery-note"><MapPin /><span><b>Earliest delivery: Today, 3:30–4:00 PM</b><small>Choose delivery or pickup at checkout</small></span></div><button className="button primary full" onClick={() => add({ size, message })}>Add to bag · {formatKES(product.price + extra)} <ArrowRight /></button></div></div></div>;
}

function CartPanel({ open, close, cart, subtotal, update }: { open: boolean; close: () => void; cart: CartItem[]; subtotal: number; update: (id: string, size: string, delta: number) => void }) {
  return <div className={`overlay cart-overlay ${open ? "open" : ""}`} aria-hidden={!open}><button className="overlay-close" onClick={close} aria-label="Close bag" /><aside className="drawer cart-drawer" aria-label="Shopping bag"><div className="drawer-header"><div><p className="eyebrow">Your bag</p><h2>{cart.length ? "A celebration awaits." : "Your bag is empty."}</h2></div><button className="close" onClick={close}><X /></button></div><div className="cart-items">{cart.map(item => <div className="cart-item" key={`${item.id}-${item.size}-${item.message}`}><span className={`mini-cake ${item.palette}`} /><div><b>{item.name}</b><small>{item.size} · {item.message || "No cake message"}</small><div className="quantity"><button onClick={() => update(item.id, item.size, -1)}><Minus /></button><span>{item.quantity}</span><button onClick={() => update(item.id, item.size, 1)}><Plus /></button></div></div><strong>{formatKES(item.unitPrice * item.quantity)}</strong></div>)}</div>{cart.length > 0 && <div className="cart-footer"><div className="progress"><span style={{ width: `${Math.min(100, subtotal / 50)}%` }} /></div><p>{subtotal >= 5000 ? "You’ve unlocked complimentary delivery." : `${formatKES(5000 - subtotal)} away from complimentary delivery`}</p><div className="total"><span>Estimated subtotal<small>Confirmed securely at checkout</small></span><b>{formatKES(subtotal)}</b></div><a className="button primary full" href="/checkout">Choose delivery time <ArrowRight /></a><small className="secure"><Check /> Secure checkout · M-Pesa and cards</small></div>}</aside></div>;
}
