from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContribuableViewSet, ImpotViewSet, DeclarationViewSet,
    PaiementViewSet, PenaliteViewSet, NotificationViewSet,
    DashboardView, RegisterView, RevenusMensuelView,
    UserListView, UserToggleActiveView, UserProfileView
)

router = DefaultRouter()
router.register(r'contribuables', ContribuableViewSet, basename='contribuable')
router.register(r'impots', ImpotViewSet, basename='impot')
router.register(r'declarations', DeclarationViewSet, basename='declaration')
router.register(r'paiements', PaiementViewSet, basename='paiement')
router.register(r'penalites', PenaliteViewSet, basename='penalite')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/revenus-mensuels/', RevenusMensuelView.as_view(), name='revenus-mensuels'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('users/', UserListView.as_view(), name='users'),
    path('users/<int:pk>/toggle-active/', UserToggleActiveView.as_view(), name='user-toggle-active'),  # <-- CORRIGÉ
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]