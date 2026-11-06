from django.db import models


class Level(models.TextChoices):
    SIXIEME = "6e", "6e"
    CINQUIEME = "5e", "5e"
    QUATRIEME = "4e", "4e"
    TROISIEME = "3e", "3e"
    SECONDE = "2nde", "2nde"
    PREMIERE = "1re", "1re"
    TERMINALE = "Tle", "Terminale"


COLLEGE_LEVELS = {Level.SIXIEME, Level.CINQUIEME, Level.QUATRIEME, Level.TROISIEME}


class SubjectCode(models.TextChoices):
    MATHS = "maths", "Mathématiques"
    PHYSIQUE_CHIMIE = "physique_chimie", "Physique-Chimie"
    SVT = "svt", "Sciences de la Vie et de la Terre"
    FRANCAIS = "francais", "Français"
    ANGLAIS = "anglais", "Anglais"
    HISTOIRE_GEO = "histoire_geo", "Histoire-Géographie"
