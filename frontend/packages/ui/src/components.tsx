import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, useId, type ComponentPropsWithoutRef, type ReactNode } from "react";
import { cn } from "./cn";

const buttonVariants = cva(
  "inline-flex min-h-touch select-none items-center justify-center gap-2 rounded-lg px-4 font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg hover:bg-primary/90",
        secondary: "border border-border bg-surface text-fg hover:bg-surface-2",
        ghost: "text-fg hover:bg-surface-2",
        accent: "bg-accent text-accent-fg hover:bg-accent/90",
        danger: "bg-danger text-white hover:bg-danger/90",
      },
      size: {
        md: "text-base",
        lg: "min-h-12 px-6 text-lg",
        icon: "min-w-touch px-0",
      },
      block: { true: "w-full" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonProps = ComponentPropsWithoutRef<"button"> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean; loading?: boolean };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, block, asChild, loading, disabled, children, ...props },
  ref,
) {
  const classes = cn(buttonVariants({ variant, size, block }), className);
  // Slot exige un unique enfant : pas d'indicateur de chargement en mode asChild.
  if (asChild) {
    return (
      <Slot ref={ref} className={classes} {...props}>
        {children}
      </Slot>
    );
  }
  return (
    <button
      ref={ref}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Spinner className="size-4" /> : null}
      {children}
    </button>
  );
});

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <span
      role={label ? "status" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className={cn(
        "inline-block size-5 animate-spin rounded-full border-2 border-current border-r-transparent",
        className,
      )}
    />
  );
}

export const Card = forwardRef<HTMLDivElement, ComponentPropsWithoutRef<"div">>(function Card(
  { className, ...props },
  ref,
) {
  return (
    <div ref={ref} className={cn("border-border bg-surface rounded-xl border p-4", className)} {...props} />
  );
});

const fieldControl =
  "min-h-touch w-full rounded-lg border border-border bg-surface px-3 text-base text-fg placeholder:text-muted aria-[invalid=true]:border-danger";

export const Input = forwardRef<HTMLInputElement, ComponentPropsWithoutRef<"input">>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(fieldControl, className)} {...props} />;
});

/** Liste native : légère et adaptée aux claviers / lecteurs d'écran des téléphones. */
export const Select = forwardRef<HTMLSelectElement, ComponentPropsWithoutRef<"select">>(function Select(
  { className, ...props },
  ref,
) {
  return <select ref={ref} className={cn(fieldControl, "appearance-auto", className)} {...props} />;
});

type FieldProps = {
  label: ReactNode;
  error?: string;
  hint?: ReactNode;
  className?: string;
  children: (ids: { id: string; describedBy?: string; invalid: boolean }) => ReactNode;
};

/** Libellé + contrôle + aide + erreur, reliés pour l'accessibilité. */
export function Field({ label, error, hint, className, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-semibold">
        {label}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint ? (
        <p id={hintId} className="text-muted text-sm">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-danger text-sm font-medium">
          {error}
        </p>
      ) : null}
    </div>
  );
}

type ChoiceOption<T extends string> = { value: T; label: ReactNode; description?: ReactNode };

type ChoiceGroupProps<T extends string> = {
  legend: ReactNode;
  options: ChoiceOption<T>[];
  columns?: 1 | 2 | 3 | 4;
  error?: string;
  className?: string;
} & (
  | { multiple?: false; value: T | null; onChange: (value: T) => void }
  | { multiple: true; value: T[]; onChange: (value: T[]) => void }
);

/** Choix en grosses tuiles (radio ou cases à cocher natives, accessibles au clavier). */
export function ChoiceGroup<T extends string>(props: ChoiceGroupProps<T>) {
  const { legend, options, columns = 2, error, className } = props;
  const name = useId();
  const isChecked = (v: T) => (props.multiple ? props.value.includes(v) : props.value === v);
  const toggle = (v: T) => {
    if (props.multiple) {
      props.onChange(props.value.includes(v) ? props.value.filter((x) => x !== v) : [...props.value, v]);
    } else {
      props.onChange(v);
    }
  };
  const grid = { 1: "grid-cols-1", 2: "grid-cols-2", 3: "grid-cols-3", 4: "grid-cols-2 sm:grid-cols-4" }[
    columns
  ];
  return (
    <fieldset className={cn("flex flex-col gap-2", className)} aria-invalid={Boolean(error) || undefined}>
      <legend className="mb-2 text-sm font-semibold">{legend}</legend>
      <div className={cn("grid gap-2", grid)}>
        {options.map((option) => (
          <label
            key={option.value}
            className={cn(
              "min-h-touch border-border bg-surface flex cursor-pointer flex-col justify-center rounded-lg border-2 px-3 py-2 transition-colors",
              "has-[:focus-visible]:outline-ring has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px]",
              isChecked(option.value) && "border-primary bg-primary-soft",
            )}
          >
            <input
              type={props.multiple ? "checkbox" : "radio"}
              name={name}
              value={option.value}
              checked={isChecked(option.value)}
              onChange={() => toggle(option.value)}
              className="sr-only"
            />
            <span className="font-semibold">{option.label}</span>
            {option.description ? <span className="text-muted text-sm">{option.description}</span> : null}
          </label>
        ))}
      </div>
      {error ? (
        <p role="alert" className="text-danger text-sm font-medium">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

export function Alert({
  tone = "danger",
  className,
  children,
}: {
  tone?: "danger" | "success" | "info";
  className?: string;
  children: ReactNode;
}) {
  const tones = {
    danger: "border-danger/40 bg-danger-soft",
    success: "border-success/40 bg-success-soft",
    info: "border-primary/30 bg-primary-soft",
  };
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("rounded-lg border p-3 text-sm", tones[tone], className)}
    >
      {children}
    </div>
  );
}

export function ProgressBar({
  value,
  label,
  className,
}: {
  value: number;
  label: string;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      className={cn("bg-surface-2 h-2 w-full overflow-hidden rounded-full", className)}
    >
      <div className="bg-primary h-full rounded-full transition-[width]" style={{ width: `${clamped}%` }} />
    </div>
  );
}
