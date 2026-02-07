from rest_framework.permissions import BasePermission, DjangoModelPermissions

from .permissions import ROLE_ADMIN, ROLE_MANAGER, user_has_any_role


class StrictDjangoModelPermissions(DjangoModelPermissions):
    """
    Require Django model permissions for every HTTP method, including read access.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class IsManagerOrAdmin(BasePermission):
    message = "No tienes permisos para acceder a este recurso."

    def has_permission(self, request, view):
        return user_has_any_role(request.user, [ROLE_ADMIN, ROLE_MANAGER])


class IsOwnerOrManagerAdmin(BasePermission):
    message = "No tienes permisos sobre este recurso."

    def has_object_permission(self, request, view, obj):
        if user_has_any_role(request.user, [ROLE_ADMIN, ROLE_MANAGER]):
            return True

        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner_id_matches(owner, request.user.id)

        owner = getattr(obj, "captured_by", None) or getattr(obj, "created_by", None)
        if owner is not None:
            return owner_id_matches(owner, request.user.id)

        cash_session = getattr(obj, "cash_session", None)
        if cash_session is not None and getattr(cash_session, "user_id", None) is not None:
            return cash_session.user_id == request.user.id

        return False


def owner_id_matches(owner_obj, user_id):
    return getattr(owner_obj, "id", None) == user_id
