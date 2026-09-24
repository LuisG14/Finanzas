"""
data_manager.py
Manejo de archivos CSV por año y hoja de ahorros separada.
"""

import pandas as pd
import os
import uuid
from datetime import datetime, date

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

TRANSACTIONS_COLS = [
    "id", "fecha", "tipo",        # ingreso / gasto / ajuste_salario
    "monto", "descripcion",
    "etiquetas",                   # separadas por |
    "recurrente_id",               # FK a recurrentes, vacío si no aplica
    "moneda_original", "monto_original",
]

RECURRENTES_COLS = [
    "id", "nombre", "monto", "tipo_recurrencia",  # suscripcion / mensualidades
    "meses_total",        # null si suscripcion indefinida
    "meses_pagados",
    "fecha_inicio",
    "activo",             # True/False
    "etiquetas",
    "tiene_pago_inicial",
    "monto_pago_inicial",
    "fecha_pago_inicial",
    "pago_inicial_registrado",
    "descripcion_pago_inicial",
    "etiquetas_pago_inicial",
]

INGRESOS_RECURRENTES_COLS = [
    "id", "nombre", "monto", "dia_semana",
    "fecha_inicio", "fecha_fin", "activo", "etiquetas",
]

METAS_COLS = [
    "id", "nombre", "monto_objetivo", "monto_actual",
    "fecha_objetivo", "completada", "descripcion",
]

SAVINGS_COLS = [
    "fecha", "ahorro_acumulado", "salario_base",
]

SALARY_COLS = [
    "fecha_desde", "monto",
]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _txn_path(year: int) -> str:
    return os.path.join(DATA_DIR, f"transacciones_{year}.csv")


def _parse_txn_fecha(fecha):
    try:
        return pd.to_datetime(fecha, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(fecha, errors="coerce")


def _txn_date_str(fecha) -> str:
    parsed = _parse_txn_fecha(fecha)
    if pd.isna(parsed):
        return date.today().strftime("%Y-%m-%d")
    return parsed.strftime("%Y-%m-%d")


def _optional_date_str(fecha) -> str:
    if fecha is None or str(fecha).strip() == "" or str(fecha).strip().lower() == "nan":
        return ""
    parsed = _parse_txn_fecha(fecha)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def _txn_year_from_fecha(fecha) -> int:
    parsed = _parse_txn_fecha(fecha)
    if pd.isna(parsed):
        return datetime.now().year
    return int(parsed.year)


def _rec_path() -> str:
    return os.path.join(DATA_DIR, "recurrentes.csv")


def _ingresos_rec_path() -> str:
    return os.path.join(DATA_DIR, "ingresos_recurrentes.csv")


def _meta_path() -> str:
    return os.path.join(DATA_DIR, "metas.csv")


def _savings_path() -> str:
    return os.path.join(DATA_DIR, "ahorros.csv")


def _salary_path() -> str:
    return os.path.join(DATA_DIR, "salario_historial.csv")


# ─── Transacciones ────────────────────────────────────────────────────────────

def load_transactions(year: int = None) -> pd.DataFrame:
    _ensure_dir()
    if year:
        path = _txn_path(year)
        if not os.path.exists(path):
            return pd.DataFrame(columns=TRANSACTIONS_COLS)
        df = pd.read_csv(path, dtype=str)
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
        df["monto_original"] = pd.to_numeric(df["monto_original"], errors="coerce")
        df["fecha"] = _parse_txn_fecha(df["fecha"])
        return df

    # Cargar todos los años disponibles
    frames = []
    for f in os.listdir(DATA_DIR):
        if f.startswith("transacciones_") and f.endswith(".csv"):
            df = pd.read_csv(os.path.join(DATA_DIR, f), dtype=str)
            df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
            df["monto_original"] = pd.to_numeric(df["monto_original"], errors="coerce")
            df["fecha"] = _parse_txn_fecha(df["fecha"])
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=TRANSACTIONS_COLS)
    return pd.concat(frames, ignore_index=True).sort_values("fecha")


