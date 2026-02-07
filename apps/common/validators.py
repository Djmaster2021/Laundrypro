import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordComplexityValidator:
    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(_("La contrasena debe incluir al menos una letra mayuscula."), code="password_no_upper")
        if not re.search(r"[a-z]", password):
            raise ValidationError(_("La contrasena debe incluir al menos una letra minuscula."), code="password_no_lower")
        if not re.search(r"\d", password):
            raise ValidationError(_("La contrasena debe incluir al menos un numero."), code="password_no_digit")
        if not re.search(r"[^\w\s]", password):
            raise ValidationError(_("La contrasena debe incluir al menos un simbolo."), code="password_no_symbol")

    def get_help_text(self):
        return _("Tu contrasena debe incluir mayuscula, minuscula, numero y simbolo.")
