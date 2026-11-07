import { zodResolver } from "@hookform/resolvers/zod";
import { isApiError, useLogin } from "@stem/api-client";
import { Alert, Button, Field, Input } from "@stem/ui";
import { useForm } from "react-hook-form";
import { Link, useLocation } from "react-router-dom";
import { z } from "zod";
import { PasswordInput } from "@/components/PasswordInput";
import { errorMessage } from "@/lib/errors";
import { isValidPhone, normalizePhone } from "@/lib/phone";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

const schema = z.object({
  phone: z.string().refine(isValidPhone, t.auth.phoneInvalid),
  password: z.string().min(1, t.auth.passwordRequired),
});

type Values = z.infer<typeof schema>;

export function LoginPage() {
  const login = useLogin();
  const notice = (useLocation().state as { notice?: string } | null)?.notice;
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) });
  const { errors } = formState;

  const onSubmit = handleSubmit(({ phone, password }) =>
    login.mutate({ phone: normalizePhone(phone), password }),
  );

  const failure = login.error
    ? isApiError(login.error) && login.error.status === 401
      ? t.auth.invalidCredentials
      : errorMessage(login.error)
    : null;

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-bold">{t.auth.loginTitle}</h1>
        <p className="mt-1 text-muted">{t.auth.loginSubtitle}</p>
      </header>

      {notice && !failure ? <Alert tone="info">{notice}</Alert> : null}
      {failure ? <Alert>{failure}</Alert> : null}

      <Field label={t.auth.phone} hint={t.auth.phoneHint} error={errors.phone?.message}>
        {({ id, describedBy, invalid }) => (
          <Input
            id={id}
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            aria-describedby={describedBy}
            aria-invalid={invalid}
            {...register("phone")}
          />
        )}
      </Field>

      <Field label={t.auth.password} error={errors.password?.message}>
        {({ id, describedBy, invalid }) => (
          <PasswordInput
            id={id}
            autoComplete="current-password"
            aria-describedby={describedBy}
            aria-invalid={invalid}
            {...register("password")}
          />
        )}
      </Field>

      <Button type="submit" size="lg" block loading={login.isPending}>
        {t.auth.login}
      </Button>

      <p className="text-center text-sm text-muted">
        {t.auth.noAccount}{" "}
        <Link to={paths.register} className="font-semibold text-primary underline-offset-4 hover:underline">
          {t.auth.createAccount}
        </Link>
      </p>
    </form>
  );
}
