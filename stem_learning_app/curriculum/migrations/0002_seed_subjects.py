from django.db import migrations

# Référentiel figé des matières (README §1). Les chapitres du programme congolais
# sont ajoutés séparément, à partir des programmes officiels.
SUBJECTS = [
    ("maths", "Mathématiques"),
    ("physique_chimie", "Physique-Chimie"),
    ("svt", "Sciences de la Vie et de la Terre"),
    ("francais", "Français"),
    ("anglais", "Anglais"),
    ("histoire_geo", "Histoire-Géographie"),
]


def seed_subjects(apps, schema_editor):
    Subject = apps.get_model("curriculum", "Subject")
    for order, (code, name) in enumerate(SUBJECTS):
        Subject.objects.update_or_create(code=code, defaults={"name": name, "order": order})


def unseed_subjects(apps, schema_editor):
    Subject = apps.get_model("curriculum", "Subject")
    Subject.objects.filter(code__in=[code for code, _ in SUBJECTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_subjects, unseed_subjects),
    ]
