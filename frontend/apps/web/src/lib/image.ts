// Préparation des photos avant envoi (README frontend §1 et §6) : data mobile chère, téléphones modestes.
// Recadrage + rotation + réduction au côté long MAX_SIDE + JPEG, et les EXIF (localisation…) disparaissent
// avec le réencodage.

export const MAX_SIDE = 1600;
export const JPEG_QUALITY = 0.8;
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

/** Rectangle de recadrage en fractions de l'image (0 → 1). */
export type CropRect = { x: number; y: number; w: number; h: number };
export const FULL_CROP: CropRect = { x: 0, y: 0, w: 1, h: 1 };
export const MIN_CROP = 0.1;

export type Rotation = 0 | 90 | 180 | 270;

export const isPdf = (file: Blob) => file.type === "application/pdf";
export const isImage = (file: Blob) => file.type.startsWith("image/");

/** Dimensions après réduction pour que le côté long ne dépasse pas `max` (jamais d'agrandissement). */
export function fitWithin(width: number, height: number, max = MAX_SIDE) {
  const scale = Math.min(1, max / Math.max(width, height));
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) };
}

/** Rectangle en pixels de l'image source pour un recadrage fractionnaire. */
export function cropPixels(crop: CropRect, width: number, height: number) {
  const x = Math.round(crop.x * width);
  const y = Math.round(crop.y * height);
  return {
    x,
    y,
    width: Math.max(1, Math.min(width - x, Math.round(crop.w * width))),
    height: Math.max(1, Math.min(height - y, Math.round(crop.h * height))),
  };
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** Garde le rectangle dans l'image et au-dessus de la taille minimale. */
export function clampCrop({ x, y, w, h }: CropRect): CropRect {
  const width = clamp(w, MIN_CROP, 1);
  const height = clamp(h, MIN_CROP, 1);
  return { x: clamp(x, 0, 1 - width), y: clamp(y, 0, 1 - height), w: width, h: height };
}

export type Handle = "nw" | "ne" | "sw" | "se" | "move";

/** Déplace un coin (ou tout le cadre) de (dx, dy), en fractions de l'image. */
export function dragCrop(crop: CropRect, handle: Handle, dx: number, dy: number): CropRect {
  if (handle === "move") return clampCrop({ ...crop, x: crop.x + dx, y: crop.y + dy });
  let { x, y, w, h } = crop;
  const right = x + w;
  const bottom = y + h;
  if (handle.includes("w")) x = clamp(x + dx, 0, right - MIN_CROP);
  if (handle.includes("e")) w = clamp(w + dx, MIN_CROP, 1 - x);
  if (handle.includes("n")) y = clamp(y + dy, 0, bottom - MIN_CROP);
  if (handle.includes("s")) h = clamp(h + dy, MIN_CROP, 1 - y);
  if (handle.includes("w")) w = right - x;
  if (handle.includes("n")) h = bottom - y;
  return { x, y, w, h };
}

async function decode(file: Blob): Promise<ImageBitmap | HTMLImageElement> {
  if ("createImageBitmap" in window) {
    // L'orientation EXIF est appliquée par défaut (imageOrientation: "from-image").
    return createImageBitmap(file);
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return img;
  } finally {
    URL.revokeObjectURL(url);
  }
}

function toBlob(canvas: HTMLCanvasElement, type = "image/jpeg", quality = JPEG_QUALITY) {
  return new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Encodage impossible"))), type, quality),
  );
}

/** Tourne l'image d'un quart de tour par pas (aperçu et source du recadrage). */
export async function rotateImage(file: Blob, rotation: Rotation): Promise<Blob> {
  if (rotation === 0) return file;
  const image = await decode(file);
  const quarter = rotation % 180 !== 0;
  const { width, height } = fitWithin(image.width, image.height, MAX_SIDE * 2);
  const canvas = document.createElement("canvas");
  canvas.width = quarter ? height : width;
  canvas.height = quarter ? width : height;
  const ctx = canvas.getContext("2d")!;
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate((rotation * Math.PI) / 180);
  ctx.drawImage(image, -width / 2, -height / 2, width, height);
  return toBlob(canvas, "image/jpeg", 0.92);
}

/** Recadre, réduit et réencode en JPEG. */
export async function prepareImage(file: Blob, crop: CropRect = FULL_CROP): Promise<Blob> {
  const image = await decode(file);
  const area = cropPixels(crop, image.width, image.height);
  const target = fitWithin(area.width, area.height);
  const canvas = document.createElement("canvas");
  canvas.width = target.width;
  canvas.height = target.height;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#fff"; // PNG transparents : fond blanc plutôt que noir
  ctx.fillRect(0, 0, target.width, target.height);
  ctx.drawImage(image, area.x, area.y, area.width, area.height, 0, 0, target.width, target.height);
  if ("close" in image) image.close();
  return toBlob(canvas);
}
