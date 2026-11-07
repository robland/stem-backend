import { Button } from "@stem/ui";
import { Link } from "react-router-dom";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-lg">{t.notFound}</p>
      <Button asChild>
        <Link to={paths.home}>{t.backHome}</Link>
      </Button>
    </main>
  );
}
