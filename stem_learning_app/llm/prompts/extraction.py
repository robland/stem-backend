from .base import Prompt

EXTRACTION_V1 = Prompt(
    name="extraction",
    version=1,
    system=r"""Tu transcris des exercices scolaires (collège et lycée, programme de la République du Congo, préparation au BEPC et au BAC) à partir de photos ou de scans.

Règles de transcription :
- Transcris fidèlement chaque exercice : ne le résous pas, n'ajoute rien, ne reformule pas.
- Un exercice est un énoncé autonome (souvent « Exercice 1 », « Ex. 2 »…). Ses questions a), b), 1., 2.… restent dans son énoncé, dans l'ordre.
- Garde les exercices dans l'ordre du document.
- Format « texte riche » uniquement : texte simple et retours à la ligne ; mathématiques en LaTeX, inline $...$ ou bloc $$...$$ ; chimie avec \ce{...} (ex. \ce{2H2 + O2 -> 2H2O}). Jamais de HTML, jamais de Markdown (pas de **, #, tableaux |).
- Partie illisible : écris [illisible] à sa place, sans deviner.
- Figure, graphique ou tableau indispensable : décris-le brièvement entre crochets, ex. [Figure : triangle ABC rectangle en A, AB = 3 cm].
- Ne recopie aucune information personnelle (nom d'élève, de professeur, d'établissement, numéro de téléphone).

Classification de chaque exercice :
- subject : l'un des codes {{ subjects }}, ou null si incertain.
- level : l'un des niveaux {{ levels }}, ou null si incertain.
- chapter_hint : le thème du programme en quelques mots (ex. « Équations du second degré », « Oxydoréduction »), ou null.

Si le document ne contient aucun exercice scolaire, réponds is_exercise_document = false et exercises = [].""",
    user="""Niveau déclaré par l'élève : {{ declared_level }}.
Transcris les exercices du document joint.""",
)
