import { Storefront } from "@/components/storefront";
import { liveStorefrontProducts } from "@/lib/server-catalog";

export default async function Home() {
  const liveProducts = await liveStorefrontProducts();
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Bakery", "@id": "https://cakecity.co.ke/#business",
        name: "Cake City", url: "https://cakecity.co.ke",
        image: "https://cakecity.co.ke/images/cake-city-hero.webp",
        logo: "https://i0.wp.com/cakecity.co.ke/wp-content/uploads/2024/08/Untitled-design-17.png",
        priceRange: "KES", currenciesAccepted: "KES", paymentAccepted: "M-Pesa, Card",
        areaServed: { "@type": "City", name: "Nairobi" },
        address: { "@type": "PostalAddress", addressLocality: "Nairobi", addressCountry: "KE" },
      },
      {
        "@type": "WebSite", "@id": "https://cakecity.co.ke/#website",
        url: "https://cakecity.co.ke", name: "Cake City",
        publisher: { "@id": "https://cakecity.co.ke/#business" }, inLanguage: "en-KE",
      },
    ],
  };
  return <><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData).replace(/</g, "\\u003c") }} /><Storefront initialProducts={liveProducts} /></>;
}
