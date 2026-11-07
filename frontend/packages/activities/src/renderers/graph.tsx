// Repère en SVG maison (léger, sans JSXGraph) : points à placer, courbe paramétrée par curseurs.
import type { Axes } from "@stem/content-schema";
import { cn, Input } from "@stem/ui";
import { useId, useRef, type PointerEvent, type ReactNode } from "react";
import { compileFunction } from "../math/expression";
import { s } from "../strings";
import type { ActivityDefinition, ActivityOf } from "../types";
import { mark, markClass } from "./common";

const W = 320;
const H = 240;
const PAD = 24;

/** Pas de graduation « rond » (1, 2 ou 5 × 10ⁿ) donnant environ `target` intervalles. */
export function niceStep(range: number, target = 8) {
  const raw = range / target;
  const power = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((m) => m * power).find((step) => step >= raw) ?? 10 * power;
}

const round = (value: number, step: number) => Number((Math.round(value / step) * step).toFixed(6));
const format = (n: number) => String(Number(n.toFixed(4))).replace(".", ",");
/** Nombre saisi en français (virgule) ou en anglais ; NaN si illisible. */
export const parseNumber = (text: string) =>
  text.trim() ? Number(text.replace(/\s/g, "").replace(",", ".").replace("−", "-")) : NaN;

export function scaleFor(axes: Axes) {
  const sx = (x: number) => PAD + ((x - axes.x_min) / (axes.x_max - axes.x_min)) * (W - 2 * PAD);
  const sy = (y: number) => H - PAD - ((y - axes.y_min) / (axes.y_max - axes.y_min)) * (H - 2 * PAD);
  const fromPixels = (px: number, py: number) => ({
    x: axes.x_min + ((px - PAD) / (W - 2 * PAD)) * (axes.x_max - axes.x_min),
    y: axes.y_min + ((H - PAD - py) / (H - 2 * PAD)) * (axes.y_max - axes.y_min),
  });
  return { sx, sy, fromPixels };
}

/** Tracé échantillonné ; coupé là où la fonction n'est pas définie ou saute (asymptote). */
export function curvePath(fn: (x: number) => number, axes: Axes, samples = 240) {
  const { sx, sy } = scaleFor(axes);
  const span = axes.y_max - axes.y_min;
  let d = "";
  let previous: number | null = null;
  for (let i = 0; i <= samples; i++) {
    const x = axes.x_min + (i / samples) * (axes.x_max - axes.x_min);
    const y = fn(x);
    const visible = Number.isFinite(y) && Math.abs(y - (axes.y_min + span / 2)) < span * 2;
    if (!visible || (previous !== null && Math.abs(y - previous) > span)) {
      previous = visible ? y : null;
      if (visible) d += `M${sx(x).toFixed(1)},${sy(y).toFixed(1)}`;
      continue;
    }
    d += `${previous === null ? "M" : "L"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`;
    previous = y;
  }
  return d;
}

