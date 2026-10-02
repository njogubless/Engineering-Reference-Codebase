from django.urls import path

from apps.core import views

health_urlpatterns = [
    path("live", views.LivenessView.as_view(), name="health-live"),
    path("ready", views.ReadinessView.as_view(), name="health-ready"),
]

api_urlpatterns = [
    path("meta", views.MetaView.as_view(), name="meta"),
]
