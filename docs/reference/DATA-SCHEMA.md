# Esquema de Datos — Finanzas Personales

Todos los datos se almacenan en archivos CSV dentro de la carpeta `data/`.
No hay base de datos; `data_manager.py` es el único módulo que lee y escribe estos archivos.

---

## `transacciones_{year}.csv`

Un archivo por año calendario (ej. `transacciones_2026.csv`).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | string | Identificador único. Formato: `txn_{timestamp_ms}_{uuid6}` |
| `fecha` | date (YYYY-MM-DD) | Fecha del movimiento |
| `tipo` | enum | `gasto` · `ingreso` |
| `monto` | float | Monto en MXN |
| `descripcion` | string | Texto libre. Los recurrentes tienen prefijo `[Recurrente]` o `[Enganche]`. Los ingresos recurrentes usan `[Ingreso recurrente]`. |
| `etiquetas` | string | Etiquetas separadas por `\|`. Ej: `comida\|trabajo` |
| `recurrente_id` | string (FK) | ID del recurrente en `recurrentes.csv` o `ingresos_recurrentes.csv`. Vacío si es manual. |
| `moneda_original` | string | Siempre `MXN` por ahora |
| `monto_original` | float | Igual a `monto` (reservado para conversiones futuras) |

**Ejemplo:**
```csv
id,fecha,tipo,monto,descripcion,etiquetas,recurrente_id,moneda_original,monto_original
txn_1779727728780,2026-05-14,ingreso,6491.23,Bono mayo,bono|trabajo,,MXN,6491.23
```

---

## `recurrentes.csv`

Gastos periódicos fijos: suscripciones y compras a meses.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | string | Formato: `rec_{timestamp_ms}` |
| `nombre` | string | Nombre descriptivo del recurrente |
| `monto` | float | Monto mensual en MXN |
| `tipo_recurrencia` | enum | `suscripcion` (indefinida) · `mensualidades` (n meses fijos) |
| `meses_total` | int \| vacío | Solo para mensualidades. Total de meses a pagar. |
| `meses_pagados` | int | Contador de mensualidades ya registradas |
| `fecha_inicio` | date (YYYY-MM-DD) | Fecha del primer cobro |
| `activo` | bool | `True` / `False` |
| `etiquetas` | string | Separadas por `\|` |
| `tiene_pago_inicial` | bool | Si tiene enganche/down payment |
| `monto_pago_inicial` | float | Monto del enganche |
| `fecha_pago_inicial` | date \| vacío | Fecha del enganche |
| `pago_inicial_registrado` | bool | Si el enganche ya fue guardado como transacción |
| `descripcion_pago_inicial` | string | Descripción del enganche |
| `etiquetas_pago_inicial` | string | Etiquetas del enganche |

**Ejemplo:**
```csv
rec_1788990202034,Orient Bambino,1169.7,mensualidades,6,1,2026-09-08,True,Personal|Reloj,False,0.0,,False,,
```

---

## `ingresos_recurrentes.csv`

Ingresos periódicos **semanales** (ej. pago semanal de nómina o freelance).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | string | Formato: `ingrec_{timestamp_ms}` |
| `nombre` | string | Nombre descriptivo |
| `monto` | float | Monto por ocurrencia |
| `dia_semana` | int (0–6) | Día de la semana (0=Lunes … 6=Domingo) |
| `fecha_inicio` | date | Desde cuándo aplica |
| `fecha_fin` | date \| vacío | Hasta cuándo aplica. Vacío = indefinido |
| `activo` | bool | `True` / `False`. Se desactiva automáticamente al llegar a `fecha_fin` |
| `etiquetas` | string | Separadas por `\|` |

---

## `salario_historial.csv`

Historial de cambios de salario base mensual. Permite calcular el salario correcto para meses pasados.

| Columna | Tipo | Descripción |
|---|---|---|
| `fecha_desde` | date (YYYY-MM-DD) | A partir de qué fecha aplica este salario |
| `monto` | float | Salario mensual en MXN |

**Regla de consulta:** Para obtener el salario de un mes, se toma la última fila
cuyo `fecha_desde` sea anterior o igual al último día de ese mes.

**Ejemplo:**
```csv
fecha_desde,monto
2026-05-14,8337.0
```

---

## `ahorros.csv`

Snapshots históricos del ahorro acumulado. Se genera automáticamente cada vez que
se registra o modifica un movimiento, y manualmente con el botón del sidebar.

| Columna | Tipo | Descripción |
|---|---|---|
| `fecha` | datetime (YYYY-MM-DD HH:MM:SS) | Momento del snapshot |
| `ahorro_acumulado` | float | Ahorro real acumulado (incluye ingresos extra) |
| `salario_base` | float | Salario vigente en el momento del snapshot |

> **Nota:** Este archivo es de solo lectura para la UI. No se edita directamente.

---

## Convenciones generales

- **Separador de etiquetas:** `\|` (pipe). Nunca comas.
- **Fechas:** siempre `YYYY-MM-DD` en disco. Los objetos Python son `date` o `pd.Timestamp`.
- **Booleanos:** se guardan como el string `True` / `False` en CSV. `data_manager.py` los convierte al leer.
- **Moneda:** todo en MXN. La conversión a USD es solo para display.
- **Sin ORM:** nunca hay migraciones automáticas. Si se agrega una columna nueva, `data_manager.py` la rellena con el valor por defecto al leer.
