import django_prometheus
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from kvstore.views import KeyValueViewSet

router = DefaultRouter()
router.register(r'kv', KeyValueViewSet, basename='keyvalue')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('metrics/', include('django_prometheus.urls')),
]