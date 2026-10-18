"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Price } from "@/lib/types";
import { formatPrice } from "@/lib/utils";
import { formatObservedAt, formatShortDate } from "@/lib/freshness";

export function PriceHistoryChart({ history }: { history: Price[] }) {
  // Sort chronologically (oldest -> newest) for a left-to-right timeline.
  // We never invent, interpolate, or dedupe points — identical consecutive
  // prices render as a flat segment, which is correct.
  const points = [...history]
    .sort(
      (a, b) =>
        new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime(),
    )
    .map((p) => ({
      date: formatShortDate(p.scraped_at),
      price: parseFloat(p.price),
    }));

  if (points.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No price history yet. Observations appear here once prices have been
        collected for this product.
      </p>
    );
  }

  if (points.length === 1) {
    const only = history[0];
    return (
      <p className="text-sm text-gray-500">
        Only one observation so far:{" "}
        <span className="font-medium text-gray-700">
          {formatPrice(only.price, only.currency)}
        </span>{" "}
        on {formatObservedAt(only.scraped_at)}. A trend line appears once there
        are at least two observations.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
        <YAxis
          tick={{ fontSize: 12 }}
          stroke="#9ca3af"
          domain={["auto", "auto"]}
          tickFormatter={(v) => formatPrice(v, "GBP")}
          width={64}
        />
        <Tooltip formatter={(v: number) => [formatPrice(v, "GBP"), "Price"]} />
        <Line
          type="monotone"
          dataKey="price"
          stroke="#00539f"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
