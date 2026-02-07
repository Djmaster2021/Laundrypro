# LaundryPro

Sistema web para lavandería + planchado (órdenes, clientes, caja, reportes, inventario).
Stack: Django + DRF + PostgreSQL.

## Setup (dev)
1. Crear venv: `python -m venv .venv` y activar
2. Instalar deps: `pip install -r requirements/dev.txt`
3. Crear `.env` desde `.env.example` (usa `sqlite` por defecto para desarrollo local)
4. Bootstrap completo POS:
   - `python manage.py bootstrap_pos`
5. Crear admin (opcional, recomendado): `python manage.py createsuperuser`
6. Ejecutar: `python manage.py runserver`

## Comandos utiles
- `python manage.py seed_roles`: crea/actualiza roles base
- `python manage.py seed_employees`: crea/actualiza usuarias base (ana, sofia)
- `python manage.py seed_catalog`: crea/actualiza servicios base del POS

## Produccion (minimo)
- Configura `DJANGO_SECRET_KEY` con una clave larga y aleatoria (50+ caracteres).
- Ejemplo para generar una: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- Define `CSRF_TRUSTED_ORIGINS` y `DJANGO_ALLOWED_HOSTS` con tu dominio real.
- Proteccion anti fuerza bruta en login habilitada por defecto:
  - `LOGIN_RATE_LIMIT_MAX_ATTEMPTS` (default `5`)
  - `LOGIN_RATE_LIMIT_WINDOW_SECONDS` (default `900`)
  - `LOGIN_RATE_LIMIT_LOCK_SECONDS` (default `900`)

## Validacion de seguridad
- `python manage.py test apps.accounts.tests.test_security apps.accounts.tests.test_authorization apps.accounts.tests.test_permissions_matrix -v 2`
- `DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy`

## Bloque critico implementado
- Auditoria automatica de acciones criticas en `apps_common_auditlog`:
  - cambio de precios (`service.price_changed`)
  - cancelacion de orden (`order.cancelled`)
  - creacion/edicion/anulacion de cobros (`payment.created|edited|voided`)
  - cierre de caja (`cash_session.closed`)
- Backups y restore test:
  - backup diario: `ops/backups/pg_backup.sh`
  - prueba de restauracion: `ops/backups/pg_restore_smoke_test.sh`
  - variables de entorno: `ops/backups/backup.env.example`
- Plantillas de despliegue seguro:
  - `deploy/systemd/laundrypro.service`
  - `deploy/systemd/laundrypro-backup.service`
  - `deploy/systemd/laundrypro-backup.timer`
  - `deploy/nginx/laundrypro.conf`
- Seguridad de sesion y API:
  - contrasena fuerte + rotacion: `apps/common/validators.py`, `apps/accounts/models.py`
  - inactividad/expiracion de sesion: `apps/common/security_middleware.py`
  - throttling + denegaciones API: `apps/common/throttling.py`, `apps/common/api_exception_handler.py`
  - permisos por objeto en pagos/caja: `apps/payments/views.py`
- Politica de SSH keys only:
  - `deploy/ssh/sshd_hardening.conf`
- Monitoreo operativo:
  - alertas: `apps/common/models.py` (`OperationalAlert`)
  - detector 500: `apps/common/monitoring_middleware.py`
  - chequeo alertas: `apps/common/management/commands/check_operational_alerts.py`
  - timer: `deploy/systemd/laundrypro-alert-check.timer`
- Regresion de negocio automatizada:
  - `apps/payments/tests/test_business_regression_flow.py`

Guia paso a paso: `docs/production_runbook.md`.
