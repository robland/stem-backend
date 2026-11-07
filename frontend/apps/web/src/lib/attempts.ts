/** Identifiant généré côté client (tentative, réponse) : rend les envois idempotents. */
export const newId = () => crypto.randomUUID();
