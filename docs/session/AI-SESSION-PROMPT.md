# AI Session Prompt — Reglas y Restricciones

Este documento contiene las reglas innegociables, decisiones de arquitectura
confirmadas y restricciones que cualquier colaborador (humano o IA) debe
respetar al trabajar en este proyecto.

---

## Reglas de seguridad y datos

| # | Regla | Detalle |
|---|---|---|
| R-01 | **No commitear datos personales** | Los archivos `data/*.csv` contienen información financiera real. No incluirlos en commits públicos. El repo es privado; si cambia a público, mover `data/` al `.gitignore`. |
| R-02 | **No hardcodear credenciales** | Sin API keys, tokens ni contraseñas en el código. `currency.py` usa endpoints abiertos sin key. |
| R-03 | **No cambiar el separador de etiquetas** | Siempre `\|` (pipe). Cambiar esto rompe todos los filtros. |
| R-04 | **No mover transacciones entre años desde la UI** | `update_transaction()` lanza `ValueError` si se cambia el año. Es intencional: los CSVs son por año. |
| R-05 | **No borrar `ahorros.csv` manualmente** | Es el historial de snapshots. Los datos se acumulan; se puede truncar pero nunca borrar toda la historia. |

---

## Decisiones de arquitectura

| ID | Decisión | Justificación |
|---|---|---|
| D-01 | **CSV por año para transacciones** | Evita archivos gigantes. El año está en el nombre del archivo (`transacciones_2026.csv`). |
| D-02 | **Ciclo de presupuesto del día 14** | Refleja el patrón de quincenas del usuario. Parametrizable con `start_day=14` pero no cambiar sin migrar datos. |
| D-03 | **Sin base de datos** | Diseño deliberado para portabilidad. Los CSV son suficientes para un solo usuario. |
| D-04 | **data_manager.py como única capa de I/O** | Ningún otro módulo debe tocar `data/` directamente. |
| D-05 | **Pre-registro de recurrentes futuros** | Los cobros del ciclo actual se pre-registran con fecha futura para que aparezcan en el presupuesto, pero no cuentan como ahorro real hasta que pase su fecha. |
| D-06 | **Startup guard con session_state** | `startup_data_integrity_checked_v4` evita que el proceso de startup corra más de una vez por sesión de Streamlit. Si se hacen cambios estructurales al startup, incrementar el sufijo numérico del key. |

---

## Archivos de solo lectura (no modificar sin análisis)

| Archivo | Razón |
|---|---|
| `data/salario_historial.csv` | Historial acumulativo. Agregar filas está bien; borrar o editar filas pasadas distorsiona los cálculos históricos. |
| `data/ahorros.csv` | Solo se escribe vía `update_savings_snapshot()`. Nunca editar a mano. |

---

## Convenciones de código

- Todo en **español** en la UI (labels, mensajes, descripciones).
- Comentarios de código en **español** o inglés, consistente con el archivo.
- Etiquetas de usuario: **case-insensitive** en comparación (`_normalize_tag` usa `casefold`), pero se preserva el case original al mostrar.
- Fechas en disco: siempre `YYYY-MM-DD`. Objetos Python: `datetime.date` o `pd.Timestamp`.
- Rangos de fechas: siempre **`[start, end)`** (end exclusivo).
