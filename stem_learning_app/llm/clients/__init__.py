from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string

from .base import ImageInput, LLMClient, LLMResult

__all__ = ["ImageInput", "LLMClient", "LLMResult", "get_client"]


@cache
def _build_client(dotted_path):
    return import_string(dotted_path)()


def get_client() -> LLMClient:
    """Client configuré par settings.LLM_CLIENT (instance partagée par processus)."""
    return _build_client(settings.LLM_CLIENT)