def save_transaction(row: dict):
    _ensure_dir()
    if "fecha" not in row or not row["fecha"]:
        row["fecha"] = date.today().strftime("%Y-%m-%d")
    else:
        row["fecha"] = _txn_date_str(row["fecha"])

    year = _txn_year_from_fecha(row["fecha"])
    path = _txn_path(year)
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=object).astype(object)
    else:
        df = pd.DataFrame(columns=TRANSACTIONS_COLS)

    for col in TRANSACTIONS_COLS:
        if col not in df.columns:
            df[col] = ""

    # Generar ID
    row["id"] = f"txn_{int(datetime.now().timestamp()*1000)}_{uuid.uuid4().hex[:6]}"
    new_row = pd.DataFrame([{col: row.get(col, "") for col in TRANSACTIONS_COLS}])
    df = pd.concat([df, new_row], ignore_index=True)
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["monto_original"] = pd.to_numeric(df["monto_original"], errors="coerce")
    df = df[TRANSACTIONS_COLS]
    df.to_csv(path, index=False)
    return row["id"]


def delete_transaction(txn_id: str):
    _ensure_dir()
    for f in os.listdir(DATA_DIR):
        if not (f.startswith("transacciones_") and f.endswith(".csv")):
            continue
        path = os.path.join(DATA_DIR, f)
        df = pd.read_csv(path, dtype=str)
        if "id" not in df.columns or txn_id not in set(df["id"].astype(str)):
            continue
        df = df[df["id"] != txn_id]
        df.to_csv(path, index=False)
        return True
    return False


def update_transaction(txn_id: str, updates: dict):
    """Actualiza una transacción sin moverla de archivo anual."""
    _ensure_dir()
    numeric_cols = {"monto", "monto_original"}
    string_cols = {
        "fecha", "tipo", "descripcion", "etiquetas",
        "recurrente_id", "moneda_original",
    }

    for f in os.listdir(DATA_DIR):
        if not (f.startswith("transacciones_") and f.endswith(".csv")):
            continue

        path = os.path.join(DATA_DIR, f)
        df = pd.read_csv(path, dtype=object).astype(object)
        if "id" not in df.columns or txn_id not in set(df["id"].astype(str)):
            continue

        mask = df["id"].astype(str) == txn_id
        current_fecha = pd.NaT
        if "fecha" in df.columns:
            current_fecha = _parse_txn_fecha(df.loc[mask, "fecha"].iloc[0])

        if "fecha" in updates:
            new_fecha = _parse_txn_fecha(updates["fecha"])
            if pd.notna(current_fecha) and pd.notna(new_fecha) and current_fecha.year != new_fecha.year:
                raise ValueError("No se puede cambiar el movimiento a otro año desde esta vista.")

        updated = False
        for key, value in updates.items():
            if key not in df.columns or key == "id":
                continue

            if key in numeric_cols:
                value = pd.to_numeric(value, errors="coerce")
            elif key == "fecha":
                value = _txn_date_str(value)
            elif key in string_cols:
                value = "" if pd.isna(value) else str(value)

            df.loc[mask, key] = value
            updated = True

        if not updated:
            return False

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].where(pd.notna(df[col]), "").astype(str)

        df.to_csv(path, index=False)
        return True

    return False


# ─── Recurrentes ──────────────────────────────────────────────────────────────

