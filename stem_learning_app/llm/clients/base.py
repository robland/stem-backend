import base64
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pydantic import BaseModel

from llm.prompts.base import RenderedPrompt

T = TypeVar("T", bound=BaseModel)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str

    def __post_init__(self):
        if self.mime_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Type d'image non supporté : {self.mime_type}")

    def data_url(self):
        return f"data:{self.mime_type};base64,{base64.b64encode(self.data).decode('ascii')}"


@dataclass(frozen=True)
class LLMResult(Generic[T]):
    output: T
    model: str
    prompt_id: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(ABC):
    """Contrat commun aux fournisseurs : une sortie toujours structurée et validée par Pydantic."""

    def model_for(self, task):
        try:
            return settings.LLM_MODELS[task]
        except KeyError:
            raise ImproperlyConfigured(f"Aucun modèle LLM configuré pour la tâche « {task} » (LLM_MODELS).")

    @abstractmethod
    def generate(
        self,
        *,
        task: str,
        prompt: RenderedPrompt,
        output_schema: type[T],
        images: Sequence[ImageInput] = (),
    ) -> LLMResult[T]:
        """Lève LLMError (ou une sous-classe) en cas d'échec ; ne renvoie jamais de sortie non validée."""
