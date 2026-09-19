"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { ProductGrid } from "@/components/ProductGrid";
import { Pagination } from "@/components/Pagination";

const PAGE_SIZE = 12;

export default function HomePage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", page],
    queryFn: () => api.listProducts(page, PAGE_SIZE),
  });

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-gradient-to-r from-brand to-brand-dark px-6 py-12 text-center text-white">
        <h1 className="text-3xl font-bold sm:text-4xl">
          Compare UK grocery prices
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-white/80">
          Search products and track prices. Phase 1 covers Tesco — more
          supermarkets coming soon.
        </p>
        <div className="mt-6 flex justify-center">
          <SearchBar />
        </div>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Browse products</h2>
          {data && (
            <span className="text-sm text-gray-500">{data.total} products</span>
          )}
        </div>

        {isLoading && <GridSkeleton />}
        {isError && (
          <p className="py-16 text-center text-red-500">
            Couldn’t load products. Is the API running?
          </p>
        )}
        {data && <ProductGrid products={data.items} />}
        {data && (
          <Pagination page={data.page} pages={data.pages} onChange={setPage} />
        )}
      </section>
    </div>
  );
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-64 animate-pulse rounded-lg bg-gray-200" />
      ))}
    </div>
  );
}
