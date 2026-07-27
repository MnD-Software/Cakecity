export type Product = {
  id: string;
  name: string;
  note: string;
  price: number;
  rating: number;
  tag?: string;
  palette: string;
  imageUrl?: string;
  category?: string;
  categories?: string[];
};

export type CartItem = Product & {
  quantity: number;
  size: "1kg" | "1.5kg" | "2kg";
  message?: string;
  addOns: string[];
  unitPrice: number;
};

export const products: Product[] = [
  { id: "red-velvet", name: "The Red Velvet", note: "Velvet crumb · vanilla cream", price: 3200, rating: 4.9, tag: "Bestseller", palette: "ruby" },
  { id: "salted-caramel", name: "Salted Caramel Muse", note: "Caramel sponge · sea salt", price: 3600, rating: 4.8, tag: "New", palette: "caramel" },
  { id: "chocolate", name: "Midnight Chocolate", note: "Dark cocoa · ganache", price: 3400, rating: 4.9, palette: "cocoa" },
  { id: "berry", name: "Berry Chantilly", note: "Vanilla bean · fresh berries", price: 3900, rating: 4.7, palette: "berry" }
];

export const formatKES = (amount: number) =>
  new Intl.NumberFormat("en-KE", { style: "currency", currency: "KES", maximumFractionDigits: 0 }).format(amount);
