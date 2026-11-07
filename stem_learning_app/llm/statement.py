"""Analyse légère d'un énoncé (sans LLM), partagée par la génération et la revérification."""

import re

# Questions numérotées en début de ligne : « 1) », « 2. », « a) », « b- ».
QUESTION_RE = re.compile(r"^\s*(?:\d{1,2}|[a-h])\s*[).-]\s", re.MULTILINE)


def count_questions(statement):
    return len(QUESTION_RE.findall(statement or ""))
