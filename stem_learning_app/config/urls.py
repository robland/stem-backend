from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from accounts.views import MeView


urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name="swagger-ui"),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('admin/', admin.site.urls),
    path('api/auth/', include("accounts.urls")),
    path('api/me/', MeView.as_view(), name="me"),
    path('api/curriculum/', include("curriculum.urls")),
    path('api/', include("ingestion.urls")),
    path('api/', include("learning.urls")),
]

# Les médias ne sont servis par Django qu'en développement (static() ne fait rien si DEBUG=False).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
