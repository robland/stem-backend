// Même normalisation que le backend (`accounts.models.normalize_phone`, format international E.164) et même
// contrôle (`PHONE_RE`) : `06 123 45 67`, `00242…` et `242…` deviennent `+242061234567`.
export function normalizePhone(input: string) {
  const phone = input.replace(/[\s.()-]/g, "");
  if (phone.startsWith("00")) return `+${phone.slice(2)}`;
  if (/^0\d{8}$/.test(phone)) return `+242${phone}`; // numéro national congolais : 9 chiffres, le 0 est conservé
  if (/^242\d{9}$/.test(phone)) return `+${phone}`;
  return phone;
}

export const isValidPhone = (phone: string) => /^\+[0-9]{8,15}$/.test(normalizePhone(phone));