function Plot({
  axes,
  children,
  label,
  onPointer,
}: {
  axes: Axes;
  children?: ReactNode;
  label: string;
  onPointer?: (x: number, y: number, phase: "down" | "move" | "up") => void;
}) {
  const { sx, sy, fromPixels } = scaleFor(axes);
  const svg = useRef<SVGSVGElement>(null);
  const clip = useId();
  const stepX = niceStep(axes.x_max - axes.x_min);
  const stepY = niceStep(axes.y_max - axes.y_min);
  const ticks = (min: number, max: number, step: number) => {
    const out: number[] = [];
    for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(round(v, step));
    return out;
  };
  const pointer = (phase: "down" | "move" | "up") => (event: PointerEvent<SVGSVGElement>) => {
    if (!onPointer || !svg.current) return;
    if (phase === "move" && event.buttons === 0 && event.pointerType === "mouse") return;
    const box = svg.current.getBoundingClientRect();
    const { x, y } = fromPixels(
      ((event.clientX - box.left) / box.width) * W,
      ((event.clientY - box.top) / box.height) * H,
    );
    if (phase === "down") svg.current.setPointerCapture(event.pointerId);
    onPointer(x, y, phase);
  };
  const x0 = Math.min(Math.max(0, axes.x_min), axes.x_max);
  const y0 = Math.min(Math.max(0, axes.y_min), axes.y_max);
  return (
    <svg
      ref={svg}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={label}
      className={cn(
        "border-border bg-surface text-muted w-full max-w-lg touch-none select-none rounded-lg border",
        onPointer && "cursor-crosshair",
      )}
      onPointerDown={pointer("down")}
      onPointerMove={pointer("move")}
      onPointerUp={pointer("up")}
    >
      <defs>
        <clipPath id={clip}>
          <rect x={PAD} y={PAD} width={W - 2 * PAD} height={H - 2 * PAD} />
        </clipPath>
      </defs>
      {ticks(axes.x_min, axes.x_max, stepX).map((x) => (
        <g key={`x${x}`}>
          <line x1={sx(x)} x2={sx(x)} y1={PAD} y2={H - PAD} stroke="currentColor" strokeOpacity={0.15} />
          <text
            x={sx(x)}
            y={Math.min(H - 6, sy(y0) + 12)}
            fontSize={9}
            textAnchor="middle"
            fill="currentColor"
          >
            {x === 0 ? "" : format(x)}
          </text>
        </g>
      ))}
      {ticks(axes.y_min, axes.y_max, stepY).map((y) => (
        <g key={`y${y}`}>
          <line x1={PAD} x2={W - PAD} y1={sy(y)} y2={sy(y)} stroke="currentColor" strokeOpacity={0.15} />
          <text x={Math.max(10, sx(x0) - 4)} y={sy(y) + 3} fontSize={9} textAnchor="end" fill="currentColor">
            {y === 0 ? "" : format(y)}
          </text>
        </g>
      ))}
      <line x1={PAD} x2={W - PAD} y1={sy(y0)} y2={sy(y0)} stroke="currentColor" strokeWidth={1.2} />
      <line x1={sx(x0)} x2={sx(x0)} y1={PAD} y2={H - PAD} stroke="currentColor" strokeWidth={1.2} />
      <g clipPath={`url(#${clip})`}>{children}</g>
    </svg>
  );
}

// --- Points à placer -----------------------------------------------------------------------------

type PointsValue = { points: { x: number; y: number | null }[] };

export const graphPoints: ActivityDefinition<ActivityOf<"graph_points">, PointsValue> = {
  initial: (activity) => ({ points: activity.points_to_place.map((x) => ({ x, y: null })) }),
  isComplete: (_a, value) =>
    Boolean(value?.points.length && value.points.every((p) => p.y !== null && Number.isFinite(p.y))),
  serialize: (value) => ({ points: value.points.map((p) => ({ x: p.x, y: p.y })) }),
  Renderer({ activity, value, onChange, disabled, details }) {
    const { axes } = activity;
    const { sx, sy } = scaleFor(axes);
    const active = useRef<number | null>(null);
    const points = value?.points ?? activity.points_to_place.map((x) => ({ x, y: null }));
    const snap = niceStep(axes.y_max - axes.y_min) / 10;
    const setY = (index: number, y: number | null) =>
      onChange({ points: points.map((p, i) => (i === index ? { ...p, y } : p)) });

    const onPointer = (x: number, y: number, phase: "down" | "move" | "up") => {
      if (disabled) return;
      if (phase === "down") {
        // Le point le plus proche (en abscisse) de l'endroit touché.
        let best = 0;
        points.forEach((p, i) => {
          if (Math.abs(p.x - x) < Math.abs(points[best]!.x - x)) best = i;
        });
        active.current = best;
      }
      if (active.current !== null && phase !== "up") {
        setY(active.current, round(Math.min(axes.y_max, Math.max(axes.y_min, y)), snap));
      }
      if (phase === "up") active.current = null;
    };

    return (
      <div className="flex flex-col gap-3">
        <p className="text-muted text-sm">{s.graphHint}</p>
        <Plot axes={axes} label={s.graph} onPointer={disabled ? undefined : onPointer}>
          {points.map((p) => (
            <line
              key={`g${p.x}`}
              x1={sx(p.x)}
              x2={sx(p.x)}
              y1={0}
              y2={H}
              stroke="rgb(var(--primary))"
              strokeDasharray="3 3"
              strokeOpacity={0.6}
            />
          ))}
          {points.map((p) =>
            p.y === null ? null : (
              <circle
                key={`p${p.x}`}
                cx={sx(p.x)}
                cy={sy(p.y)}
                r={7}
                fill="rgb(var(--primary))"
                stroke="white"
                strokeWidth={2}
              />
            ),
          )}
        </Plot>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {points.map((p, i) => (
            <PointInput
              key={p.x}
              x={p.x}
              y={p.y}
              disabled={disabled}
              ok={mark(details, "points", String(p.x))}
              onChange={(y) => setY(i, y)}
            />
          ))}
        </div>
      </div>
    );
  },
};

