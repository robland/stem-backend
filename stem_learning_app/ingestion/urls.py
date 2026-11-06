from rest_framework.routers import DefaultRouter

from .views import ExtractedExerciseViewSet, UploadViewSet

router = DefaultRouter()
router.register("uploads", UploadViewSet, basename="upload")
router.register("extracted-exercises", ExtractedExerciseViewSet, basename="extracted-exercise")

urlpatterns = router.urls
