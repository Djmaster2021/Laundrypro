# Roadmap por Fases - LaundryPro

Estado del proyecto: `FASE 5 CERRADA`

## Fases

| Fase | Nombre | Estado | Entregable de cierre |
|---|---|---|---|
| 0 | Descubrimiento + Diseño | Cerrada | Documento de alcance firmado |
| 1 | Operacion base | Cerrada parcial | Flujo completo de orden + ticket |
| 2 | Caja, cobros y turnos | Cerrada parcial | Corte diario y trazabilidad por usuario |
| 3 | Escaneo + entrega rapida | Cerrada | Flujo por scanner Code128 |
| 4 | Planchado completo | Cerrada | Ordenes mixtas lavanderia/planchado |
| 5 | Inventario + gastos + reportes | Cerrada | Tablero de reportes y alertas de stock |

## Regla de avance

Se avanza a la siguiente fase solo cuando:
1. Se cumplen todos los puntos de la fase.
2. Se hace validacion funcional.
3. Se confirma cierre contigo en mensaje: `FASE X CERRADA`.

## Definicion de hecho (DoD)

1. Codigo versionado y funcional.
2. Sin errores en `python manage.py check`.
3. Migraciones aplicadas cuando corresponda.
4. Flujo probado en interfaz/admin o API.
5. Nota de cierre de fase en este archivo.

## Bitacora de cierres

- 2026-02-06: `FASE 0 CERRADA` con reglas confirmadas de cobro, cancelacion, entrega, ticket y roles.
- 2026-02-06: inicio tecnico `FASE 2` con modelos de caja por turno y trazabilidad de pagos por usuario/sesion.
- 2026-02-06: inicio tecnico `FASE 3` con pantalla de escaneo, vista rapida de cobro/entrega y ticket con Code128.
- 2026-02-06: `FASE 3 CERRADA` con escaneo autofocus, cobro rapido, entrega validada por saldo y reimpresion.
- 2026-02-06: inicio tecnico `FASE 4` con servicios por categoria (lavanderia/planchado), estados por area y reporte de ventas por tipo.
- 2026-02-06: paneles por rol implementados (`Encargada` y `Punto de venta`) con login inicial y metricas operativas.
- 2026-02-06: `FASE 4 CERRADA` con tablero de produccion por area y sincronizacion automatica del estado global.
- 2026-02-06: `FASE 5 CERRADA` con inventario, movimientos, gastos y reportes avanzados (clientes frecuentes, consumo, pendientes y atrasadas).