function PointInput({
  x,
  y,
  onChange,
  disabled,
  ok,
}: {
  x: number;
  y: number | null;
  onChange: (y: number | null) => void;
  disabled?: boolean;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span aria-hidden className="whitespace-nowrap font-serif">
        x = {format(x)}, y =
      </span>
      <Input
        aria-label={s.pointY(format(x))}
        inputMode="decimal"
        disabled={disabled}
        defaultValue={y === null ? "" : format(y)}
        key={y === null ? "vide" : format(y)}
        onBlur={(e) => {
          const parsed = parseNumber(e.target.value);
          onChange(Number.isFinite(parsed) ? parsed : null);
        }}
        className={cn("w-20 border-2", markClass(ok))}
      />
    </div>
  );
}

// --- Courbe paramétrée ---------------------------------------------------------------------------

type ParamsValue = { values: { name: string; value: number }[] };

export const graphParameters: ActivityDefinition<ActivityOf<"graph_parameters">, ParamsValue> = {
  initial: (activity) => ({ values: activity.sliders.map((sl) => ({ name: sl.name, value: sl.initial })) }),
  isComplete: (_a, value) => Boolean(value?.values.length),
  Renderer({ activity, value, onChange, disabled, details }) {
    const values = value?.values ?? activity.sliders.map((sl) => ({ name: sl.name, value: sl.initial }));
    const params = Object.fromEntries(values.map((v) => [v.name, v.value]));
    const fn = compileFunction(activity.function, params);
    const set = (name: string, v: number) =>
      onChange({ values: values.map((x) => (x.name === name ? { ...x, value: v } : x)) });
    return (
      <div className="flex flex-col gap-4">
        <Plot axes={activity.axes} label={s.graph}>
          {fn ? (
            <path
              d={curvePath(fn, activity.axes)}
              fill="none"
              stroke="rgb(var(--primary))"
              strokeWidth={2.5}
            />
          ) : null}
        </Plot>
        {activity.sliders.map((slider) => {
          const current = params[slider.name] ?? slider.initial;
          const ok = mark(details, "values", slider.name);
          return (
            <label
              key={slider.name}
              className={cn("flex flex-col gap-1 rounded-lg border-2 border-transparent p-2", markClass(ok))}
            >
              <span className="flex justify-between font-semibold">
                <span className="font-serif italic">{slider.name}</span>
                <output aria-live="polite">{format(current)}</output>
              </span>
              <input
                type="range"
                min={slider.min}
                max={slider.max}
                step={slider.step}
                value={current}
                disabled={disabled}
                aria-label={s.slider(slider.name)}
                onChange={(e) => set(slider.name, Number(e.target.value))}
                className="h-11 w-full accent-[rgb(var(--primary))]"
              />
            </label>
          );
        })}
      </div>
    );
  },
};
