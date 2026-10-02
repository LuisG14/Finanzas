# Guía de Documentación (`docs/`)

Este documento describe el propósito, la estructura y el contenido que debe incluirse en cada archivo y carpeta dentro de `docs/`. Sirve como estándar y guía de mantenimiento para desarrolladores y modelos de IA que trabajen en el proyecto.

---

## 📂 Visión General del Directorio

```text
docs/
├── DOCS-GUIDE.md               # Esta guía explicativa
├── HANDOFF.md                  # Estado global del proyecto y prompt de inicio de sesión
├── problems/                   # Registro histórico de problemas y bloqueos
│   └── PROBLEMS.md             # Log de errores, causas raíz y soluciones (por arquitectura/componente)
├── reference/                  # Contexto técnico y guías de referencia detalladas
│   ├── CHART-CREATION-GUIDE.md
│   ├── DATASET-CONTEXT.md
│   └── SUPERSET-CHART-TYPES.md
└── session/                    # Gestión del contexto y seguimiento de sesiones LLM
    ├── AI-SESSION-PROMPT.md    # Reglas críticas, constraints y decisiones de arquitectura
    ├── NEXT-SESSION.md         # Estado dinámico actual y desglose de tracks/tareas
    └── PLANNING-SESSION.md     # Registro de sesiones de diseño y decisiones tomadas
```

> **Nota:** La carpeta `docs/` se mantiene ignorada por git (`.gitignore`) para almacenar contexto local y de sesión sin contaminar el repositorio principal.

---

## 📄 Archivos en la Raíz de `docs/`

### [`docs/HANDOFF.md`](docs/HANDOFF.md)
* **Propósito:** Es el documento principal de traspaso entre sesiones de trabajo. Contiene el estado macro del proyecto, el resumen de infraestructura y el prompt oficial que se copia al inicio de cada chat con la IA.
* **Qué agregar/actualizar aquí:**
  - El encabezado con la sesión y track actual.
  - El *Session Start Prompt* indicando el orden de lectura de los archivos.
  - Tabla de estado de infraestructura (versiones de Helm, URLs activas, digests de imágenes).
  - Resumen de tracks completados y el estado del track en curso.
  - Registro de logros recientes (*Recent Accomplishments*).

---

## 📁 Carpeta `problems/`

### [`docs/problems/PROBLEMS.md`](docs/problems/PROBLEMS.md)
* **Propósito:** Log permanente de incidentes, errores de despliegue, problemas de permisos/SCC, fallos de compilación o incompatibilidades de librerías. **Los problemas nunca se borran**, incluso después de resolverse, para evitar reincidencias.
* **Estructura por Arquitectura y Componentes (Regla Importante):**
  - Si se trabaja en entornos o arquitecturas heterogéneas, se debe segregar o clasificar la documentación de problemas por sistema operativo / arquitectura (por ejemplo: `macOS Apple Silicon (arm64)`, `Linux / OpenShift (amd64)`, `Windows`, `Linux Server`).
  - Igualmente, si se integran diferentes tecnologías o servicios en el ecosistema (por ejemplo: `Apache Superset`, `Apache Airflow`, `Apache Spark`, `PostgreSQL`, `IBM Db2`), se debe registrar un apartado o documento específico para cada componente.
* **Qué agregar en cada entrada de problema:**
  - Identificador único (`P-01`, `P-02`, etc.) y título descriptivo.
  - **Fecha** y **Fase/Track** en que ocurrió.
  - **Síntoma:** Mensaje exacto de error o comportamiento observado.
  - **Causa Raíz (*Root Cause*):** Explicación técnica de por qué ocurrió el fallo.
  - **Solución (*Fix*):** Pasos concretos, comandos o cambios de código aplicados.
  - **Resultado:** Estado tras la corrección y hashes/artefactos resultantes.
  - **Prevención / Lección Aprendida:** Cómo evitar que vuelva a ocurrir.

---

## 📁 Carpeta `reference/`

* **Propósito:** Esta carpeta alberga contexto específico, detallado y técnico sobre fuentes de datos, catálogos de APIs y compatibilidad de herramientas.
* **Concepto Clave:** Es el lugar adecuado para documentar características particulares que dependen de versiones o ecosistemas concretos (por ejemplo, en el caso de Apache Superset, los tipos de gráficos y plugins soportados según la versión desplegada, catálogos de columnas de bases de datos, guías de automatización de APIs, etc.).
* **Archivos actuales:**
  - [`docs/reference/SUPERSET-CHART-TYPES.md`](docs/reference/SUPERSET-CHART-TYPES.md): Catálogo de `viz_type` soportados por la versión de Superset activa (ej. `echarts_timeseries_bar`, `table`), plugins registrados y parámetros requeridos.
  - [`docs/reference/DATASET-CONTEXT.md`](docs/reference/DATASET-CONTEXT.md): Diccionario y contexto de negocio de los datasets (columnas útiles para métricas, dimensiones, campos a ignorar).
  - [`docs/reference/CHART-CREATION-GUIDE.md`](docs/reference/CHART-CREATION-GUIDE.md): Guía paso a paso para la creación automatizada de gráficos y dashboards vía REST API, incluyendo payloads y lecciones aprendidas.

---

## 📁 Carpeta `session/`

* **Propósito:** Gestión interna de memoria, reglas de negocio e historial de planificación para el trabajo asistido por IA y desarrolladores.

### [`docs/session/AI-SESSION-PROMPT.md`](docs/session/AI-SESSION-PROMPT.md)
* **Propósito:** Documento de reglas profundas, restricciones innegociables y decisiones de arquitectura fijas.
* **Qué agregar aquí:**
  - Tabla de reglas obligatorias de seguridad y despliegue (ej. no hardcodear UIDs, no comitear secretos, uso de `restricted-v2` SCC, flags de compilación multiplataforma).
  - Tabla de decisiones de arquitectura confirmadas (`D-01`, `D-02`, etc.) con sus justificaciones.
  - Restricciones sobre qué archivos son de solo lectura (como `airflow-helm-ocp4/`).

### [`docs/session/NEXT-SESSION.md`](docs/session/NEXT-SESSION.md)
* **Propósito:** Seguimiento dinámico y vivo del estado del proyecto. Es el checklist operativo de tareas pendientes e inmediatas.
* **Qué agregar aquí:**
  - Estado actual del semáforo del proyecto (ej. 🟢 LIVE, 🟡 En progreso).
  - Desglose de cada Track de trabajo con sus checkboxes de tareas (`[x]` completadas, `[ ]` pendientes).
  - Registro de variables de entorno y comandos operativos útiles.

### [`docs/session/PLANNING-SESSION.md`](docs/session/PLANNING-SESSION.md)
* **Propósito:** Bitácora de discusiones de arquitectura, acuerdos tomados durante sesiones de diseño y respuestas a preguntas técnicas de fondo.
* **Qué agregar aquí:**
  - Resumen de preguntas y respuestas de sesiones de arquitectura.
  - Análisis comparativo de opciones evaluadas (ej. PostgreSQL empaquetado vs. externo, estrategia de imágenes personalizadas).
  - Hallazgos técnicos descubiertos durante la validación de manifiestos y plantillas.
