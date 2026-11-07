import { zodResolver } from "@hookform/resolvers/zod";
import {
  isApiError,
  useLogin,
  useRegister,
  type Level,
  type Serie,
  type SubjectCode,
} from "@stem/api-client";
import { Alert, Button, ChoiceGroup, Field, Input, ProgressBar } from "@stem/ui";
import { useState } from "react";
import { Controller, useForm, type FieldPath } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { PasswordInput } from "@/components/PasswordInput";
import { applyFieldErrors, errorMessage } from "@/lib/errors";
import { isValidPhone, normalizePhone } from "@/lib/phone";
import { setPreferences } from "@/lib/preferences";
import { paths } from "@/paths";
import { HIGH_SCHOOL_LEVELS, LEVELS, SERIES, SUBJECTS, t, type Goal } from "@/strings/fr";

const schema = z
  .object({
    phone: z.string().refine(isValidPhone, t.auth.phoneInvalid),
    pseudo: z.string().trim().min(1, t.register.pseudoRequired).max(30, t.register.pseudoTooLong),
    password: z.string().min(8, t.register.passwordTooShort),
    level: z.custom<Level>((v) => typeof v === "string" && v !== "", t.register.levelRequired),
    serie: z.custom<Serie | "">(),
    subjects: z.array(z.custom<SubjectCode>()),
    goal: z.custom<Goal>().nullable(),
  })
  .refine((v) => !HIGH_SCHOOL_LEVELS.includes(v.level) || v.serie !== "", {
    path: ["serie"],
    message: t.register.serieRequired,
  });

type Values = z.infer<typeof schema>;

// Champs validés à chaque étape ; les erreurs du serveur ramènent à l'étape du champ fautif.
const STEP_FIELDS: FieldPath<Values>[][] = [
  ["phone", "pseudo", "password"],
  ["level", "serie"],
  ["subjects"],
  ["goal"],
];
const SERVER_FIELDS: FieldPath<Values>[] = ["phone", "pseudo", "password", "level", "serie"];

const defaultGoal = (level: Level | undefined): Goal =>
  level === "3e" ? "bepc" : level === "Tle" ? "bac" : "devoirs";

/**
 * Onboarding : compte → classe (et série au lycée) → matières → objectif.
 * Tout est envoyé à la dernière étape : l'API ne stocke que téléphone, pseudo, mot de passe, niveau et série ;
 * matières et objectif restent des préférences locales.
 */
