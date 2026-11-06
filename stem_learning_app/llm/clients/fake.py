from pydantic import ValidationError

from llm.exceptions import LLMOutputInvalid, summarize_validation_error

from .base import LLMClient, LLMResult


class FakeLLMClient(LLMClient):
    """Client de test : renvoie des réponses mises en file, sans aucun appel réseau.

    Une réponse est un dict (validé par le schéma demandé, comme le ferait le SDK),
    une instance Pydantic, ou une exception à lever.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.responses = []
        self.calls = []

    def queue(self, *responses):
        self.responses.extend(responses)

    def generate(self, *, task, prompt, output_schema, images=()):
        self.calls.append({"task": task, "prompt": prompt, "schema": output_schema, "images": list(images)})
        if not self.responses:
            raise AssertionError(f"FakeLLMClient : aucune réponse en file pour {prompt.id}.")

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, dict):
            try:
                response = output_schema.model_validate(response)
            except ValidationError as e:
                raise LLMOutputInvalid(
                    f"Réponse LLM hors schéma ({prompt.id}).", summarize_validation_error(e)
                ) from e
        return LLMResult(output=response, model=self.model_for(task), prompt_id=prompt.id)
