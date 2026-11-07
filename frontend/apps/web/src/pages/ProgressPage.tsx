import { ComingSoon, PageHeader } from "@/components/PageHeader";
import { t } from "@/strings/fr";

export function ProgressPage() {
  return (
    <>
      <PageHeader title={t.progress.title} />
      <ComingSoon>{t.common.soon}</ComingSoon>
    </>
  );
}
