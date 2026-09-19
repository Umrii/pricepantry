export interface Store {
  id: number;
  name: string;
  slug: string;
  website_url: string | null;
  logo_url: string | null;
}

export interface Product {
  id: number;
  store_id: number;
  external_id: string | null;
  name: string;
  brand: string | null;
  weight: string | null;
  category: string | null;
  image_url: string | null;
  url: string;
  store: Store;
  latest_price: string | null;
  currency: string | null;
}

export interface Price {
  id: number;
  product_id: number;
  price: string;
  currency: string;
  unit_price: string | null;
  in_stock: boolean;
  scraped_at: string;
}

export interface ProductDetail extends Product {
  price_history: Price[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
