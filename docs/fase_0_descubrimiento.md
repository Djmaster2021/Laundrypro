# Fase 0 - Descubrimiento y Diseno

Objetivo: congelar reglas de negocio para evitar retrabajo.

## 1) Datos del negocio

- Nombre comercial: `LaundryPro` (temporal, editable despues)
- Sucursal(es): por definir
- Horario: por definir
- Responsable operativo: por definir

## 2) Politica de cobro

- Moneda: `MXN`
- IVA: `16%`
- Esquema de cobro:
  - Lavado/Secado: por kilo
  - Planchado: no incluido en Fase 1 (modulo separado, proximamente)
  - Mixto en una misma orden: no en Fase 1
- Manejo de redondeo: (2 decimales / otro)

## 3) Flujo operativo actual (libreta -> sistema)

- Datos minimos al recibir orden:
- Regla de fecha promesa:
- Estados permitidos:
  - Recibido -> En proceso -> Listo -> Entregado
- Regla para cancelar orden:
  - Permitida solo si la orden sigue en `Recibido`
  - Si ya paso a `En proceso` (lavado iniciado), no se puede cancelar

## 4) Caja y pagos

- Metodos habilitados:
  - Efectivo
  - Tarjeta
  - Transferencia
- Se permite anticipo: si
- Se permite pago parcial multiple: si
- Regla de entrega con saldo pendiente: no permitida (solo entrega con saldo en 0)

## 5) Ticket

- Campos obligatorios en ticket:
  - Folio
  - Nombre de lavanderia
  - Cliente
  - Fecha
  - Fecha recepcion
  - Precio
  - Conceptos
  - Anticipo
  - Saldo
- Copias de ticket: dos (cliente + mostrador) y respaldo en sistema

## 6) Usuarios y permisos (minimo)

- Admin: acceso total
- Encargada: operacion completa de mostrador y caja
- Vendedora: alta/edicion de ordenes, cobro y entrega bajo reglas
- Restricciones especiales:

## 7) Alcance firmado de Fase 1

Incluye:
1. Login basico por roles (Admin/Operador)
2. CRUD de clientes
3. CRUD de ordenes con items y estados
4. Pagos (anticipo/parcial/final)
5. Ticket base imprimible
6. Busqueda por folio y telefono

No incluye en Fase 1:
1. Scanner Code128
2. Inventario y gastos
3. Reportes avanzados
4. Flujos de planchado avanzado por area

## 8) Criterios de aceptacion Fase 0

- [x] Reglas de negocio definidas
- [x] Campos del ticket definidos
- [x] Estados de orden confirmados
- [x] Reglas de pago confirmadas
- [x] Alcance de Fase 1 aprobado

Estado actual: `CERRADA`
