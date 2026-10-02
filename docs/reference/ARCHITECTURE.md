# Arquitectura — Finanzas Personales

## Visión General

Aplicación web de finanzas personales de un solo usuario. UI 100% en Streamlit,
sin servidor de base de datos: todos los datos viven en archivos CSV dentro de `data/`.

---

## Diagrama de capas

```
+---------------------------------------------+
¦                  app.py                      ¦  ? UI Streamlit (9 páginas)
¦  Dashboard · Registrar · Mes a Mes          ¦
¦  Editar · Recurrentes · Ingresos rec.       ¦
¦  Metas · Ahorros · Configuración            ¦
+---------------------------------------------+
                ¦              ¦
     +----------?---+   +------?----------+
     ¦calculations  ¦   ¦   currency.py   ¦
     ¦    .py       ¦   ¦ MXN?USD (live)  ¦
     +--------------+   +-----------------+
                ¦
     +----------?------------+
     ¦    data_manager.py    ¦   ? Único punto de acceso a disco
     +-----------------------+
                ¦
     +----------?------------+
     ¦       data/           ¦
     ¦  transacciones_YYYY.csv   (uno por año)
     ¦  recurrentes.csv
     ¦  ingresos_recurrentes.csv
     ¦  salario_historial.csv
     ¦  ahorros.csv
     +-----------------------+
```

---

## Módulos

### `app.py`
Punto de entrada. Define las 9 páginas de la app como bloques `if/elif` sobre
la variable `pagina` del sidebar. Contiene además helpers de UI reutilizables:

| Helper | Función |
|---|---|
| `metric_html()` | Tarjeta de métrica con CSS inline |
| `tag_selector()` | Multiselect con historial de etiquetas recientes |
| `segmented_selector()` | Control segmentado (usa `st.segmented_control` si disponible, botones si no) |
| `movement_type_selector()` | Selector Gasto / Ingreso extra |
| `parse_transaction_dates()` | Parseo robusto de fechas mixtas |
| `clean_tags() / tags_to_text()` | Normalización del campo `etiquetas` (separador `\|`) |

**Startup:** Al cargar la app por primera vez en cada sesión de Streamlit
(guardado en `st.session_state["startup_data_integrity_checked_v4"]`), ejecuta:
1. `ensure_startup_data_integrity()` — normaliza CSVs de config.
2. `process_due_recurrentes()` — registra gastos recurrentes vencidos.
3. `process_planned_recurrentes_for_cycle()` — pre-registra cobros futuros del ciclo actual.
4. Limpia la caché de Streamlit.

---

### `modules/calculations.py`
Toda la lógica financiera. Sin estado propio; lee de `data_manager`.

**Concepto clave — Ciclo de presupuesto:**
El ciclo no sigue el mes calendario. Corre del **día 14** de un mes al **día 13**
del mes siguiente (ambos inclusive). Esto refleja el patrón de quincenas/nómina.

```python
get_budget_period(year, month)  ? (date, date)   # [día 14, día 14 siguiente)
get_current_budget_cycle(today) ? (year, month)  # ciclo al que pertenece "today"
```

**Funciones principales:**

| Función | Descripción |
|---|---|
| `get_budget_cycle_summary()` | Ingresos, gastos, balance de un ciclo |
| `get_period_summary()` | Ídem para cualquier rango `[start, end)` |
| `get_cumulative_savings()` | Ahorro histórico contando solo salario |
| `get_savings_with_extras()` | Ahorro histórico incluyendo ingresos extra |
| `get_expenses_by_tag()` | Gastos agrupados por etiqueta |
| `process_due_recurrentes()` | Cobra recurrentes vencidos (sin duplicar) |
| `process_planned_recurrentes_for_cycle()` | Pre-registra cobros futuros del ciclo |
| `process_due_ingresos_recurrentes()` | Registra ingresos semanales pendientes |
| `find_duplicate_transaction()` | Detecta duplicados exactos antes de guardar |
| `snapshot_savings()` | Guarda snapshot en `ahorros.csv` |

---

### `modules/data_manager.py`
Único módulo que toca el disco. Todas las funciones de lectura/escritura de CSV.

**Rutas de archivos:**
- Transacciones: `data/transacciones_{year}.csv` — se crea un archivo por año.
- Demás archivos: únicos, en `data/`.

**IDs:**
- Transacciones: `txn_{timestamp_ms}_{uuid6}`
- Recurrentes: `rec_{timestamp_ms}`
- Ingresos recurrentes: `ingrec_{timestamp_ms}`
- Metas: `meta_{timestamp_ms}`

**Regla crítica:** `update_transaction()` no permite mover un movimiento a otro
año distinto al del CSV en que está. Si se cambia la fecha a otro año, lanza
`ValueError`.

---

### `modules/currency.py`
Tipo de cambio USD/MXN en tiempo real. Cacheado 1 hora con `@st.cache_data`.

**Fuentes en orden de prioridad:**
1. `open.er-api.com/v6/latest/USD` (sin API key, ~1500 req/mes gratis)
2. `api.frankfurter.app/latest?from=USD&to=MXN` (BCE europeo, sin key)
3. Fallback hardcodeado: `17.5`

---

## Esquema de etiquetas

Las etiquetas se almacenan como string separado por `|` en la columna `etiquetas`:

```
comida|transporte|trabajo
```

Las funciones internas `_split_tags()`, `_normalize_tag()` y `_tag_matches()`
en `calculations.py` manejan el parsing y la comparación case-insensitive.

---

## Flujo de recurrentes

```
Alta del recurrente (save_recurrente)
        ¦
        ?
Al iniciar la app:
  process_due_recurrentes()          ? cobra todo lo vencido hasta hoy
  process_planned_recurrentes_for_cycle()  ? pre-registra cobros futuros del ciclo
        ¦
        ?
Transacción tipo "gasto" con:
  descripcion = "[Recurrente] {nombre}"
  recurrente_id = FK al recurrente
```

Las mensualidades (compras a meses) cuentan `meses_pagados` y se
desactivan automáticamente al llegar a `meses_total`.
Los recurrentes con enganche (`tiene_pago_inicial=True`) registran
un gasto separado con `[Enganche]` en la descripción.
