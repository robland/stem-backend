import { Button } from "@stem/ui";
import { Square, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { speakable } from "@/lib/speech";
import { t } from "@/strings/fr";

/** Lecture audio par la synthèse vocale de l'appareil (README frontend §2, accessibilité). */
export function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  useEffect(() => () => void (supported && window.speechSynthesis.cancel()), [supported]);
  if (!supported) return null;

  const toggle = () => {
    window.speechSynthesis.cancel();
    if (speaking) return setSpeaking(false);
    const utterance = new SpeechSynthesisUtterance(speakable(text));
    utterance.lang = "fr-FR";
    utterance.onend = utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };
  const Icon = speaking ? Square : Volume2;
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={speaking ? t.reader.stopListening : t.reader.listen}
      aria-pressed={speaking}
    >
      <Icon aria-hidden className="size-5" />
    </Button>
  );
}
