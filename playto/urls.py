from django.contrib import admin
from django.urls import path, include
from api.auth_views import CSRFView, LoginView, LogoutView, MeView
from payouts.views import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', HealthCheckView.as_view(), name='health-check'),
    path('api/', include('api.urls')),
    path('api/auth/csrf/', CSRFView.as_view(), name='auth-csrf'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/auth/me/', MeView.as_view(), name='auth-me'),
]
