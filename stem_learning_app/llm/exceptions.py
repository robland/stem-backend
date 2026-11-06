class LLMError(Exception):
    """Échec d'un appel LLM (réseau, quota, réponse inexploitable)."""


class LLMRefusal(LLMError):
    """Le modèle a refusé de répondre (contenu jugé inapproprié)."""


class LLMOutputInvalid(LLMError):
    """La réponse ne respecte pas le schéma attendu (tronquée ou invalide)."""
