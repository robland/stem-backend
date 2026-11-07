import { isValidPhone, normalizePhone } from "./phone";

describe("normalizePhone (miroir du backend)", () => {
  it.each([
    ["06 123 45 67", "+242061234567"],
    ["06.123.45.67", "+242061234567"],
    ["00242 06 123 45 67", "+242061234567"],
    ["242061234567", "+242061234567"],
    ["+242 06 123 45 67", "+242061234567"],
    ["+33 6 12 34 56 78", "+33612345678"],
  ])("%s → %s", (input, expected) => {
    expect(normalizePhone(input)).toBe(expected);
  });

  it("refuse un numéro trop court ou sans indicatif reconnaissable", () => {
    expect(isValidPhone("12")).toBe(false);
    expect(isValidPhone("1234567")).toBe(false);
    expect(isValidPhone("06 123 45 67")).toBe(true);
  });
});
