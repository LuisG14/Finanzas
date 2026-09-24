"""
calculations.py
Lógica de negocio: ahorros, balance, recurrentes pendientes.
"""

import pandas as pd
import calendar
from datetime import date, timedelta
from modules.data_manager import (
    load_transactions, load_recurrentes, get_salary_for_month,
    get_current_salary, update_savings_snapshot, update_recurrente,
    save_transaction, load_ingresos_recurrentes, update_ingreso_recurrente
)


def get_monthly_summary(year: int, month: int) -> dict:
    """Resumen de ingresos, gastos y balance para un mes dado."""
    df = load_transactions(year)
    if df.empty:
        salary = get_salary_for_month(year, month)
        return {
            "ingresos": salary,
            "gastos": 0.0,
            "balance": salary,
            "salario": salary,
            "ingresos_extra": 0.0,
        }

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    mask = (df["fecha"].dt.year == year) & (df["fecha"].dt.month == month)
    mes_df = df[mask]

    salary = get_salary_for_month(year, month)
    ingresos_extra = mes_df[mes_df["tipo"] == "ingreso"]["monto"].sum()
    gastos = mes_df[mes_df["tipo"] == "gasto"]["monto"].sum()
    total_ingresos = salary + ingresos_extra

    return {
        "ingresos": total_ingresos,
        "gastos": gastos,
        "balance": total_ingresos - gastos,
        "salario": salary,
        "ingresos_extra": ingresos_extra,
    }


def get_cumulative_savings() -> float:
    """
    Calcula el ahorro acumulado total desde el inicio
    considerando solo salario (sin ingresos extra).
    """
    df_all = load_transactions()
    if df_all.empty:
        return 0.0

    df_all["fecha"] = pd.to_datetime(df_all["fecha"], errors="coerce")
    # Los cargos recurrentes se pueden programar con fecha futura para el
    # presupuesto del ciclo. No son parte del ahorro real hasta que llegue su
    # fecha de cobro.
    df_all = df_all[df_all["fecha"].dt.date <= date.today()]
    if df_all.empty:
        return 0.0

    # Obtener todos los meses con transacciones
    months = df_all["fecha"].dropna().apply(lambda x: (x.year, x.month)).unique()

    total_savings = 0.0
    for year, month in sorted(months):
        salary = get_salary_for_month(year, month)
        if salary <= 0:
            continue
        gastos = df_all[
            (df_all["fecha"].dt.year == year) &
            (df_all["fecha"].dt.month == month) &
            (df_all["tipo"] == "gasto")
        ]["monto"].sum()
        total_savings += salary - gastos

    return total_savings


def get_savings_with_extras() -> float:
    """Ahorro real incluyendo ingresos extra."""
    df_all = load_transactions()
    if df_all.empty:
        return 0.0

    df_all["fecha"] = pd.to_datetime(df_all["fecha"], errors="coerce")
    df_all = df_all[df_all["fecha"].dt.date <= date.today()]
    if df_all.empty:
        return 0.0

    months = df_all["fecha"].dropna().apply(lambda x: (x.year, x.month)).unique()

    total = 0.0
    for year, month in sorted(months):
        mes_df = df_all[
            (df_all["fecha"].dt.year == year) &
            (df_all["fecha"].dt.month == month)
        ]
        salary = get_salary_for_month(year, month)
        ingresos_extra = mes_df[mes_df["tipo"] == "ingreso"]["monto"].sum()
        gastos = mes_df[mes_df["tipo"] == "gasto"]["monto"].sum()
        total += salary + ingresos_extra - gastos
    return total


def get_monthly_available_money(year: int, month: int) -> float:
    """Dinero disponible del mes: ingresos totales del mes menos gastos del mes."""
    summary = get_monthly_summary(year, month)
    return summary["ingresos"] - summary["gastos"]


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12) + (month - 1) + delta
    return month_index // 12, (month_index % 12) + 1


def _monthly_date(year: int, month: int, original_day: int) -> date:
    """Devuelve la ocurrencia mensual, ajustando sólo los meses más cortos."""
    return date(year, month, min(original_day, calendar.monthrange(year, month)[1]))


