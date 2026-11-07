import { cn } from "@stem/ui";
import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { dragCrop, type CropRect, type Handle } from "@/lib/image";
import { t } from "@/strings/fr";

const CORNERS: { handle: Exclude<Handle, "move">; className: string; label: string }[] = [
  {
    handle: "nw",
    className: "left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nwse-resize",
    label: t.scan.cropCorners.nw,
  },
  {
    handle: "ne",
    className: "right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-nesw-resize",
    label: t.scan.cropCorners.ne,
  },
  {
    handle: "sw",
    className: "bottom-0 left-0 -translate-x-1/2 translate-y-1/2 cursor-nesw-resize",
    label: t.scan.cropCorners.sw,
  },
  {
    handle: "se",
    className: "bottom-0 right-0 translate-x-1/2 translate-y-1/2 cursor-nwse-resize",
    label: t.scan.cropCorners.se,
  },
];

const KEY_STEP = 0.02;
const KEYS: Record<string, [number, number]> = {
  ArrowLeft: [-KEY_STEP, 0],
  ArrowRight: [KEY_STEP, 0],
  ArrowUp: [0, -KEY_STEP],
  ArrowDown: [0, KEY_STEP],
};

const rectStyle = (crop: CropRect) => ({
  left: `${crop.x * 100}%`,
  top: `${crop.y * 100}%`,
  width: `${crop.w * 100}%`,
  height: `${crop.h * 100}%`,
});

type Props = { src: string; crop: CropRect; onChange: (crop: CropRect) => void; alt: string };

/** Recadrage au doigt (coins de 44 px, cadre déplaçable) ou au clavier (flèches sur un coin ou le cadre). */
export function ImageCropper({ src, crop, onChange, alt }: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ handle: Handle; x: number; y: number; start: CropRect } | null>(null);

  const onPointerDown = (handle: Handle) => (event: PointerEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { handle, x: event.clientX, y: event.clientY, start: crop };
  };

  const onPointerMove = (event: PointerEvent<HTMLElement>) => {
    const current = drag.current;
    const box = frame.current?.getBoundingClientRect();
    if (!current || !box?.width || !box.height) return;
    const dx = (event.clientX - current.x) / box.width;
    const dy = (event.clientY - current.y) / box.height;
    onChange(dragCrop(current.start, current.handle, dx, dy));
  };

  const onPointerUp = () => {
    drag.current = null;
  };

  const onKeyDown = (handle: Handle) => (event: KeyboardEvent) => {
    const delta = KEYS[event.key];
    if (!delta) return;
    event.preventDefault();
    onChange(dragCrop(crop, handle, delta[0], delta[1]));
  };

  const pointerProps = (handle: Handle) => ({
    onPointerDown: onPointerDown(handle),
    onPointerMove,
    onPointerUp,
    onPointerCancel: onPointerUp,
    onKeyDown: onKeyDown(handle),
  });

  return (
    <div className="bg-surface-2 flex justify-center rounded-xl p-4">
      <div ref={frame} className="relative inline-block touch-none select-none">
        <img src={src} alt={alt} draggable={false} className="block max-h-[55dvh] w-auto max-w-full" />
        {/* Voile hors du cadre, coupé aux bords de l'image ; les poignées, elles, peuvent déborder. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute shadow-[0_0_0_9999px_rgba(0,0,0,0.55)]" style={rectStyle(crop)} />
        </div>
        <div className="absolute border-2 border-white" style={rectStyle(crop)}>
          <button
            type="button"
            aria-label={t.scan.cropMove}
            className="absolute inset-0 cursor-move"
            {...pointerProps("move")}
          />
          {CORNERS.map(({ handle, className, label }) => (
            <button
              key={handle}
              type="button"
              aria-label={label}
              className={cn("absolute flex size-11 items-center justify-center", className)}
              {...pointerProps(handle)}
            >
              <span aria-hidden className="border-primary size-5 rounded-full border-2 bg-white shadow" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
