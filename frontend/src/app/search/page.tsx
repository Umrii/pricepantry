"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { ProductGrid } from "@/components/ProductGrid";
import { Pagination } from "@/components/Pagination";

const PAGE_SIZE = 12;

function SearchResults() {
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const [page, setPage] = useState(1);

  // Reset to page 1 whenever the query term changes.
  useEffect(() => setPage(1), [q]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["search", q, page],
    queryFn: () => api.search(q, page, PAGE_SIZE),
    enabled: q.length > 0,
  });

  return (
    <div className="space-y-6">
      <SearchBar initial={q} />

      {q.length === 0 ? (
        <p className="py-16 text-center text-gray-500">
          Type a search term above to find products.
        </p>
      ) : (
        <>
          <h1 className="text-lg text-gray-700">
            Results for <span className="font-semibold">“{q}”</span>
            {data ? ` — ${data.total} found` : ""}
          </h1>
          {isLoading && <p className="py-16 text-center text-gray-500">Searching…</p>}
          {isError && (
            <p className="py-16 text-center text-red-500">Search failed.</p>
          )}
          {data && <ProductGrid products={data.items} />}
          {data && (
            <Pagination page={data.page} pages={data.pages} onChange={setPage} />
          )}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="py-16 text-center text-gray-500">Loading…</p>}>
      <SearchResults />
    </Suspense>
  );
}
