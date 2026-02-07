from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

ROLE_ADMIN = "Administrador"
ROLE_MANAGER = "Encargada"
ROLE_SELLER = "Vendedora"


def user_has_any_role(user, roles):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


class RoleRequiredMixin(AccessMixin):
    allowed_roles = tuple()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if user_has_any_role(request.user, self.allowed_roles):
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "No tienes permisos para acceder a esta seccion.")
        return redirect("app-home")
