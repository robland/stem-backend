// L'API n'expose jamais le fichier envoyé (README frontend §6) : la photo reste sur l'appareil pour être
// affichée à côté de l'énoncé pendant la vérification. En mémoire seulement (perdue au rechargement) ;
// la persistance viendra avec packages/offline.
const photos = new Map<string, string>();

export function keepPhoto(uploadId: string, file: Blob) {
  const previous = photos.get(uploadId);
  if (previous) URL.revokeObjectURL(previous);
  photos.set(uploadId, URL.createObjectURL(file));
}

export const getPhoto = (uploadId: string) => photos.get(uploadId) ?? null;
