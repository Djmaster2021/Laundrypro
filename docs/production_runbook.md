# Runbook de Produccion

## 1) Despliegue real (Gunicorn + Nginx + HTTPS)

1. Crear carpeta de despliegue: `/srv/laundrypro`.
2. Instalar dependencias del sistema: `python3-venv`, `nginx`, `certbot`, `python3-certbot-nginx`, `postgresql-client`.
3. Crear virtualenv e instalar dependencias:
   - `python -m venv .venv`
   - `.venv/bin/pip install -r requirements/prod.txt`
4. Definir entorno de produccion (`.env`):
   - `DJANGO_ENV=prod`
   - `DJANGO_DEBUG=0`
   - `DJANGO_SECRET_KEY=<aleatoria_50+>`
   - `DJANGO_ALLOWED_HOSTS=lavanderia.ejemplo.com`
   - `CSRF_TRUSTED_ORIGINS=https://lavanderia.ejemplo.com`
   - `DATABASE_URL=postgresql://...`
5. Migrar + estaticos:
   - `.venv/bin/python manage.py migrate`
   - `.venv/bin/python manage.py collectstatic --noinput`
6. Instalar unidad systemd de Gunicorn:
   - copiar `deploy/systemd/laundrypro.service` a `/etc/systemd/system/`
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now laundrypro`
7. Instalar Nginx:
   - copiar `deploy/nginx/laundrypro.conf` a `/etc/nginx/sites-available/laundrypro`
   - enlazar a `sites-enabled`
   - `sudo nginx -t && sudo systemctl reload nginx`
8. Emitir TLS con Let\'s Encrypt:
   - `sudo certbot --nginx -d lavanderia.ejemplo.com`

Nunca usar `runserver` en produccion.

## 2) Backups PostgreSQL automaticos

### Backup diario
1. Copiar `ops/backups/backup.env.example` a `ops/backups/backup.env` y ajustar valores.
2. Copiar unidades:
   - `deploy/systemd/laundrypro-backup.service` -> `/etc/systemd/system/`
   - `deploy/systemd/laundrypro-backup.timer` -> `/etc/systemd/system/`
3. Activar timer:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now laundrypro-backup.timer`
4. Verificar ejecucion:
   - `systemctl list-timers | grep laundrypro-backup`
   - `journalctl -u laundrypro-backup.service -n 100 --no-pager`

### Prueba de restauracion mensual
Programar (cron o timer mensual):
`/srv/laundrypro/ops/backups/pg_restore_smoke_test.sh`

El script restaura en una DB temporal, valida tablas publicas y elimina la DB de prueba.

## 3) Auditoria critica

Se registra automaticamente en `apps_common_auditlog`:
- `service.price_changed`
- `order.cancelled`
- `payment.created`, `payment.edited`, `payment.voided`
- `cash_session.closed`

Campos clave: usuario actor, IP, entidad objetivo y cambios antes/despues.

Consulta rapida:
`SELECT created_at, action, target_model, target_pk, actor_id FROM apps_common_auditlog ORDER BY created_at DESC LIMIT 100;`

## 4) Seguridad de sesion y acceso

- Contrasena fuerte obligatoria:
  - minimo configurable (`PASSWORD_MIN_LENGTH`, recomendado 12+)
  - requiere mayuscula, minuscula, numero y simbolo.
- Expiracion absoluta de sesion:
  - `SESSION_COOKIE_AGE_SECONDS` (recomendado 8h o menos).
- Bloqueo por inactividad:
  - `SESSION_INACTIVITY_TIMEOUT_SECONDS` (recomendado 15 min).
- Rotacion de credenciales:
  - `PASSWORD_MAX_AGE_DAYS` (recomendado 90 dias).
  - middleware redirige forzosamente a `/password/change/` al expirar.

## 5) Endurecimiento API

- Throttling activo por IP y usuario:
  - `API_THROTTLE_ANON_IP_RATE`
  - `API_THROTTLE_USER_RATE`
  - `API_THROTTLE_SENSITIVE_USER_RATE`
- Permisos por objeto para caja/cobros:
  - vendedora solo ve/edita sus sesiones, movimientos y cobros.
  - encargada/admin pueden operar globalmente.
- Log de intentos denegados:
  - eventos 401/403/429 en logger `security`.
  - revisar con `journalctl -u laundrypro -n 200 --no-pager | grep api_access_denied`.

## 6) Politica SSH obligatoria (GitHub y servidores)

Aplicar siempre autenticacion por llave SSH, no password:

1. Endurecer SSHD en servidor (`/etc/ssh/sshd_config`):
   - `PasswordAuthentication no`
   - `KbdInteractiveAuthentication no`
   - `PubkeyAuthentication yes`
   - `PermitRootLogin no`
2. Reiniciar SSH: `sudo systemctl restart sshd`.
3. GitHub remoto por SSH:
   - `git remote set-url origin git@github.com:ORG/REPO.git`
4. Usar llaves modernas:
   - `ssh-keygen -t ed25519 -a 64 -C "deploy@laundrypro"`
5. Rotacion de llaves:
   - cada 90 dias para cuentas criticas,
   - revocar inmediatamente cualquier llave sospechosa.

## 7) Monitoreo y alertas (DB, 500, diferencia de caja)

Alertas operativas registradas en `apps_common_operationalalert`:
- `database.unavailable` (healthcheck con DB no disponible)
- `http.server_error` (respuesta 500)
- `cash_session.high_difference` (diferencia de cierre sobre umbral)

Configuracion:
- `CASH_DIFF_ALERT_THRESHOLD` (ej. `200.00`)

Verificacion activa:
1. Instalar unidades:
   - `deploy/systemd/laundrypro-alert-check.service`
   - `deploy/systemd/laundrypro-alert-check.timer`
2. Activar:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now laundrypro-alert-check.timer`
3. Revisar estado:
   - `journalctl -u laundrypro-alert-check.service -n 100 --no-pager`

Comando manual:
- `python manage.py check_operational_alerts --minutes 60`

## 8) Regresion de negocio automatizada

Flujo validado por prueba automatica:
- abrir caja -> crear orden -> cobrar total -> entregar -> cerrar caja -> corte diario.

Prueba:
- `python manage.py test apps.payments.tests.test_business_regression_flow -v 2`
