from django.contrib import admin
from django.urls import include, path

from core.views import healthcheck

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', healthcheck, name='healthcheck'),
    path('api/', include('api.urls')),
]
