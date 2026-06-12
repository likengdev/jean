from rest_framework.permissions import BasePermission

class EstSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profil.role == 'superadmin'
        except Exception:  # <-- CORRIGÉ (était "except:")
            return request.user.is_superuser

class EstAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profil.role in ['superadmin', 'admin']
        except Exception:  # <-- CORRIGÉ
            return request.user.is_superuser

class EstGestionnaire(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            return request.user.profil.role in ['superadmin', 'admin', 'gestionnaire']
        except Exception:  # <-- CORRIGÉ
            return request.user.is_authenticated