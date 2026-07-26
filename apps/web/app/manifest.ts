import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Cake City",
    short_name: "Cake City",
    description: "Handcrafted cakes, made for your moment.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#fbf6ef",
    theme_color: "#72153b",
    categories: ["shopping", "food", "lifestyle"],
    shortcuts: [
      { name: "Shop cakes", short_name: "Shop", url: "/#shop", icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }] },
      { name: "My bag", short_name: "Bag", url: "/?bag=open", icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }] }
    ],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
    ]
  };
}
