from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from apps.accounts.urls import urlpatterns as accounts_urlpatterns
from apps.core.urls import api_urlpatterns, health_urlpatterns
from apps.posts.urls import urlpatterns as posts_urlpatterns

urlpatterns = [
    path("health/", include(health_urlpatterns)),
    path("api/v1/", include(api_urlpatterns)),
    path("api/v1/", include(accounts_urlpatterns)),
    path("api/v1/", include(posts_urlpatterns)),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
]

handler400 = "apps.core.errors.handler400"
handler403 = "apps.core.errors.handler403"
handler404 = "apps.core.errors.handler404"
handler500 = "apps.core.errors.handler500"