def load_recurrentes() -> pd.DataFrame:
    _ensure_dir()
    path = _rec_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=RECURRENTES_COLS)
    df = pd.read_csv(path, dtype=object).astype(object)
    defaults = {
        "meses_total": "",
        "meses_pagados": 0,
        "activo": True,
        "etiquetas": "",
        "tiene_pago_inicial": False,
        "monto_pago_inicial": 0,
        "fecha_pago_inicial": "",
        "pago_inicial_registrado": False,
        "descripcion_pago_inicial": "",
        "etiquetas_pago_inicial": "",
    }
    for col in RECURRENTES_COLS:
        if col not in df.columns:
            df[col] = defaults.get(col, "")

    df = df[RECURRENTES_COLS]
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["meses_total"] = pd.to_numeric(df["meses_total"], errors="coerce")
    df["meses_pagados"] = pd.to_numeric(df["meses_pagados"], errors="coerce")
    df["monto_pago_inicial"] = pd.to_numeric(df["monto_pago_inicial"], errors="coerce").fillna(0)
    df["fecha_inicio"] = df["fecha_inicio"].apply(_txn_date_str)
    df["fecha_pago_inicial"] = df["fecha_pago_inicial"].apply(_optional_date_str)
    df["activo"] = df["activo"].map({"True": True, "False": False, True: True, False: False}).fillna(True)
    df["tiene_pago_inicial"] = df["tiene_pago_inicial"].map({"True": True, "False": False, True: True, False: False}).fillna(False)
    df["pago_inicial_registrado"] = df["pago_inicial_registrado"].map({"True": True, "False": False, True: True, False: False}).fillna(False)
    for col in ["nombre", "tipo_recurrencia", "etiquetas", "descripcion_pago_inicial", "etiquetas_pago_inicial"]:
        df[col] = df[col].where(pd.notna(df[col]), "").astype(str)
    return df


def save_recurrente(row: dict):
    _ensure_dir()
    df = load_recurrentes()
    row["id"] = f"rec_{int(datetime.now().timestamp()*1000)}"
    row.setdefault("tiene_pago_inicial", False)
    row.setdefault("monto_pago_inicial", 0)
    row.setdefault("fecha_pago_inicial", "")
    row.setdefault("pago_inicial_registrado", False)
    row.setdefault("descripcion_pago_inicial", "")
    row.setdefault("etiquetas_pago_inicial", "")
    row["fecha_inicio"] = _txn_date_str(row.get("fecha_inicio") or date.today())
    row["fecha_pago_inicial"] = _optional_date_str(row.get("fecha_pago_inicial"))
    new_row = pd.DataFrame([{col: row.get(col, "") for col in RECURRENTES_COLS}])
    df = pd.concat([df, new_row], ignore_index=True)
    df = df[RECURRENTES_COLS]
    df.to_csv(_rec_path(), index=False)
    return row["id"]


def update_recurrente(rec_id: str, updates: dict):
    df = load_recurrentes().astype(object)
    numeric_cols = {"monto", "meses_total", "meses_pagados", "monto_pago_inicial"}
    bool_cols = {"activo", "tiene_pago_inicial", "pago_inicial_registrado"}
    date_cols = {"fecha_inicio", "fecha_pago_inicial"}

    for k, v in updates.items():
        if k not in RECURRENTES_COLS or k == "id":
            continue
        if k in numeric_cols:
            v = pd.to_numeric(v, errors="coerce")
        elif k in bool_cols:
            v = bool(v)
        elif k in date_cols:
            v = _txn_date_str(v) if k == "fecha_inicio" else _optional_date_str(v)
        else:
            v = "" if pd.isna(v) else str(v)
        df.loc[df["id"] == rec_id, k] = v

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": True, "False": False, True: True, False: False}).fillna(False)
    df = df[RECURRENTES_COLS]
    df.to_csv(_rec_path(), index=False)


def cancel_recurrente(rec_id: str):
    update_recurrente(rec_id, {"activo": False})


# ─── Ingresos recurrentes ─────────────────────────────────────────────────────