export function RegisterPage() {
  const [step, setStep] = useState(0);
  const [failure, setFailure] = useState<string | null>(null);
  const navigate = useNavigate();
  const registerUser = useRegister();
  const login = useLogin();

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      phone: "",
      pseudo: "",
      password: "",
      serie: "",
      subjects: ["maths", "physique_chimie"],
      goal: null,
    },
    mode: "onTouched",
  });
  const { register, control, handleSubmit, trigger, watch, setValue, setError, formState } = form;
  const { errors } = formState;
  const level = watch("level");
  const total = STEP_FIELDS.length;

  const next = async () => {
    if (!(await trigger(STEP_FIELDS[step]))) return;
    if (step === 1 && form.getValues("goal") === null) setValue("goal", defaultGoal(level));
    setStep((s) => s + 1);
  };

  const onSubmit = handleSubmit(async (values) => {
    setFailure(null);
    const phone = normalizePhone(values.phone);
    const serie = HIGH_SCHOOL_LEVELS.includes(values.level) ? values.serie : "";
    try {
      await registerUser.mutateAsync({
        phone,
        pseudo: values.pseudo.trim(),
        password: values.password,
        level: values.level,
        serie,
      });
    } catch (error) {
      if (applyFieldErrors(error, setError, SERVER_FIELDS) && isApiError(error)) {
        const fields = Object.keys(error.fieldErrors);
        setStep(
          Math.max(
            0,
            STEP_FIELDS.findIndex((group) => group.some((f) => fields.includes(f))),
          ),
        );
      } else {
        setFailure(errorMessage(error));
      }
      return;
    }
    setPreferences({ subjects: values.subjects, goal: values.goal });
    try {
      await login.mutateAsync({ phone, password: values.password });
    } catch {
      navigate(paths.login, { replace: true, state: { notice: t.register.accountCreatedLoginFailed } });
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <p className="text-muted text-sm font-semibold">{t.register.stepLabel(step + 1, total)}</p>
        <ProgressBar value={((step + 1) / total) * 100} label={t.register.stepLabel(step + 1, total)} />
      </div>

      {failure ? <Alert>{failure}</Alert> : null}

      {step === 0 ? (
        <>
          <header>
            <h1 className="text-2xl font-bold">{t.register.accountTitle}</h1>
            <p className="text-muted mt-1">{t.register.accountSubtitle}</p>
          </header>
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
          <Field label={t.register.pseudo} hint={t.register.pseudoHint} error={errors.pseudo?.message}>
            {({ id, describedBy, invalid }) => (
              <Input
                id={id}
                autoComplete="nickname"
                maxLength={30}
                aria-describedby={describedBy}
                aria-invalid={invalid}
                {...register("pseudo")}
              />
            )}
          </Field>
          <Field label={t.auth.password} hint={t.register.passwordHint} error={errors.password?.message}>
            {({ id, describedBy, invalid }) => (
              <PasswordInput
                id={id}
                autoComplete="new-password"
                aria-describedby={describedBy}
                aria-invalid={invalid}
                {...register("password")}
              />
            )}
          </Field>
        </>
      ) : null}

      {step === 1 ? (
        <>
          <h1 className="text-2xl font-bold">{t.register.levelTitle}</h1>
          <Controller
            control={control}
            name="level"
            render={({ field }) => (
              <ChoiceGroup
                legend={t.register.level}
                columns={4}
                options={LEVELS}
                value={field.value ?? null}
                onChange={field.onChange}
                error={errors.level?.message}
              />
            )}
          />
          {level && HIGH_SCHOOL_LEVELS.includes(level) ? (
            <Controller
              control={control}
              name="serie"
              render={({ field }) => (
                <ChoiceGroup
                  legend={t.register.serie}
                  columns={3}
                  options={SERIES.map((s) => ({ value: s, label: `Série ${s}` }))}
                  value={field.value || null}
                  onChange={field.onChange}
                  error={errors.serie?.message}
                />
              )}
            />
          ) : null}
        </>
      ) : null}

      {step === 2 ? (
        <>
          <h1 className="text-2xl font-bold">{t.register.subjectsTitle}</h1>
          <Controller
            control={control}
            name="subjects"
            render={({ field }) => (
              <ChoiceGroup
                multiple
                legend={t.register.subjects}
                options={SUBJECTS.filter((s) => s.available)}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <p className="text-muted text-sm">{t.register.subjectsSoon}</p>
        </>
      ) : null}

      {step === 3 ? (
        <>
          <h1 className="text-2xl font-bold">{t.register.goalTitle}</h1>
          <Controller
            control={control}
            name="goal"
            render={({ field }) => (
              <ChoiceGroup
                legend={t.register.goal}
                columns={1}
                options={(Object.keys(t.register.goals) as Goal[]).map((g) => ({
                  value: g,
                  ...t.register.goals[g],
                }))}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </>
      ) : null}

      <div className="flex gap-3">
        {step > 0 ? (
          <Button type="button" variant="secondary" size="lg" onClick={() => setStep((s) => s - 1)}>
            {t.common.back}
          </Button>
        ) : null}
        {step < total - 1 ? (
          <Button type="button" size="lg" block onClick={next}>
            {t.common.next}
          </Button>
        ) : (
          <Button type="submit" size="lg" block loading={formState.isSubmitting}>
            {t.register.finish}
          </Button>
        )}
      </div>

      {step === 0 ? (
        <p className="text-muted text-center text-sm">
          {t.auth.hasAccount}{" "}
          <Link to={paths.login} className="text-primary font-semibold underline-offset-4 hover:underline">
            {t.auth.login}
          </Link>
        </p>
      ) : null}
    </form>
  );
}
