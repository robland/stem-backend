from rest_framework.routers import DefaultRouter

from .views import SubjectViewSet, ChapterViewSet

router = DefaultRouter()
router.register(r"subjects", SubjectViewSet, basename="subject")
router.register(r"chapters", ChapterViewSet, basename="chapter")

urlpatterns = router.urls