def load_ingresos_recurrentes() -> pd.DataFrame:
    _ensure_dir()
    path = _ingresos_rec_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=INGRESOS_RECURRENTES_COLS)

    df = pd.read_csv(path, dtype=object).astype(object)
    for col in INGRESOS_RECURRENTES_COLS:
        if col not in df.columns:
            df[col] = ""

    df = df[INGRESOS_RECURRENTES_COLS]
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["dia_semana"] = pd.to_numeric(df["dia_semana"], errors="coerce")
    df["fecha_inicio"] = _parse_txn_fecha(df["fecha_inicio"])
    df["fecha_fin"] = _parse_txn_fecha(df["fecha_fin"])
    df["activo"] = df["activo"].map({"True": True, "False": False, True: True, False: False}).fillna(False)
    return df


def save_ingreso_recurrente(row: dict):
    _ensure_dir()
    df = load_ingresos_recurrentes()

    row["id"] = f"ingrec_{int(datetime.now().timestamp()*1000)}"
    row["monto"] = pd.to_numeric(row.get("monto", 0), errors="coerce")
    row["dia_semana"] = int(row.get("dia_semana", 0) or 0)
    row["fecha_inicio"] = _txn_date_str(row.get("fecha_inicio") or date.today())
    row["fecha_fin"] = _optional_date_str(row.get("fecha_fin"))
    row["activo"] = bool(row.get("activo", True))

    new_row = pd.DataFrame([{col: row.get(col, "") for col in INGRESOS_RECURRENTES_COLS}])
    df = pd.concat([df, new_row], ignore_index=True)
    df["fecha_inicio"] = df["fecha_inicio"].apply(_txn_date_str)
    df["fecha_fin"] = df["fecha_fin"].apply(_optional_date_str)
    df.to_csv(_ingresos_rec_path(), index=False)
    return row["id"]


def update_ingreso_recurrente(ingreso_id: str, updates: dict):
    _ensure_dir()
    df = load_ingresos_recurrentes().astype(object)
    if df.empty or ingreso_id not in set(df["id"].astype(str)):
        return False

    mask = df["id"].astype(str) == ingreso_id
    for key, value in updates.items():
        if key not in INGRESOS_RECURRENTES_COLS or key == "id":
            continue

        if key == "monto":
            value = pd.to_numeric(value, errors="coerce")
        elif key == "dia_semana":
            value = int(value)
        elif key in {"fecha_inicio", "fecha_fin"}:
            value = _txn_date_str(value) if key == "fecha_inicio" else _optional_date_str(value)
        elif key == "activo":
            value = bool(value)
        else:
            value = "" if pd.isna(value) else str(value)

        df.loc[mask, key] = value

    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["dia_semana"] = pd.to_numeric(df["dia_semana"], errors="coerce")
    df["fecha_inicio"] = df["fecha_inicio"].apply(_txn_date_str)
    df["fecha_fin"] = df["fecha_fin"].apply(_optional_date_str)
    df = df[INGRESOS_RECURRENTES_COLS]
    df.to_csv(_ingresos_rec_path(), index=False)
    return True


def cancel_ingreso_recurrente(ingreso_id: str):
    return update_ingreso_recurrente(ingreso_id, {"activo": False})


# ─── Metas ────────────────────────────────────────────────────────────────────

def load_metas() -> pd.DataFrame:
    _ensure_dir()
    path = _meta_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=METAS_COLS)
    df = pd.read_csv(path, dtype=str)
    df["monto_objetivo"] = pd.to_numeric(df["monto_objetivo"], errors="coerce")
    df["monto_actual"] = pd.to_numeric(df["monto_actual"], errors="coerce")
    df["completada"] = df["completada"].map({"True": True, "False": False, True: True, False: False})
    return df


def save_meta(row: dict):
    _ensure_dir()
    df = load_metas()
    row["id"] = f"meta_{int(datetime.now().timestamp()*1000)}"
    row.setdefault("monto_actual", 0)
    row.setdefault("completada", False)
    new_row = pd.DataFrame([row])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(_meta_path(), index=False)
    return row["id"]


