import { ComingSoon, PageHeader } from "@/components/PageHeader";
import { t } from "@/strings/fr";

export function ScanPage() {
  return (
    <>
      <PageHeader title={t.scan.title} />
      <ComingSoon>{t.common.soon}</ComingSoon>
    </>
  );
}
