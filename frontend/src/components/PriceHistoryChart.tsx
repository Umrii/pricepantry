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

export function PriceHistoryChart({ history }: { history: Price[] }) {
  // Oldest -> newest for a left-to-right timeline.
  const data = [...history]
    .reverse()
    .map((p) => ({
      date: new Date(p.scraped_at).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
      }),
      price: parseFloat(p.price),
    }));

  if (data.length < 2) {
    return (
      <p className="text-sm text-gray-500">
        Not enough data yet — price history appears after a few scrapes.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
        <YAxis
          tick={{ fontSize: 12 }}
          stroke="#9ca3af"
          domain={["auto", "auto"]}
          tickFormatter={(v) => `£${v}`}
        />
        <Tooltip formatter={(v: number) => [`£${v.toFixed(2)}`, "Price"]} />
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
