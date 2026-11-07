from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

# Motifs de refus d'un énoncé avant publication au catalogue des défis (README §5.4).
ModerationReason = Literal["personal_data", "inappropriate", "not_schoolwork"]


class ModerationOutput(BaseModel):
    """Verdict sans texte libre : rien de l'énoncé n'est recopié (ni dans la réponse ni dans les journaux)."""

    model_config = ConfigDict(extra="forbid")

    acceptable: bool
    reasons: list[ModerationReason]

    @model_validator(mode="after")
    def _reasons_match_verdict(self):
        if self.acceptable and self.reasons:
            raise ValueError("Énoncé acceptable : aucun motif de refus attendu.")
        if not self.acceptable and not self.reasons:
            raise ValueError("Énoncé refusé : au moins un motif attendu.")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("Motifs en double.")
        return self