def get_budget_period(year: int, month: int, start_day: int = 14) -> tuple[date, date]:
    """Periodo de presupuesto: start_day del mes al dia anterior del siguiente ciclo."""
    start = date(year, month, start_day)
    end_year, end_month = _shift_month(year, month, 1)
    end = date(end_year, end_month, start_day)
    return start, end


def get_current_budget_cycle(today: date = None, start_day: int = 14) -> tuple[int, int]:
    """Retorna el año/mes del ciclo actual según el dia de pago."""
    today = today or date.today()
    if today.day >= start_day:
        return today.year, today.month
    return _shift_month(today.year, today.month, -1)


def _filter_transactions_by_range(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    return df[(df["fecha"] >= start_ts) & (df["fecha"] < end_ts)]


def get_period_summary(start_date: date, end_date: date, salary_year: int = None, salary_month: int = None) -> dict:
    """Resumen para un rango [start_date, end_date), usando salario del mes indicado."""
    df = load_transactions()
    salary_year = salary_year or start_date.year
    salary_month = salary_month or start_date.month
    salary = get_salary_for_month(salary_year, salary_month)

    if df.empty:
        return {
            "ingresos": salary,
            "gastos": 0.0,
            "balance": salary,
            "salario": salary,
            "ingresos_extra": 0.0,
            "fecha_inicio": start_date,
            "fecha_fin": end_date,
        }

    period_df = _filter_transactions_by_range(df, start_date, end_date)
    ingresos_extra = period_df[period_df["tipo"] == "ingreso"]["monto"].sum()
    gastos = period_df[period_df["tipo"] == "gasto"]["monto"].sum()
    total_ingresos = salary + ingresos_extra

    return {
        "ingresos": total_ingresos,
        "gastos": gastos,
        "balance": total_ingresos - gastos,
        "salario": salary,
        "ingresos_extra": ingresos_extra,
        "fecha_inicio": start_date,
        "fecha_fin": end_date,
    }


def get_budget_cycle_summary(year: int, month: int, start_day: int = 14) -> dict:
    start_date, end_date = get_budget_period(year, month, start_day)
    return get_period_summary(start_date, end_date, year, month)


def get_budget_cycle_available_money(year: int, month: int, start_day: int = 14) -> float:
    summary = get_budget_cycle_summary(year, month, start_day)
    return summary["ingresos"] - summary["gastos"]


def find_duplicate_transaction(tipo: str, monto: float, fecha_mov: date, descripcion: str):
    """Busca un movimiento con misma descripción, monto, fecha y tipo."""
    df = load_transactions()
    if df.empty:
        return None

    target_desc = " ".join(str(descripcion or "").strip().lower().split())
    if not target_desc:
        return None

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce")

    descriptions = df["descripcion"].fillna("").astype(str).map(
        lambda value: " ".join(value.strip().lower().split())
    )
    target_date = pd.to_datetime(fecha_mov).date()

    mask = (
        (df["tipo"] == tipo) &
        (df["fecha"].dt.date == target_date) &
        (df["monto"].sub(float(monto)).abs() < 0.01) &
        (descriptions == target_desc)
    )

    matches = df[mask].sort_values("fecha", ascending=False)
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


def _split_tags(raw_tags) -> list[str]:
    if pd.isna(raw_tags):
        return []
    return [
        tag.strip()
        for tag in str(raw_tags).split("|")
        if tag.strip()
    ]


def _normalize_tag(tag) -> str:
    if tag is None or pd.isna(tag):
        return ""
    return str(tag).strip().casefold()


def _tag_matches(raw_tags, tag) -> bool:
    target = _normalize_tag(tag)
    tags = _split_tags(raw_tags)
    if target == "sin etiqueta":
        return not tags
    return any(_normalize_tag(item) == target for item in tags)


def _matches_any_tag(raw_tags, tags) -> bool:
    return any(_tag_matches(raw_tags, tag) for tag in tags or [])


def get_all_tags() -> list[str]:
    """Retorna todas las etiquetas usadas, sin duplicados."""
    df = load_transactions()
    if df.empty or "etiquetas" not in df.columns:
        return []

    tags = set()
    for raw_tags in df["etiquetas"].dropna():
        tags.update(_split_tags(raw_tags))
    return sorted(tags, key=str.lower)


def get_recent_tags(limit: int = 5) -> list[str]:
    """Retorna las últimas etiquetas distintas usadas."""
    df = load_transactions()
    if df.empty or "etiquetas" not in df.columns:
        return []

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    recent = []

    for _, row in df.sort_values("fecha", ascending=False).iterrows():
        for tag in _split_tags(row.get("etiquetas", "")):
            if tag not in recent:
                recent.append(tag)
            if len(recent) >= limit:
                return recent

    return recent


def get_tags_for_period(
    year: int = None,
    month: int = None,
    tipo: str = None,
    start_date: date = None,
    end_date: date = None,
) -> list[str]:
    """Retorna etiquetas usadas en un periodo, preservando el nombre original."""
    df = load_transactions(year) if year and not start_date else load_transactions()
    if df.empty or "etiquetas" not in df.columns:
        return []

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    if start_date and end_date:
        df = _filter_transactions_by_range(df, start_date, end_date)
    elif year and month:
        df = df[
            (df["fecha"].dt.year == year) &
            (df["fecha"].dt.month == month)
        ]
    if tipo:
        df = df[df["tipo"] == tipo]

    tags_by_key = {}
    include_untagged = False
    for raw_tags in df["etiquetas"].fillna(""):
        tags = _split_tags(raw_tags)
        if not tags:
            include_untagged = True
        for tag in tags:
            tags_by_key.setdefault(_normalize_tag(tag), tag)

    tags = sorted(tags_by_key.values(), key=str.lower)
    if include_untagged:
        tags.append("sin etiqueta")
    return tags


def get_transactions_by_tag(
    tag: str,
    year: int = None,
    month: int = None,
    tipo: str = None,
    start_date: date = None,
    end_date: date = None,
    exclude_tags: list[str] = None,
) -> pd.DataFrame:
    """Movimientos que contienen una etiqueta, aunque tengan varias separadas por |."""
    df = load_transactions(year) if year and not start_date else load_transactions()
    columns = ["fecha", "tipo", "descripcion", "monto", "etiquetas"]
    if df.empty or "etiquetas" not in df.columns or not str(tag or "").strip():
        return pd.DataFrame(columns=columns)

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)

    if start_date and end_date:
        df = _filter_transactions_by_range(df, start_date, end_date)
    elif year and month:
        df = df[
            (df["fecha"].dt.year == year) &
            (df["fecha"].dt.month == month)
        ]
    if tipo:
        df = df[df["tipo"] == tipo]

    matches = df[df["etiquetas"].apply(lambda value: _tag_matches(value, tag))].copy()
    if exclude_tags:
        matches = matches[
            ~matches["etiquetas"].apply(lambda value: _matches_any_tag(value, exclude_tags))
        ].copy()
    if matches.empty:
        return pd.DataFrame(columns=columns)

    return matches.sort_values("fecha", ascending=False)


