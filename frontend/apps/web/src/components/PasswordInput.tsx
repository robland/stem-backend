import { Input } from "@stem/ui";
import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useState, type ComponentPropsWithoutRef } from "react";
import { t } from "@/strings/fr";

/** Mot de passe avec bouton « afficher » : saisie plus sûre sur petit clavier tactile. */
export const PasswordInput = forwardRef<HTMLInputElement, Omit<ComponentPropsWithoutRef<"input">, "type">>(
  function PasswordInput(props, ref) {
    const [visible, setVisible] = useState(false);
    const Icon = visible ? EyeOff : Eye;
    return (
      <div className="relative">
        <Input ref={ref} type={visible ? "text" : "password"} className="pr-12" {...props} />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? t.auth.hidePassword : t.auth.showPassword}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex min-w-touch items-center justify-center rounded-r-lg text-muted hover:text-fg"
        >
          <Icon aria-hidden className="size-5" />
        </button>
      </div>
    );
  },
);
