from django.urls import path
from apps.accounts.views import RegisterView, LoginView, LogoutView, MeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('register', RegisterView.as_view(), name='auth-register-noslash'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('login', LoginView.as_view(), name='auth-login-noslash'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('logout', LogoutView.as_view(), name='auth-logout-noslash'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('me', MeView.as_view(), name='auth-me-noslash'),
    path('session/', MeView.as_view(), name='auth-session'),
    path('session', MeView.as_view(), name='auth-session-noslash'),
]
