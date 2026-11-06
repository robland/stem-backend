import pytest
from django.db import IntegrityError
from django.urls import reverse

from curriculum.choices import SubjectCode
from curriculum.models import Subject, Chapter

pytestmark = pytest.mark.django_db


@pytest.fixture
def maths():
    return Subject.objects.get(code="maths")


@pytest.fixture
def chapters(maths):
    pc = Subject.objects.get(code="physique_chimie")
    return [
        Chapter.objects.create(subject=maths, level="3e", name="Fonctions affines", order=2),
        Chapter.objects.create(subject=maths, level="3e", name="Théorème de Thalès", order=1),
        Chapter.objects.create(subject=maths, level="Tle", name="Fonctions logarithmes", order=1),
        Chapter.objects.create(subject=pc, level="3e", name="Fonctions affines"),
    ]


class TestSubjectsSeed:
    def test_all_subjects_are_created_by_migration(self):
        assert set(Subject.objects.values_list("code", flat=True)) == set(SubjectCode.values)


class TestChapterConstraints:
    def test_same_name_allowed_in_another_subject_or_level(self, chapters):
        assert Chapter.objects.filter(name="Fonctions affines").count() == 2

    def test_duplicate_in_same_subject_and_level_is_rejected(self, maths, chapters):
        with pytest.raises(IntegrityError):
            Chapter.objects.create(subject=maths, level="3e", name="Fonctions affines")


class TestCurriculumApi:
    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("subject-list")).status_code == 401

    def test_lists_subjects_in_order(self, auth_client):
        response = auth_client.get(reverse("subject-list"))

        assert response.status_code == 200
        assert [s["code"] for s in response.data][:2] == ["maths", "physique_chimie"]

    def test_subject_detail_by_code(self, auth_client):
        response = auth_client.get(reverse("subject-detail", args=["svt"]))

        assert response.data == {"code": "svt", "name": "Sciences de la Vie et de la Terre"}

    def test_filters_chapters_by_subject_and_level(self, auth_client, chapters):
        response = auth_client.get(reverse("chapter-list"), {"subject": "maths", "level": "3e"})

        assert [c["name"] for c in response.data] == ["Théorème de Thalès", "Fonctions affines"]
        assert {c["subject"] for c in response.data} == {"maths"}

    def test_is_read_only(self, auth_client, maths):
        response = auth_client.post(reverse("chapter-list"), {"name": "x", "level": "3e"}, format="json")

        assert response.status_code == 405
