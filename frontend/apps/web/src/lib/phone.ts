// Même normalisation que le backend (`accounts.models.normalize_phone`) et même contrôle (`PHONE_RE`).
export const normalizePhone = (phone: string) => phone.replace(/[\s.-]/g, "");

export const isValidPhone = (phone: string) => /^\+?[0-9]{8,15}$/.test(normalizePhone(phone));
