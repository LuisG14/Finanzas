# HANDOFF — Finanzas Personales

> **Copia este bloque al iniciar una nueva sesión con la IA:**
> 1. Lee `docs/HANDOFF.md` (este archivo) para el estado global.
> 2. Lee `docs/session/NEXT-SESSION.md` para las tareas pendientes.
> 3. Lee `docs/session/AI-SESSION-PROMPT.md` para las reglas y restricciones.
> 4. Si hay un problema activo, revisa `docs/problems/PROBLEMS.md`.

---

## Estado del Proyecto

| Campo | Valor |
|---|---|
| **Estado** | ?? Operativo |
| **Stack** | Python 3 · Streamlit · Pandas · Plotly · uv |
| **Entrada punto** | `app.py` |
| **Datos** | `data/` — CSVs locales, sin base de datos |
| **Divisa base** | MXN (con conversión live a USD via exchangerate-api) |
| **Repo** | git@github.com:LuisG14/Finanzas.git (privado) |
| **NAS** | TrueNAS SCALE · IP: 100.104.88.116 · usuario: admin |
| **Ruta en NAS** | /mnt/Luis/Finanzas |

---

## Arquitectura en una línea

`app.py` (UI Streamlit) ? `modules/calculations.py` (lógica) ? `modules/data_manager.py` (CSV I/O) ? `data/*.csv`

---

## Tracks completados

| # | Descripción | Estado |
|---|---|---|
| T-01 | Commit inicial del repo al branch main | ? |
| T-02 | SSH sin contraseña al NAS configurado | ? |
| T-03 | Repo clonado en /mnt/Luis/Finanzas en el NAS | ? |
| T-04 | Documentación base creada | ? |

---

## Track en curso

**T-05 — Despliegue con Docker en TrueNAS SCALE**
- Pendiente: crear Dockerfile + docker-compose.yml
- Pendiente: levantar como servicio con restart automático

---

## Logros recientes

- Primer commit con 16 archivos (4 222 líneas) subido a GitHub.
- SSH key-based auth funcionando desde la PC al NAS.
- Repo clonado en /mnt/Luis/Finanzas en TrueNAS SCALE.