def get_transactions_for_period(start_date: date, end_date: date, tipo: str = None) -> pd.DataFrame:
    """Movimientos en un rango [start_date, end_date), opcionalmente por tipo."""
    df = load_transactions()
    columns = ["fecha", "tipo", "descripcion", "monto", "etiquetas"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df = _filter_transactions_by_range(df, start_date, end_date)
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    if tipo:
        df = df[df["tipo"] == tipo]
    return df.sort_values("fecha", ascending=False)


def get_transactions_by_tags(
    tags: list[str],
    start_date: date,
    end_date: date,
    tipo: str = None,
    exclude_tags: list[str] = None,
) -> pd.DataFrame:
    """Movimientos que tienen cualquiera de las etiquetas indicadas."""
    df = get_transactions_for_period(start_date, end_date, tipo)
    if df.empty or not tags:
        return df

    matches = df[df["etiquetas"].apply(lambda value: _matches_any_tag(value, tags))].copy()
    if exclude_tags:
        matches = matches[
            ~matches["etiquetas"].apply(lambda value: _matches_any_tag(value, exclude_tags))
        ].copy()
    return matches.sort_values("fecha", ascending=False)


def get_monthly_chart_data(months_back: int = 12) -> pd.DataFrame:
    """Datos para la gráfica mensual: ingresos, gastos, ahorro."""
    today = date.today()
    rows = []
    for i in range(months_back - 1, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        summary = get_monthly_summary(year, month)
        rows.append({
            "periodo": f"{year}-{month:02d}",
            "ingresos": summary["ingresos"],
            "gastos": summary["gastos"],
            "balance": summary["balance"],
            "salario": summary["salario"],
        })
    return pd.DataFrame(rows)


def get_budget_cycle_chart_data(months_back: int = 12, start_day: int = 14) -> pd.DataFrame:
    """Datos para la grafica de ciclos de presupuesto 14->13."""
    cycle_year, cycle_month = get_current_budget_cycle(date.today(), start_day)
    rows = []
    for i in range(months_back - 1, -1, -1):
        year, month = _shift_month(cycle_year, cycle_month, -i)
        start_date, end_date = get_budget_period(year, month, start_day)
        summary = get_period_summary(start_date, end_date, year, month)
        rows.append({
            "periodo": f"{year}-{month:02d}",
            "rango": f"{start_date.strftime('%Y-%m-%d')} a {(end_date - timedelta(days=1)).strftime('%Y-%m-%d')}",
            "ingresos": summary["ingresos"],
            "gastos": summary["gastos"],
            "balance": summary["balance"],
            "salario": summary["salario"],
        })
    return pd.DataFrame(rows)


def get_expenses_by_tag(
    year: int = None,
    month: int = None,
    start_date: date = None,
    end_date: date = None,
) -> pd.DataFrame:
    """Gastos agrupados por etiqueta."""
    df = load_transactions(year) if year and not start_date else load_transactions()
    if df.empty:
        return pd.DataFrame(columns=["etiqueta", "monto"])

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    gastos = df[df["tipo"] == "gasto"].copy()

    if start_date and end_date:
        gastos = _filter_transactions_by_range(gastos, start_date, end_date)
    elif year and month:
        gastos = gastos[
            (gastos["fecha"].dt.year == year) &
            (gastos["fecha"].dt.month == month)
        ]

    rows = []
    for _, row in gastos.iterrows():
        tags = _split_tags(row.get("etiquetas", "")) or ["sin etiqueta"]
        for tag in tags:
            tag = tag.strip() or "sin etiqueta"
            rows.append({"etiqueta": tag, "monto": row["monto"]})

    if not rows:
        return pd.DataFrame(columns=["etiqueta", "monto"])

    tag_df = pd.DataFrame(rows)
    return tag_df.groupby("etiqueta", as_index=False)["monto"].sum().sort_values("monto", ascending=False)


def process_due_recurrentes(target_date: date = None, recurrente_id: str = None):
    """
    Registra recurrentes vencidos, sin duplicar cargos ya cobrados.
    Las mensualidades se procesan desde su fecha de inicio exacta hasta la fecha actual.
    Retorna lista de recurrentes procesados.
    """
    today = target_date or date.today()
    df = load_recurrentes()
    processed = []

    if df.empty:
        return processed

    activos = df[df["activo"] == True]
    if recurrente_id:
        activos = activos[activos["id"].astype(str) == str(recurrente_id)]

    txns = load_transactions()
    if not txns.empty:
        txns = txns.copy()
        txns["fecha"] = pd.to_datetime(txns["fecha"], errors="coerce")

    for _, rec in activos.iterrows():
        fecha_inicio = pd.to_datetime(rec.get("fecha_inicio"), errors="coerce")
        if pd.isna(fecha_inicio) or fecha_inicio.date() > today:
            continue

        inicio = fecha_inicio.date()
        dia_inicio = inicio.day

        if rec["tipo_recurrencia"] == "mensualidades":
            meses_total_raw = rec.get("meses_total")
            if pd.isna(meses_total_raw):
                continue
            meses_total = int(meses_total_raw)

            fecha_cobro = inicio
            fechas_programadas = []
            while fecha_cobro <= today and len(fechas_programadas) < meses_total:
                fechas_programadas.append(fecha_cobro)
                next_year, next_month = _shift_month(fecha_cobro.year, fecha_cobro.month, 1)
                fecha_cobro = _monthly_date(next_year, next_month, dia_inicio)
        else:
            fecha_cobro = _monthly_date(today.year, today.month, dia_inicio)
            if fecha_cobro > today:
                continue
            fechas_programadas = [fecha_cobro]

        meses_registrados = set()
        if not txns.empty:
            descripcion_txn = txns["descripcion"].fillna("").astype(str)
            txns_rec = txns[
                (txns["recurrente_id"].astype(str) == str(rec["id"])) &
                (descripcion_txn.str.startswith("[Recurrente]")) &
                txns["fecha"].notna()
            ]
            meses_registrados = {
                (int(fecha.year), int(fecha.month))
                for fecha in txns_rec["fecha"]
            }

        registro_nuevo = False
        for fecha_cobro in fechas_programadas:
            clave_mes = (fecha_cobro.year, fecha_cobro.month)
            if clave_mes in meses_registrados:
                continue

            save_transaction({
                "fecha": fecha_cobro.strftime("%Y-%m-%d"),
                "tipo": "gasto",
                "monto": rec["monto"],
                "descripcion": f"[Recurrente] {rec['nombre']}",
                "etiquetas": rec.get("etiquetas", ""),
                "recurrente_id": rec["id"],
                "moneda_original": "MXN",
                "monto_original": rec["monto"],
            })
            meses_registrados.add(clave_mes)
            registro_nuevo = True

        if rec["tipo_recurrencia"] == "mensualidades":
            meses_pagados = min(len(meses_registrados), meses_total)
            update_recurrente(rec["id"], {
                "meses_pagados": meses_pagados,
                "activo": meses_pagados < meses_total,
            })

        if registro_nuevo:
            processed.append(rec["nombre"])

    return processed


def process_planned_recurrentes_for_cycle(
    cycle_start: date,
    cycle_end: date,
    today: date = None,
    recurrente_id: str = None,
):
    """
    Registra por anticipado los cobros recurrentes que aún no vencen, pero que
    caen dentro del ciclo de presupuesto indicado. Conserva la fecha real de
    cobro para que el gasto aparezca en el ciclo correcto sin contarse como
    ahorro real antes de tiempo.

    ``cycle_end`` es exclusivo, igual que los demás rangos de presupuesto.
    """
    today = today or date.today()
    if cycle_start >= cycle_end:
        return []

    window_start = max(cycle_start, today)
    window_end = cycle_end
    if window_start >= window_end:
        return []

    df = load_recurrentes()
    if df.empty:
        return []

    activos = df[df["activo"] == True]
    if recurrente_id:
        activos = activos[activos["id"].astype(str) == str(recurrente_id)]

    txns = load_transactions()
    if not txns.empty:
        txns = txns.copy()
        txns["fecha"] = pd.to_datetime(txns["fecha"], errors="coerce")

    processed = []
    for _, rec in activos.iterrows():
        fecha_inicio = pd.to_datetime(rec.get("fecha_inicio"), errors="coerce")
        if pd.isna(fecha_inicio):
            continue

        inicio = fecha_inicio.date()
        if inicio >= window_end:
            continue

        meses_total = None
        if rec["tipo_recurrencia"] == "mensualidades":
            meses_total_raw = rec.get("meses_total")
            if pd.isna(meses_total_raw):
                continue
            meses_total = int(meses_total_raw)

        meses_registrados = set()
        if not txns.empty:
            descripcion_txn = txns["descripcion"].fillna("").astype(str)
            txns_rec = txns[
                (txns["recurrente_id"].astype(str) == str(rec["id"])) &
                (descripcion_txn.str.startswith("[Recurrente]")) &
                txns["fecha"].notna()
            ]
            meses_registrados = {
                (int(fecha.year), int(fecha.month))
                for fecha in txns_rec["fecha"]
            }

        fecha_cobro = inicio
        indice_mensualidad = 0
        registro_nuevo = False
        while fecha_cobro < window_end:
            if meses_total is not None and indice_mensualidad >= meses_total:
                break

            clave_mes = (fecha_cobro.year, fecha_cobro.month)
            if fecha_cobro >= window_start and clave_mes not in meses_registrados:
                save_transaction({
                    "fecha": fecha_cobro.strftime("%Y-%m-%d"),
                    "tipo": "gasto",
                    "monto": rec["monto"],
                    "descripcion": f"[Recurrente] {rec['nombre']}",
                    "etiquetas": rec.get("etiquetas", ""),
                    "recurrente_id": rec["id"],
                    "moneda_original": "MXN",
                    "monto_original": rec["monto"],
                })
                meses_registrados.add(clave_mes)
                registro_nuevo = True

            indice_mensualidad += 1
            next_year, next_month = _shift_month(fecha_cobro.year, fecha_cobro.month, 1)
            fecha_cobro = _monthly_date(next_year, next_month, inicio.day)

        if registro_nuevo:
            processed.append(rec["nombre"])

    return processed


def register_first_installment_for_recurrente(rec_id: str, fecha_pago: date) -> bool:
    """Registra una primera mensualidad ya pagada, sin confundirla con un enganche."""
    df = load_recurrentes()
    if df.empty or rec_id not in set(df["id"].astype(str)):
        return False

    rec = df[df["id"].astype(str) == str(rec_id)].iloc[0]
    if rec["tipo_recurrencia"] != "mensualidades":
        return False

    fecha = pd.to_datetime(fecha_pago, errors="coerce")
    if pd.isna(fecha) or fecha.date() > date.today():
        return False

    txns = load_transactions()
    if not txns.empty:
        txns = txns.copy()
        txns["fecha"] = pd.to_datetime(txns["fecha"], errors="coerce")
        descripcion_txn = txns["descripcion"].fillna("").astype(str)
        ya_registrada = txns[
            (txns["recurrente_id"].astype(str) == str(rec_id)) &
            (txns["tipo"] == "gasto") &
            descripcion_txn.str.startswith("[Recurrente]") &
            (txns["fecha"].dt.year == fecha.year) &
            (txns["fecha"].dt.month == fecha.month)
        ]
        if not ya_registrada.empty:
            return False

    save_transaction({
        "fecha": fecha.strftime("%Y-%m-%d"),
        "tipo": "gasto",
        "monto": rec["monto"],
        "descripcion": f"[Recurrente] {rec['nombre']}",
        "etiquetas": rec.get("etiquetas", ""),
        "recurrente_id": rec_id,
        "moneda_original": "MXN",
        "monto_original": rec["monto"],
    })
    return True


def register_initial_payment_for_recurrente(rec_id: str) -> bool:
    """Registra el pago inicial de un recurrente una sola vez."""
    df = load_recurrentes()
    if df.empty or rec_id not in set(df["id"].astype(str)):
        return False

    rec = df[df["id"].astype(str) == rec_id].iloc[0]
    tiene_pago = bool(rec.get("tiene_pago_inicial", False))
    ya_registrado = bool(rec.get("pago_inicial_registrado", False))
    monto = pd.to_numeric(rec.get("monto_pago_inicial", 0), errors="coerce")

    if not tiene_pago or ya_registrado or pd.isna(monto) or float(monto) <= 0:
        return False

    fecha_pago = pd.to_datetime(rec.get("fecha_pago_inicial"), errors="coerce")
    if pd.isna(fecha_pago):
        fecha_pago = pd.to_datetime(rec.get("fecha_inicio"), errors="coerce")
    if pd.isna(fecha_pago):
        fecha_pago = pd.Timestamp(date.today())

    descripcion_raw = rec.get("descripcion_pago_inicial", "")
    descripcion = "" if pd.isna(descripcion_raw) else str(descripcion_raw).strip()
    if not descripcion:
        descripcion = f"[Enganche] {rec['nombre']}"

    etiquetas_raw = rec.get("etiquetas_pago_inicial", "")
    etiquetas = "" if pd.isna(etiquetas_raw) else str(etiquetas_raw).strip()
    if not etiquetas:
        etiquetas_base = rec.get("etiquetas", "")
        etiquetas = "" if pd.isna(etiquetas_base) else str(etiquetas_base)

    txns = load_transactions(fecha_pago.year)
    if not txns.empty:
        txns = txns.copy()
        txns["fecha"] = pd.to_datetime(txns["fecha"], errors="coerce")
        txns["monto"] = pd.to_numeric(txns["monto"], errors="coerce")
        descripcion_txn = txns["descripcion"].fillna("").astype(str)
        duplicado = txns[
            (txns["recurrente_id"] == rec_id) &
            (txns["tipo"] == "gasto") &
            (
                descripcion_txn.str.startswith("[Enganche]") |
                (
                    (txns["fecha"].dt.date == fecha_pago.date()) &
                    (txns["monto"].sub(float(monto)).abs() < 0.01)
                )
            )
        ]
        if not duplicado.empty:
            update_recurrente(rec_id, {"pago_inicial_registrado": True})
            return False

    save_transaction({
        "fecha": fecha_pago.strftime("%Y-%m-%d"),
        "tipo": "gasto",
        "monto": float(monto),
        "descripcion": descripcion,
        "etiquetas": etiquetas,
        "recurrente_id": rec_id,
        "moneda_original": "MXN",
        "monto_original": float(monto),
    })
    update_recurrente(rec_id, {"pago_inicial_registrado": True})
    return True


def process_due_ingresos_recurrentes(target_date: date = None):
    """
    Registra ingresos semanales vencidos desde su fecha de inicio, sin duplicarlos.
    Retorna lista de ingresos procesados.
    """
    today = target_date or date.today()
    df = load_ingresos_recurrentes()
    processed = []

    if df.empty:
        return processed

    existing_weeks = set()
    txns = load_transactions()
    if not txns.empty:
        txns = txns.copy()
        txns["fecha"] = pd.to_datetime(txns["fecha"], errors="coerce")
        for _, txn in txns.dropna(subset=["fecha"]).iterrows():
            recurrente_id = str(txn.get("recurrente_id", "") or "")
            if not recurrente_id:
                continue
            txn_date = txn["fecha"].date()
            txn_week_start = txn_date - timedelta(days=txn_date.weekday())
            existing_weeks.add((recurrente_id, txn_week_start))

    activos = df[df["activo"] == True]

    for _, ingreso in activos.iterrows():
        dia_raw = ingreso.get("dia_semana", 0)
        dia_semana = int(dia_raw) if pd.notna(dia_raw) else 0
        dia_semana = min(max(dia_semana, 0), 6)

        fecha_inicio = pd.to_datetime(ingreso.get("fecha_inicio"), errors="coerce")
        if pd.isna(fecha_inicio):
            fecha_inicio = pd.Timestamp(today)
        fecha_inicio = fecha_inicio.date()
        if fecha_inicio > today:
            continue

        fecha_fin = pd.to_datetime(ingreso.get("fecha_fin"), errors="coerce")
        fecha_fin_date = fecha_fin.date() if pd.notna(fecha_fin) else None
        fecha_limite = today
        if fecha_fin_date:
            fecha_limite = min(fecha_limite, fecha_fin_date)

        if fecha_limite < fecha_inicio:
            if fecha_fin_date and fecha_fin_date < today:
                update_ingreso_recurrente(ingreso["id"], {"activo": False})
            continue

        inicio_semana = fecha_inicio - timedelta(days=fecha_inicio.weekday())
        fecha_pago = inicio_semana + timedelta(days=dia_semana)
        if fecha_pago < fecha_inicio:
            fecha_pago += timedelta(days=7)

        while fecha_pago <= fecha_limite:
            week_start = fecha_pago - timedelta(days=fecha_pago.weekday())
            week_key = (str(ingreso["id"]), week_start)

            if week_key not in existing_weeks:
                save_transaction({
                    "fecha": fecha_pago.strftime("%Y-%m-%d"),
                    "tipo": "ingreso",
                    "monto": ingreso["monto"],
                    "descripcion": f"[Ingreso recurrente] {ingreso['nombre']}",
                    "etiquetas": ingreso.get("etiquetas", ""),
                    "recurrente_id": ingreso["id"],
                    "moneda_original": "MXN",
                    "monto_original": ingreso["monto"],
                })
                existing_weeks.add(week_key)
                processed.append(f"{ingreso['nombre']} ({fecha_pago.strftime('%Y-%m-%d')})")

            fecha_pago += timedelta(days=7)

        if fecha_fin_date and fecha_fin_date <= today:
            update_ingreso_recurrente(ingreso["id"], {"activo": False})

    return processed


def snapshot_savings():
    """Guarda snapshot del ahorro actual en ahorros.csv."""
    salary = get_current_salary()
    savings = get_savings_with_extras()
    update_savings_snapshot(savings, salary)
