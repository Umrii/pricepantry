import type { Page, Product, ProductDetail } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProducts: (page = 1, pageSize = 12, category?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (category) params.set("category", category);
    return getJSON<Page<Product>>(`/products?${params.toString()}`);
  },

  search: (q: string, page = 1, pageSize = 12) => {
    const params = new URLSearchParams({
      q,
      page: String(page),
      page_size: String(pageSize),
    });
    return getJSON<Page<Product>>(`/search?${params.toString()}`);
  },

  getProduct: (id: number | string) => getJSON<ProductDetail>(`/products/${id}`),
};

export { API_URL };
