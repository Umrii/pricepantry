"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PriceTag } from "@/components/PriceTag";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";

export default function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.getProduct(id),
  });

  if (isLoading)
    return <p className="py-16 text-center text-gray-500">Loading product…</p>;
  if (isError || !product)
    return (
      <div className="py-16 text-center">
        <p className="text-red-500">Product not found.</p>
        <Link href="/" className="mt-4 inline-block text-brand hover:underline">
          ← Back to home
        </Link>
      </div>
    );

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="flex h-80 items-center justify-center bg-gray-50 p-6">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <span className="text-gray-300">No image</span>
          )}
        </Card>

        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{product.store.name}</Badge>
            {product.category && (
              <Badge className="bg-gray-100 text-gray-600">
                {product.category}
              </Badge>
            )}
          </div>

          <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>

          <dl className="grid grid-cols-2 gap-2 text-sm text-gray-600">
            {product.brand && (
              <>
                <dt className="text-gray-400">Brand</dt>
                <dd>{product.brand}</dd>
              </>
            )}
            {product.weight && (
              <>
                <dt className="text-gray-400">Size</dt>
                <dd>{product.weight}</dd>
              </>
            )}
          </dl>

          <div className="mt-2">
            <PriceTag
              value={product.latest_price}
              currency={product.currency}
              className="text-3xl"
            />
            {product.price_history[0]?.unit_price && (
              <span className="ml-2 text-sm text-gray-500">
                {product.price_history[0].unit_price}
              </span>
            )}
          </div>

          <a href={product.url} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" className="w-full sm:w-auto">
              View on Tesco <ExternalLink className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </div>

      <Card className="p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Price history
        </h2>
        <PriceHistoryChart history={product.price_history} />
      </Card>
    </div>
  );
}
