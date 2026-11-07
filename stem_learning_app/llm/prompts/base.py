import re
from dataclasses import dataclass

# {{ variable }} plutôt que str.format / string.Template : les prompts contiennent
# des accolades et des dollars LaTeX ($\frac{a}{b}$, \ce{H2O}).
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class RenderedPrompt:
    id: str
    system: str
    user: str


@dataclass(frozen=True)
class Prompt:
    """Un prompt publié est immuable : toute modification donne une nouvelle version."""

    name: str
    version: int
    system: str
    user: str

    @property
    def id(self):
        return f"{self.name}.v{self.version}"

    @property
    def variables(self):
        return set(PLACEHOLDER_RE.findall(self.system)) | set(PLACEHOLDER_RE.findall(self.user))

    def render(self, **context):
        missing = self.variables - context.keys()
        unknown = context.keys() - self.variables
        if missing or unknown:
            raise ValueError(
                f"Variables invalides pour le prompt {self.id} : "
                f"manquantes={sorted(missing)}, inconnues={sorted(unknown)}"
            )

        def substitute(text):
            return PLACEHOLDER_RE.sub(lambda m: str(context[m.group(1)]), text)

        return RenderedPrompt(id=self.id, system=substitute(self.system), user=substitute(self.user))
