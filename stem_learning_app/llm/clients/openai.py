import logging
import time

import openai
from django.conf import settings
from pydantic import ValidationError

from llm.exceptions import LLMError, LLMOutputInvalid, LLMRefusal, summarize_validation_error

from .base import LLMClient, LLMResult

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """Structured outputs OpenAI : le JSON Schema strict est dérivé du modèle Pydantic par le SDK."""

    def __init__(self, sdk_client=None):
        self._sdk = sdk_client or openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )

    def generate(self, *, task, prompt, output_schema, images=()):
        model = self.model_for(task)
        user_content = [{"type": "text", "text": prompt.user}]
        user_content += [
            {"type": "image_url", "image_url": {"url": image.data_url(), "detail": "high"}}
            for image in images
        ]
        messages = [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": user_content},
        ]

        started = time.monotonic()
        try:
            completion = self._sdk.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=output_schema,
                temperature=0,
            )
        except (openai.LengthFinishReasonError, openai.ContentFilterFinishReasonError) as e:
            raise LLMOutputInvalid(f"Réponse LLM tronquée ou filtrée ({prompt.id}).") from e
        except ValidationError as e:
            raise LLMOutputInvalid(
                f"Réponse LLM hors schéma ({prompt.id}).", summarize_validation_error(e)
            ) from e
        except openai.OpenAIError as e:
            raise LLMError(f"Appel LLM en échec ({prompt.id}) : {type(e).__name__}") from e

        message = completion.choices[0].message
        if message.refusal:
            raise LLMRefusal(f"Le modèle a refusé de répondre ({prompt.id}).")
        if message.parsed is None:
            raise LLMOutputInvalid(f"Réponse LLM vide ({prompt.id}).")

        usage = completion.usage
        result = LLMResult(
            output=message.parsed,
            model=completion.model,
            prompt_id=prompt.id,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
        # Jamais le contenu (énoncés d'élèves) dans les logs : uniquement des métriques de coût.
        logger.info(
            "llm task=%s prompt=%s model=%s images=%d in=%d out=%d duration=%.1fs",
            task, prompt.id, result.model, len(images),
            result.input_tokens, result.output_tokens, time.monotonic() - started,
        )
        return result