def update_meta(meta_id: str, updates: dict):
    df = load_metas()
    for k, v in updates.items():
        df.loc[df["id"] == meta_id, k] = v
    df.to_csv(_meta_path(), index=False)


def delete_meta(meta_id: str):
    df = load_metas()
    df = df[df["id"] != meta_id]
    df.to_csv(_meta_path(), index=False)


# ─── Ahorros ──────────────────────────────────────────────────────────────────

def load_savings() -> pd.DataFrame:
    _ensure_dir()
    path = _savings_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=SAVINGS_COLS)
    df = pd.read_csv(path, dtype=str)
    df["ahorro_acumulado"] = pd.to_numeric(df["ahorro_acumulado"], errors="coerce")
    df["salario_base"] = pd.to_numeric(df["salario_base"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df


def update_savings_snapshot(ahorro_acumulado: float, salario_base: float):
    """Guarda un snapshot del ahorro actual."""
    _ensure_dir()
    df = load_savings()
    new_row = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ahorro_acumulado": ahorro_acumulado,
        "salario_base": salario_base,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(_savings_path(), index=False)


# ─── Salario ──────────────────────────────────────────────────────────────────

def load_salary_history() -> pd.DataFrame:
    _ensure_dir()
    path = _salary_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=SALARY_COLS)
    df = pd.read_csv(path, dtype=str)
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")
    df["fecha_desde"] = _parse_txn_fecha(df["fecha_desde"])
    return df.sort_values("fecha_desde")


def get_current_salary() -> float:
    df = load_salary_history()
    if df.empty:
        return 0.0
    return float(df.iloc[-1]["monto"])


def set_salary(monto: float, fecha_desde: date = None):
    _ensure_dir()
    df = load_salary_history()
    if fecha_desde is None:
        fecha_desde = date.today().replace(day=1)  # inicio del mes actual
    new_row = pd.DataFrame([{
        "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
        "monto": monto,
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(_salary_path(), index=False)


def get_salary_for_month(year: int, month: int) -> float:
    """Retorna el salario vigente para un mes/año dado."""
    df = load_salary_history()
    if df.empty:
        return 0.0
    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)
    valid = df[df["fecha_desde"] <= month_end]
    if valid.empty:
        return 0.0
    return float(valid.iloc[-1]["monto"])


def ensure_startup_data_integrity() -> dict:
    """
    Normaliza archivos de configuración para que Streamlit lea datos frescos.
    No cambia la estructura de transacciones ni migra movimientos históricos.
    """
    _ensure_dir()
    results = {
        "salario_historial": False,
        "recurrentes": False,
        "ingresos_recurrentes": False,
    }

    salary_path = _salary_path()
    if os.path.exists(salary_path):
        df_sal = pd.read_csv(salary_path, dtype=object).astype(object)
        for col in SALARY_COLS:
            if col not in df_sal.columns:
                df_sal[col] = ""
        df_sal = df_sal[SALARY_COLS]
        df_sal["monto"] = pd.to_numeric(df_sal["monto"], errors="coerce")
        df_sal["fecha_desde"] = _parse_txn_fecha(df_sal["fecha_desde"])
        df_sal = df_sal.dropna(subset=["fecha_desde"])
        df_sal["fecha_desde"] = df_sal["fecha_desde"].dt.strftime("%Y-%m-%d")
        df_sal = df_sal.sort_values("fecha_desde")
        df_sal.to_csv(salary_path, index=False)
        results["salario_historial"] = True

    rec_path = _rec_path()
    if os.path.exists(rec_path):
        load_recurrentes().to_csv(rec_path, index=False)
        results["recurrentes"] = True

    ingresos_rec_path = _ingresos_rec_path()
    if os.path.exists(ingresos_rec_path):
        load_ingresos_recurrentes().to_csv(ingresos_rec_path, index=False)
        results["ingresos_recurrentes"] = True

    return results
