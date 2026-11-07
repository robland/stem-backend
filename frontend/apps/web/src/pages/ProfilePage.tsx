import { useLogout, useMe, useUpdateMe, type Level, type Me } from "@stem/api-client";
import { Alert, Button, Card, ChoiceGroup, Field, Input, Select, Spinner } from "@stem/ui";
import { useForm } from "react-hook-form";
import { PageHeader } from "@/components/PageHeader";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { setPreferences, usePreferences, type Theme } from "@/lib/preferences";
import { HIGH_SCHOOL_LEVELS, LEVELS, SERIES, t } from "@/strings/fr";

export function ProfilePage() {
  const me = useMe();
  const logout = useLogout();
  return (
    <>
      <PageHeader title={t.profile.title} />
      <div className="flex flex-col gap-5">
        {me.data ? <AccountForm me={me.data} /> : <Spinner label={t.common.loading} />}
        <PreferencesCard />
        <Button variant="secondary" size="lg" onClick={() => logout.mutate()} loading={logout.isPending}>
          {t.profile.logout}
        </Button>
      </div>
    </>
  );
}

type AccountValues = { pseudo: string; level: Level | ""; serie: string };

function AccountForm({ me }: { me: Me }) {
  const update = useUpdateMe();
  const { register, handleSubmit, watch, setError, formState } = useForm<AccountValues>({
    values: { pseudo: me.pseudo, level: me.level ?? "", serie: me.serie ?? "" },
  });
  const level = watch("level");
  const isHighSchool = level !== "" && HIGH_SCHOOL_LEVELS.includes(level);

  const onSubmit = handleSubmit((values) =>
    update.mutate(
      { pseudo: values.pseudo.trim(), level: values.level, serie: isHighSchool ? values.serie : "" },
      { onError: (error) => applyFieldErrors(error, setError, ["pseudo", "level", "serie"]) },
    ),
  );

  return (
    <Card>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <h2 className="text-lg font-bold">{t.profile.account}</h2>
        <p className="text-muted text-sm">
          {t.profile.phone} : <span className="text-fg font-semibold">{me.phone}</span>
        </p>
        <Field
          label={t.register.pseudo}
          hint={t.register.pseudoHint}
          error={formState.errors.pseudo?.message}
        >
          {({ id, describedBy, invalid }) => (
            <Input
              id={id}
              maxLength={30}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              {...register("pseudo", { required: t.register.pseudoRequired })}
            />
          )}
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t.register.level} error={formState.errors.level?.message}>
            {({ id, invalid }) => (
              <Select id={id} aria-invalid={invalid} {...register("level")}>
                {LEVELS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {isHighSchool ? (
            <Field label={t.register.serie} error={formState.errors.serie?.message}>
              {({ id, invalid }) => (
                <Select id={id} aria-invalid={invalid} {...register("serie")}>
                  <option value="">—</option>
                  {SERIES.map((s) => (
                    <option key={s} value={s}>
                      Série {s}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
        </div>
        {update.isError && !Object.keys(formState.errors).length ? (
          <Alert>{errorMessage(update.error)}</Alert>
        ) : null}
        {update.isSuccess && !formState.isDirty ? <Alert tone="success">{t.common.saved}</Alert> : null}
        <Button type="submit" loading={update.isPending} disabled={!formState.isDirty} className="self-start">
          {t.common.save}
        </Button>
      </form>
    </Card>
  );
}

function PreferencesCard() {
  const prefs = usePreferences();
  return (
    <Card className="flex flex-col gap-4">
      <h2 className="text-lg font-bold">{t.profile.preferences}</h2>
      <ChoiceGroup<Theme>
        legend={t.profile.theme}
        columns={3}
        value={prefs.theme}
        onChange={(theme) => setPreferences({ theme })}
        options={(Object.keys(t.profile.themes) as Theme[]).map((value) => ({
          value,
          label: t.profile.themes[value],
        }))}
      />
      <label className="min-h-touch flex cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={prefs.dyslexicFont}
          onChange={(e) => setPreferences({ dyslexicFont: e.target.checked })}
          className="mt-1 size-5 accent-[rgb(var(--primary))]"
        />
        <span>
          <span className="font-semibold">{t.profile.dyslexicFont}</span>
          <span className="text-muted block text-sm">{t.profile.dyslexicFontHint}</span>
        </span>
      </label>
    </Card>
  );
}
