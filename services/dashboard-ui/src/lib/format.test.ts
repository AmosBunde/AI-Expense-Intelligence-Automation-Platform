import { describe, expect, it } from "vitest";
import { formatCompact, formatDate, formatMoney, formatPercent, statusTone } from "./format";

describe("formatMoney", () => {
  it("keeps cents under $1000", () => {
    expect(formatMoney(42.5)).toBe("$42.50");
  });
  it("drops cents at $1000 and above", () => {
    expect(formatMoney(12345)).toBe("$12,345");
  });
});

describe("formatCompact", () => {
  it("abbreviates thousands and millions", () => {
    expect(formatCompact(950)).toBe("$950");
    expect(formatCompact(12_400)).toBe("$12.4K");
    expect(formatCompact(3_200_000)).toBe("$3.2M");
  });
});

describe("formatDate", () => {
  it("renders ISO dates and dashes for garbage", () => {
    expect(formatDate("2026-07-01T00:00:00Z")).toMatch(/Jul 1, 2026/);
    expect(formatDate("not-a-date")).toBe("—");
  });
});

describe("formatPercent", () => {
  it("renders fractions as whole percents", () => {
    expect(formatPercent(0.87)).toBe("87%");
  });
});

describe("statusTone", () => {
  it("maps statuses to the four badge tones", () => {
    expect(statusTone("approved")).toBe("good");
    expect(statusTone("PENDING")).toBe("warn");
    expect(statusTone("flagged")).toBe("serious");
    expect(statusTone("processing")).toBe("neutral");
  });
});
