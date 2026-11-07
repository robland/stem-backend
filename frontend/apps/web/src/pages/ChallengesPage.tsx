import { ComingSoon, PageHeader } from "@/components/PageHeader";
import { t } from "@/strings/fr";

export function ChallengesPage() {
  return (
    <>
      <PageHeader title={t.challenges.title} />
      <ComingSoon>{t.challenges.soon}</ComingSoon>
    </>
  );
}
