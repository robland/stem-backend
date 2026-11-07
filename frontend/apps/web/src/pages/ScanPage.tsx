import { useCreateUpload } from "@stem/api-client";
import { Alert, Button, Card, cn } from "@stem/ui";
import { Camera, FileText, ImageUp, RotateCw } from "lucide-react";
import { useEffect, useState, type ChangeEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { ImageCropper } from "@/components/scan/ImageCropper";
import {
  FULL_CROP,
  isImage,
  isPdf,
  MAX_UPLOAD_BYTES,
  prepareImage,
  rotateImage,
  type CropRect,
  type Rotation,
} from "@/lib/image";
import { keepPhoto } from "@/lib/localPhotos";
import { quotaAwareMessage } from "@/lib/quota";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

type Draft =
  | { kind: "image"; source: Blob; oriented: Blob; rotation: Rotation; preview: string; crop: CropRect }
  | { kind: "pdf"; file: File };

/** Bouton-fichier : un vrai <input type="file"> (caméra du téléphone avec `capture`). */
function FileButton({
  children,
  accept,
  capture,
  primary,
  onFile,
}: {
  children: ReactNode;
  accept: string;
  capture?: boolean;
  primary?: boolean;
  onFile: (file: File) => void;
}) {
  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // permet de reprendre la même photo
    if (file) onFile(file);
  };
  return (
    <label
      className={cn(
        "flex min-h-14 cursor-pointer items-center justify-center gap-3 rounded-lg px-5 text-lg font-semibold transition-colors",
        "has-[:focus-visible]:outline-ring has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px]",
        primary
          ? "bg-primary text-primary-fg hover:bg-primary/90"
          : "border-border bg-surface hover:bg-surface-2 border",
      )}
    >
      <input
        type="file"
        accept={accept}
        capture={capture ? "environment" : undefined}
        onChange={onChange}
        className="sr-only"
      />
      {children}
    </label>
  );
}

export function ScanPage() {
  const navigate = useNavigate();
  const upload = useCreateUpload();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const preview = draft?.kind === "image" ? draft.preview : null;
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const choose = (file: File) => {
    setProblem(null);
    upload.reset();
    if (isPdf(file)) {
      if (file.size > MAX_UPLOAD_BYTES) setProblem(t.scan.tooBig);
      else setDraft({ kind: "pdf", file });
    } else if (isImage(file)) {
      setDraft({
        kind: "image",
        source: file,
        oriented: file,
        rotation: 0,
        preview: URL.createObjectURL(file),
        crop: FULL_CROP,
      });
    } else {
      setProblem(t.scan.unsupported);
    }
  };

  const rotate = async () => {
    if (draft?.kind !== "image") return;
    setBusy(true);
    try {
      const rotation = ((draft.rotation + 90) % 360) as Rotation;
      const oriented = await rotateImage(draft.source, rotation);
      setDraft({ ...draft, oriented, rotation, preview: URL.createObjectURL(oriented), crop: FULL_CROP });
    } catch {
      setProblem(t.scan.imageError);
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    if (!draft) return;
    setProblem(null);
    setBusy(true);
    let file: Blob;
    try {
      if (draft.kind === "pdf") {
        file = draft.file;
      } else {
        file = await prepareImage(draft.oriented, draft.crop);
      }
    } catch {
      setBusy(false);
      setProblem(t.scan.imageError);
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setBusy(false);
      setProblem(t.scan.tooBig);
      return;
    }
    upload.mutate(file, {
      onSuccess: (created) => {
        if (draft.kind === "image") keepPhoto(created.id, file);
        navigate(paths.scanUpload(created.id));
      },
      onSettled: () => setBusy(false),
    });
  };

  const failure = problem ?? (upload.error ? quotaAwareMessage(upload.error) : null);

  if (!draft) {
    return (
      <>
        <PageHeader title={t.scan.title} subtitle={t.scan.subtitle} />
        <div className="flex flex-col gap-4">
          {failure ? <Alert>{failure}</Alert> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <FileButton accept="image/*" capture primary onFile={choose}>
              <Camera aria-hidden className="size-6" />
              {t.scan.takePhoto}
            </FileButton>
            <FileButton accept="image/jpeg,image/png,image/webp,application/pdf" onFile={choose}>
              <ImageUp aria-hidden className="size-6" />
              {t.scan.importFile}
            </FileButton>
          </div>
          <Card>
            <ul className="text-muted flex list-disc flex-col gap-1 pl-5">
              {t.scan.tips.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={draft.kind === "image" ? t.scan.cropTitle : t.scan.title}
        subtitle={draft.kind === "image" ? t.scan.cropHint : undefined}
      />
      <div className="flex flex-col gap-4">
        {draft.kind === "image" ? (
          <ImageCropper
            src={draft.preview}
            crop={draft.crop}
            onChange={(crop) => setDraft({ ...draft, crop })}
            alt={t.scan.cropAlt}
          />
        ) : (
          <Card className="flex items-center gap-3">
            <FileText aria-hidden className="text-primary size-8 shrink-0" />
            <span className="break-all font-semibold">{t.scan.pdfReady(draft.file.name)}</span>
          </Card>
        )}

        {failure ? <Alert>{failure}</Alert> : null}

        <div className="flex flex-wrap gap-3">
          {draft.kind === "image" ? (
            <Button variant="secondary" onClick={rotate} disabled={busy}>
              <RotateCw aria-hidden className="size-5" />
              {t.scan.rotate}
            </Button>
          ) : null}
          <Button variant="secondary" onClick={() => setDraft(null)} disabled={busy}>
            {t.scan.retake}
          </Button>
          <Button size="lg" className="grow" onClick={send} loading={busy}>
            {busy ? t.scan.sending : t.scan.send}
          </Button>
        </div>
      </div>
    </>
  );
}
