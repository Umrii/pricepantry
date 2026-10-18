import { afterEach, describe, expect, it, vi } from "vitest";
import {
  formatObservedAt,
  formatShortDate,
  freshThresholdHours,
  freshnessOf,
} from "./freshness";

afterEach(() => {
  delete process.env.NEXT_PUBLIC_PRICE_FRESH_HOURS;
  vi.useRealTimers();
});

describe("formatObservedAt", () => {
  it("formats a UTC timestamp in UK local time", () => {
    // 11:21 UTC in October is 12:21 BST (Europe/London, DST).
    expect(formatObservedAt("2026-10-18T11:21:44Z")).toBe("18 Oct, 12:21");
  });

  it("returns null for missing/invalid input", () => {
    expect(formatObservedAt(null)).toBeNull();
    expect(formatObservedAt(undefined)).toBeNull();
    expect(formatObservedAt("not-a-date")).toBeNull();
  });
});

describe("formatShortDate", () => {
  it("formats a short UK date", () => {
    expect(formatShortDate("2026-10-18T11:21:44Z")).toBe("18 Oct");
  });
});

describe("freshThresholdHours", () => {
  it("defaults to 24h", () => {
    expect(freshThresholdHours()).toBe(24);
  });
  it("reads a positive override from env", () => {
    process.env.NEXT_PUBLIC_PRICE_FRESH_HOURS = "6";
    expect(freshThresholdHours()).toBe(6);
  });
  it("ignores invalid overrides", () => {
    process.env.NEXT_PUBLIC_PRICE_FRESH_HOURS = "-3";
    expect(freshThresholdHours()).toBe(24);
  });
});

describe("freshnessOf", () => {
  const now = new Date("2026-10-18T12:00:00Z");

  it("classifies a recent observation as fresh", () => {
    expect(freshnessOf("2026-10-18T06:00:00Z", now)).toBe("fresh"); // 6h old
  });
  it("classifies an old observation as stale", () => {
    expect(freshnessOf("2026-10-16T12:00:00Z", now)).toBe("stale"); // 48h old
  });
  it("is unknown when there is no timestamp", () => {
    expect(freshnessOf(null, now)).toBe("unknown");
  });
});
