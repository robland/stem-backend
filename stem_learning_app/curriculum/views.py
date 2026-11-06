from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets

from .choices import Level, SubjectCode
from .models import Subject, Chapter
from .serializers import SubjectSerializer, ChapterSerializer


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    lookup_field = "code"
    pagination_class = None


@extend_schema(parameters=[
    OpenApiParameter("subject", str, enum=SubjectCode.values, description="Code de la matière"),
    OpenApiParameter("level", str, enum=Level.values, description="Niveau scolaire"),
])
class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChapterSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Chapter.objects.select_related("subject")
        subject = self.request.query_params.get("subject")
        level = self.request.query_params.get("level")

        if subject:
            queryset = queryset.filter(subject__code=subject)
        if level:
            queryset = queryset.filter(level=level)

        return queryset
