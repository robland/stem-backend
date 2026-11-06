from django.urls import path
from rest_framework.routers import DefaultRouter

from .attempt_views import AttemptViewSet, SyncView
from .views import ExerciseViewSet

router = DefaultRouter()
router.register("exercises", ExerciseViewSet, basename="exercise")
router.register("attempts", AttemptViewSet, basename="attempt")

urlpatterns = router.urls + [path("sync/", SyncView.as_view(), name="sync")]
