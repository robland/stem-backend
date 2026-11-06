from .base import Prompt, RenderedPrompt
from .extraction import EXTRACTION_V1
from .generation import GENERATION_V1

__all__ = ["PROMPTS", "Prompt", "RenderedPrompt", "latest_prompt"]

# Les anciennes versions restent enregistrées : l'identifiant (ex. "extraction.v1")
# est conservé avec chaque contenu produit pour pouvoir le retracer.
PROMPTS = {prompt.id: prompt for prompt in [EXTRACTION_V1, GENERATION_V1]}


def latest_prompt(name):
    versions = [p for p in PROMPTS.values() if p.name == name]
    if not versions:
        raise KeyError(f"Prompt inconnu : {name}")
    return max(versions, key=lambda p: p.version)
