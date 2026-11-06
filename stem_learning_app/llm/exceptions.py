class LLMError(Exception):
    """Échec d'un appel LLM (réseau, quota, réponse inexploitable)."""


class LLMRefusal(LLMError):
    """Le modèle a refusé de répondre (contenu jugé inapproprié)."""


class LLMOutputInvalid(LLMError):
    """La réponse ne respecte pas le schéma attendu (tronquée ou invalide).

    `errors` résume les erreurs de validation (« steps.0.activity.mcq: … ») pour
    permettre une relance corrective.
    """

    def __init__(self, message, errors=()):
        super().__init__(message)
        self.errors = list(errors)


def summarize_validation_error(error, limit=10):
    """Erreurs Pydantic → lignes courtes, sans recopier les valeurs reçues."""
    lines = []
    for item in error.errors()[:limit]:
        location = ".".join(str(part) for part in item["loc"]) or "racine"
        lines.append(f"{location}: {item['msg'].removeprefix('Value error, ')}")
    return lines
