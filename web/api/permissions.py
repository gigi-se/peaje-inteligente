from rest_framework.permissions import SAFE_METHODS, BasePermission


class AdminEscribe_TodosLeen(BasePermission):
    """Lectura para cualquier usuario autenticado; escritura solo administradores."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return request.method in SAFE_METHODS or u.es_admin


class SoloAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.es_admin)
