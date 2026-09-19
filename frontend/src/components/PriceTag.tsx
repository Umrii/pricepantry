import { formatPrice } from "@/lib/utils";

export function PriceTag({
  value,
  currency,
  className = "",
}: {
  value: string | number | null;
  currency?: string | null;
  className?: string;
}) {
  return (
    <span className={`font-bold text-brand ${className}`}>
      {formatPrice(value, currency ?? "GBP")}
    </span>
  );
}
