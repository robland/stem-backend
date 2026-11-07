import { daysUntil, relativeDay } from "./dates";

// 2026-11-07 à 22h30 à Brazzaville (UTC+1) = 21h30 UTC.
const NOW = new Date("2026-11-07T21:30:00Z");

describe("dates (fuseau de Brazzaville)", () => {
  it("compte en jours calendaires locaux, pas en tranches de 24 h", () => {
    // 23h30 UTC = 00h30 le 8 à Brazzaville : c'est déjà demain.
    expect(daysUntil(new Date("2026-11-07T23:30:00Z"), NOW)).toBe(1);
    expect(daysUntil(new Date("2026-11-07T08:00:00Z"), NOW)).toBe(0);
  });

  it.each([
    ["2026-11-06T10:00:00Z", "aujourd'hui"],
    ["2026-11-07T22:00:00Z", "aujourd'hui"],
    ["2026-11-08T10:00:00Z", "demain"],
    ["2026-11-10T10:00:00Z", "dans 3 jours"],
    ["2026-11-20T10:00:00Z", "le 20 nov."],
  ])("%s → %s", (iso, expected) => {
    expect(relativeDay(iso, NOW)).toBe(expected);
  });
});
