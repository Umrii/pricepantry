import Link from "next/link";
import type { Product } from "@/lib/types";
import { Card, Badge } from "@/components/ui/card";
import { PriceTag } from "@/components/PriceTag";

export function ProductCard({ product }: { product: Product }) {
  return (
    <Link href={`/products/${product.id}`} className="group block">
      <Card className="flex h-full flex-col overflow-hidden">
        <div className="flex h-40 items-center justify-center bg-gray-50 p-4">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
              loading="lazy"
            />
          ) : (
            <div className="text-gray-300">No image</div>
          )}
        </div>
        <div className="flex flex-1 flex-col gap-2 p-4">
          {product.category && <Badge>{product.category}</Badge>}
          <h3 className="line-clamp-2 text-sm font-medium text-gray-900 group-hover:text-brand">
            {product.name}
          </h3>
          <div className="mt-auto flex items-end justify-between pt-2">
            <PriceTag
              value={product.latest_price}
              currency={product.currency}
              className="text-lg"
            />
            {product.weight && (
              <span className="text-xs text-gray-500">{product.weight}</span>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}
