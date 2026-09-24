"""
app.py — Finanzas Personales
Streamlit app para gestión de ingresos, gastos, metas y ahorro.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import os

from modules.data_manager import (
    load_transactions, save_transaction, delete_transaction, update_transaction,
    load_recurrentes, save_recurrente, cancel_recurrente,
    load_ingresos_recurrentes, save_ingreso_recurrente,
    update_ingreso_recurrente, cancel_ingreso_recurrente,
    load_metas, save_meta, update_meta, delete_meta,
    load_savings, get_current_salary, set_salary,
    load_salary_history, ensure_startup_data_integrity,
)
from modules.currency import get_rate_info, mxn_to_usd, format_currency
from modules.calculations import (
    get_monthly_summary, get_cumulative_savings, get_savings_with_extras,
    get_monthly_available_money, get_monthly_chart_data, get_expenses_by_tag, process_due_recurrentes,
    process_planned_recurrentes_for_cycle,
    get_budget_period, get_current_budget_cycle, get_budget_cycle_summary,
    get_budget_cycle_available_money, get_budget_cycle_chart_data, get_period_summary,
    process_due_ingresos_recurrentes,
    snapshot_savings, find_duplicate_transaction, get_all_tags, get_recent_tags,
    get_tags_for_period, get_transactions_by_tag, get_transactions_for_period, get_transactions_by_tags,
    register_initial_payment_for_recurrente, register_first_installment_for_recurrente,
)

# ─── Config ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finanzas",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
}

.metric-card .label {
    font-size: 0.75rem;
    color: #8899aa;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}

.metric-card .value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: #e2e8f0;
}

.metric-card .value.positive { color: #4ade80; }
.metric-card .value.negative { color: #f87171; }
.metric-card .value.accent { color: #60a5fa; }

.metric-card .sub {
    font-size: 0.72rem;
    color: #4ade80;
    margin-top: 0.2rem;
    font-family: 'JetBrains Mono', monospace;
}

.tag-pill {
    display: inline-block;
    background: #0f3460;
    color: #60a5fa;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.72rem;
    margin: 2px;
    font-weight: 500;
}

.rate-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #fbbf24;
    background: #292219;
    border: 1px solid #7c5e10;
    border-radius: 8px;
    padding: 4px 10px;
    display: inline-block;
    margin-bottom: 1rem;
}

.section-header {
    font-size: 1.05rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 0.4rem;
    margin: 1.2rem 0 0.8rem 0;
}

.alert-info {
    background: #0c1a2e;
    border-left: 3px solid #3b82f6;
    padding: 0.6rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.85rem;
    color: #93c5fd;
    margin-bottom: 0.8rem;
}

.goal-bar-outer {
    background: #1e293b;
    border-radius: 999px;
    height: 10px;
    margin: 8px 0;
    overflow: hidden;
}

.goal-bar-inner {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    transition: width 0.5s ease;
}
</style>
""", unsafe_allow_html=True)


def metric_html(label, value, cls="", sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="metric-card"><div class="label">{label}</div><div class="value {cls}">{value}</div>{sub_html}</div>'


def clean_tags(tags) -> list[str]:
    cleaned = []
    for tag in tags or []:
        normalized = str(tag).strip()
        if normalized and normalized.lower() != "nan" and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def tags_to_text(tags) -> str:
    return "|".join(clean_tags(tags))


def parse_transaction_dates(values):
    try:
        return pd.to_datetime(values, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(values, errors="coerce")


def format_transaction_date(value, fallback="—") -> str:
    parsed = parse_transaction_dates(value)
    if pd.isna(parsed):
        return fallback
    return parsed.strftime("%Y-%m-%d")


def tag_selector(label, key, default=None):
    recent_tags = get_recent_tags(5)
    all_tags = get_all_tags()
    options = recent_tags + [tag for tag in all_tags if tag not in recent_tags]
    placeholder = "Busca etiquetas anteriores o escribe una nueva"

    try:
        selected = st.multiselect(
            label,
            options=options,
            default=clean_tags(default),
            placeholder=placeholder,
            accept_new_options=True,
            key=key,
        )
    except TypeError:
        selected = st.multiselect(
            label,
            options=options,
            default=[tag for tag in clean_tags(default) if tag in options],
            key=key,
        )
        new_tags = st.text_input("Etiquetas nuevas (separadas por coma)", key=f"{key}_new")
        selected = selected + [tag.strip() for tag in new_tags.split(",") if tag.strip()]

    if recent_tags:
        st.caption(f"Recientes: {', '.join(recent_tags)}")
    return clean_tags(selected)


def movement_type_selector(key):
    return segmented_selector("Tipo", ["Gasto", "Ingreso extra"], key, "Gasto")


def segmented_selector(label, options, key, default=None):
    default = default or options[0]
    if hasattr(st, "segmented_control"):
        kwargs = {"key": key}
        if key not in st.session_state:
            kwargs["default"] = default
        selected = st.segmented_control(label, options, **kwargs)
        return selected or default

    if key not in st.session_state:
        st.session_state[key] = default

    st.markdown(f"**{label}**")
    cols = st.columns(len(options))
    for col, option in zip(cols, options):
        with col:
            if st.button(
                option,
                type="primary" if st.session_state[key] == option else "secondary",
                use_container_width=True,
                key=f"{key}_{option}",
            ):
                st.session_state[key] = option

    return st.session_state[key]


def show_movement_feedback():
    movement_feedback = st.session_state.get("movement_feedback")
    if movement_feedback:
        st.success(movement_feedback)
        st.toast(movement_feedback, icon="✅")
        del st.session_state["movement_feedback"]


DIAS_SEMANA = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Domingo": 6,
}


def nombre_dia_semana(dia_semana) -> str:
    try:
        dia_int = int(dia_semana)
    except (TypeError, ValueError):
        dia_int = 0
    for nombre, valor in DIAS_SEMANA.items():
        if valor == dia_int:
            return nombre
    return "Lunes"


if "startup_data_integrity_checked_v4" not in st.session_state:
    ensure_startup_data_integrity()
    recurrentes_procesados_inicio = process_due_recurrentes()
    current_cycle_year, current_cycle_month = get_current_budget_cycle(date.today())
    current_cycle_start, current_cycle_end = get_budget_period(current_cycle_year, current_cycle_month)
    process_planned_recurrentes_for_cycle(
        current_cycle_start, current_cycle_end
    )
    st.cache_data.clear()
    st.session_state["startup_data_integrity_checked_v4"] = True
    if recurrentes_procesados_inicio:
        snapshot_savings()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 Finanzas")

    rate_info = get_rate_info()
    st.markdown(f'<div class="rate-badge">🏦 {rate_info["label"]} · {rate_info["updated"]}</div>', unsafe_allow_html=True)

    today_sidebar = date.today()
    sidebar_cycle_year, sidebar_cycle_month = get_current_budget_cycle(today_sidebar)
    sidebar_cycle_start, sidebar_cycle_end = get_budget_period(sidebar_cycle_year, sidebar_cycle_month)
    dinero_total = get_budget_cycle_available_money(sidebar_cycle_year, sidebar_cycle_month)
    dinero_total_cls = "positive" if dinero_total >= 0 else "negative"
    st.markdown(metric_html(
        "Dinero del ciclo",
        format_currency(dinero_total),
        dinero_total_cls,
        f"{sidebar_cycle_start.strftime('%d/%m')} - {(sidebar_cycle_end - pd.Timedelta(days=1)).strftime('%d/%m')} - aprox. {format_currency(mxn_to_usd(dinero_total), 'USD')}",
    ), unsafe_allow_html=True)

    salario_actual = get_current_salary()
    st.markdown(metric_html(
        "Salario base mensual",
        format_currency(salario_actual),
        "accent",
        f"≈ {format_currency(mxn_to_usd(salario_actual), 'USD')}",
    ), unsafe_allow_html=True)

    st.divider()

    paginas = [
        "📊 Dashboard",
        "➕ Registrar movimiento",
        "📅 Mes a Mes",
        "✏️ Editar movimientos",
        "🔄 Recurrentes",
        "💵 Ingresos recurrentes",
        "🎯 Metas",
        "💾 Ahorros",
        "⚙️ Configuración",
    ]

    pagina = st.radio(
        "Navegación",
        paginas,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("📸 Guardar snapshot de ahorro", use_container_width=True):
        snapshot_savings()
        st.success("Snapshot guardado en ahorros.csv")


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

if pagina == "📊 Dashboard":
    st.title("📊 Dashboard")

    today = date.today()
    default_cycle_year, default_cycle_month = get_current_budget_cycle(today)
    col_year, col_month = st.columns([1, 1])
    with col_year:
        year_options = list(range(today.year, today.year - 5, -1))
        sel_year = st.selectbox(
            "Año",
            year_options,
            index=year_options.index(default_cycle_year) if default_cycle_year in year_options else 0,
        )
    with col_month:
        meses_nombres = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        sel_month = st.selectbox("Mes", range(1, 13),
                                 index=default_cycle_month - 1,
                                 format_func=lambda x: meses_nombres[x-1])

    cycle_start, cycle_end = get_budget_period(sel_year, sel_month)
    cycle_end_display = cycle_end - pd.Timedelta(days=1)
    st.caption(
        f"Ciclo de presupuesto: {cycle_start.strftime('%Y-%m-%d')} a {cycle_end_display.strftime('%Y-%m-%d')}"
    )

    summary = get_budget_cycle_summary(sel_year, sel_month)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(metric_html(
            "Ingresos del ciclo",
            format_currency(summary["ingresos"]),
            "positive",
            f"Salario {format_currency(summary['salario'])} + extras {format_currency(summary['ingresos_extra'])}"
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(metric_html(
            "Gastos del ciclo",
            format_currency(summary["gastos"]),
            "negative",
            "Incluye cobros recurrentes programados en este ciclo",
        ), unsafe_allow_html=True)

    with c3:
        cls = "positive" if summary["balance"] >= 0 else "negative"
        st.markdown(metric_html(
            "Balance del ciclo",
            format_currency(summary["balance"]),
            cls,
        ), unsafe_allow_html=True)

    with c4:
        ahorro_acum = get_savings_with_extras()
        ahorro_solo_salario = get_cumulative_savings()
        st.markdown(metric_html(
            "Ahorro acumulado real",
            format_currency(ahorro_acum),
            "positive" if ahorro_acum >= 0 else "negative",
            f"Historico real - solo salario: {format_currency(ahorro_solo_salario)} - aprox. {format_currency(mxn_to_usd(ahorro_acum), 'USD')}"
        ), unsafe_allow_html=True)

    st.divider()

    # Gráfica mensual
    col_g1, col_g2 = st.columns([2, 1])

    with col_g1:
        st.markdown('<div class="section-header">Movimientos últimos 12 ciclos</div>', unsafe_allow_html=True)
        n_meses = st.slider("Ciclos a visualizar", 3, 24, 12, key="slider_meses")
        chart_df = get_budget_cycle_chart_data(n_meses)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_df["periodo"], y=chart_df["ingresos"],
            name="Ingresos", marker_color="#4ade80", opacity=0.85,
        ))
        fig.add_trace(go.Bar(
            x=chart_df["periodo"], y=chart_df["gastos"],
            name="Gastos", marker_color="#f87171", opacity=0.85,
        ))
        fig.add_trace(go.Scatter(
            x=chart_df["periodo"], y=chart_df["balance"],
            name="Balance", mode="lines+markers",
            line=dict(color="#60a5fa", width=2),
            marker=dict(size=6),
        ))
        fig.update_layout(
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.markdown('<div class="section-header">Uso del dinero del ciclo</div>', unsafe_allow_html=True)
        total_disponible_mes = summary["salario"] + summary["ingresos_extra"]
        gastos_mes = summary["gastos"]
        restante_mes = max(total_disponible_mes - gastos_mes, 0)

        if gastos_mes > total_disponible_mes:
            st.warning("Los gastos superan los ingresos del ciclo.")

        if total_disponible_mes <= 0 and gastos_mes <= 0:
            st.info("Sin ingresos o gastos para graficar este mes.")
        else:
            gastos_grafica = min(gastos_mes, total_disponible_mes) if total_disponible_mes > 0 else gastos_mes
            uso_df = pd.DataFrame([
                {
                    "categoria": "Gastos",
                    "monto": max(gastos_grafica, 0),
                    "detalle": f"Gastos registrados y programados: {format_currency(gastos_mes)}",
                },
                {
                    "categoria": "Restante",
                    "monto": restante_mes,
                    "detalle": f"Restante: {format_currency(restante_mes)}",
                },
            ])
            fig_usage = go.Figure(data=[go.Pie(
                labels=uso_df["categoria"],
                values=uso_df["monto"],
                hole=0.58,
                sort=False,
                marker=dict(
                    colors=["#f87171", "#4ade80"],
                    line=dict(color="#0f172a", width=2),
                ),
                textinfo="label+percent",
                textposition="inside",
                customdata=uso_df["detalle"],
                hovertemplate="%{label}<br>%{percent}<br>%{customdata}<extra></extra>",
            )])
            fig_usage.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=260,
            )
            st.plotly_chart(fig_usage, use_container_width=True)

        st.markdown('<div class="section-header">Gastos por etiqueta</div>', unsafe_allow_html=True)
        tag_df = get_expenses_by_tag(start_date=cycle_start, end_date=cycle_end)
        if tag_df.empty:
            st.info("Sin gastos etiquetados en este ciclo.")
        else:
            fig2 = px.pie(
                tag_df, values="monto", names="etiqueta",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=True,
                legend=dict(font=dict(size=11)),
                margin=dict(l=0, r=0, t=10, b=0),
                height=320,
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-header">Detalle por etiqueta</div>', unsafe_allow_html=True)
        tag_scope = segmented_selector(
            "Rango",
            ["Solo ciclo seleccionado", "Todo el historial"],
            "dashboard_tag_scope_cycle",
            "Solo ciclo seleccionado",
        )
        detail_year = None
        detail_month = None
        detail_start = cycle_start if tag_scope == "Solo ciclo seleccionado" else None
        detail_end = cycle_end if tag_scope == "Solo ciclo seleccionado" else None
        detail_tags = get_tags_for_period(start_date=detail_start, end_date=detail_end)

        if not detail_tags:
            st.info("Sin etiquetas para mostrar en este rango.")
        else:
            tag_key = f"dashboard_tag_detail_{detail_start or 'all'}_{detail_end or 'all'}"
            selected_tag = st.selectbox("Etiqueta", detail_tags, key=tag_key)
            exclude_options = [tag for tag in detail_tags if tag != selected_tag]
            exclude_tags = st.multiselect(
                "Excluir etiquetas",
                options=exclude_options,
                default=[],
                placeholder="Oculta movimientos que tengan cualquiera de estas etiquetas",
                key=f"dashboard_tag_exclude_{detail_start or 'all'}_{detail_end or 'all'}_{selected_tag}",
            )
            tag_movs = get_transactions_by_tag(
                selected_tag,
                start_date=detail_start,
                end_date=detail_end,
                exclude_tags=exclude_tags,
            )

            if tag_movs.empty:
                st.info("Sin movimientos para esta etiqueta con los filtros actuales.")
            else:
                total_gastos_tag = tag_movs[tag_movs["tipo"] == "gasto"]["monto"].sum()
                total_ingresos_tag = tag_movs[tag_movs["tipo"] == "ingreso"]["monto"].sum()
                period_label = (
                    f"del {cycle_start.strftime('%Y-%m-%d')} al {cycle_end_display.strftime('%Y-%m-%d')}"
                    if tag_scope == "Solo ciclo seleccionado"
                    else "historico"
                )

                if total_gastos_tag > 0:
                    total_label = f"Total gastado en {selected_tag} {period_label}"
                    total_value = total_gastos_tag
                    total_cls = "negative"
                else:
                    total_label = f"Total ingresado en {selected_tag} {period_label}"
                    total_value = total_ingresos_tag
                    total_cls = "positive"

                sub_parts = [f"{len(tag_movs)} movimientos"]
                if exclude_tags:
                    sub_parts.append(f"Excluye: {', '.join(exclude_tags)}")
                if total_ingresos_tag > 0:
                    sub_parts.append(f"Ingresos: {format_currency(total_ingresos_tag)}")
                if total_gastos_tag > 0:
                    sub_parts.append(f"Gastos: {format_currency(total_gastos_tag)}")

                st.markdown(metric_html(
                    total_label,
                    format_currency(total_value),
                    total_cls,
                    " - ".join(sub_parts),
                ), unsafe_allow_html=True)

                detail_table = tag_movs[["fecha", "tipo", "descripcion", "monto", "etiquetas"]].copy()
                detail_table["fecha"] = detail_table["fecha"].apply(format_transaction_date)
                detail_table["tipo"] = detail_table["tipo"].map({
                    "gasto": "Gasto",
                    "ingreso": "Ingreso",
                }).fillna(detail_table["tipo"])
                detail_table["monto"] = detail_table["monto"].apply(format_currency)
                detail_table = detail_table.rename(columns={
                    "fecha": "Fecha",
                    "tipo": "Tipo",
                    "descripcion": "Descripcion",
                    "monto": "Monto",
                    "etiquetas": "Etiquetas",
                })
                st.dataframe(detail_table, use_container_width=True, hide_index=True)

    # Últimas transacciones del ciclo
    st.markdown('<div class="section-header">Últimos movimientos del ciclo</div>', unsafe_allow_html=True)
    df_txn = load_transactions()
    if not df_txn.empty:
        df_txn["fecha"] = parse_transaction_dates(df_txn["fecha"])
        mes_txn = df_txn[
            (df_txn["fecha"] >= pd.Timestamp(cycle_start)) &
            (df_txn["fecha"] < pd.Timestamp(cycle_end))
        ].sort_values("fecha", ascending=False).head(20)

        if mes_txn.empty:
            st.info("Sin movimientos en este ciclo.")
        else:
            for _, row in mes_txn.iterrows():
                tipo_icon = "🟢" if row["tipo"] == "ingreso" else "🔴"
                tags_html = "".join([
                    f'<span class="tag-pill">{t.strip()}</span>'
                    for t in str(row.get("etiquetas", "") or "").split("|") if t.strip()
                ])
                fecha_fmt = format_transaction_date(row["fecha"])
                monto_fmt = format_currency(row["monto"])
                usd_fmt = f"≈ {format_currency(mxn_to_usd(row['monto']), 'USD')}"
                st.markdown(
                    f"{tipo_icon} **{row.get('descripcion', '—')}** · `{monto_fmt}` · "
                    f"<span style='color:#64748b;font-size:0.8rem'>{fecha_fmt} · {usd_fmt}</span> {tags_html}",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Sin movimientos registrados.")


# ─── MES A MES ────────────────────────────────────────────────────────────────

elif pagina == "📅 Mes a Mes":
    st.title("📅 Mes a Mes")

    today = date.today()
    default_cycle_year, default_cycle_month = get_current_budget_cycle(today)
    default_start, default_end = get_budget_period(default_cycle_year, default_cycle_month)
    default_end_display = (pd.Timestamp(default_end) - pd.Timedelta(days=1)).date()

    st.markdown('<div class="section-header">Filtros</div>', unsafe_allow_html=True)
    mode_col, type_col = st.columns([1, 1])
    with mode_col:
        date_mode = segmented_selector(
            "Fecha final",
            ["Rango", "Hasta hoy"],
            "mes_a_mes_date_mode",
            "Rango",
        )
    with type_col:
        type_filter = segmented_selector(
            "Tipo",
            ["Todos", "Gastos", "Ingresos"],
            "mes_a_mes_type_filter",
            "Todos",
        )

    date_col1, date_col2 = st.columns([1, 1])
    with date_col1:
        fecha_inicio = st.date_input(
            "Fecha inicial",
            value=default_start,
            key="mes_a_mes_fecha_inicio",
        )
    with date_col2:
        if date_mode == "Rango":
            fecha_fin = st.date_input(
                "Fecha final",
                value=default_end_display,
                key="mes_a_mes_fecha_fin",
            )
        else:
            fecha_fin = today
            st.markdown("**Fecha final**")
            st.caption(f"Hasta hoy: {fecha_fin.strftime('%Y-%m-%d')}")

    if fecha_fin < fecha_inicio:
        st.error("La fecha final no puede ser anterior a la fecha inicial.")
        st.stop()

    end_exclusive = (pd.Timestamp(fecha_fin) + pd.Timedelta(days=1)).date()
    tipo_value = {
        "Todos": None,
        "Gastos": "gasto",
        "Ingresos": "ingreso",
    }[type_filter]

    available_tags = get_tags_for_period(
        tipo=tipo_value,
        start_date=fecha_inicio,
        end_date=end_exclusive,
    )
    selected_tags = st.multiselect(
        "Categorias",
        options=available_tags,
        default=[],
        placeholder="Elige una o varias etiquetas",
        key=f"mes_a_mes_tags_{fecha_inicio}_{fecha_fin}_{type_filter}",
    )

    st.caption(f"Periodo analizado: {fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}")

    summary = get_period_summary(fecha_inicio, end_exclusive, fecha_inicio.year, fecha_inicio.month)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_html(
            "Ingresos del periodo",
            format_currency(summary["ingresos"]),
            "positive",
            f"Salario {format_currency(summary['salario'])} + extras {format_currency(summary['ingresos_extra'])}"
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_html(
            "Gastos del periodo",
            format_currency(summary["gastos"]),
            "negative",
        ), unsafe_allow_html=True)
    with c3:
        cls = "positive" if summary["balance"] >= 0 else "negative"
        st.markdown(metric_html(
            "Balance del periodo",
            format_currency(summary["balance"]),
            cls,
        ), unsafe_allow_html=True)

    st.divider()
    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.markdown('<div class="section-header">Uso del dinero del periodo</div>', unsafe_allow_html=True)
        total_disponible_mes = summary["salario"] + summary["ingresos_extra"]
        gastos_mes = summary["gastos"]
        restante_mes = max(total_disponible_mes - gastos_mes, 0)

        if gastos_mes > total_disponible_mes:
            st.warning("Los gastos superan los ingresos del periodo.")

        if total_disponible_mes <= 0 and gastos_mes <= 0:
            st.info("Sin ingresos o gastos para graficar este periodo.")
        else:
            gastos_grafica = min(gastos_mes, total_disponible_mes) if total_disponible_mes > 0 else gastos_mes
            uso_df = pd.DataFrame([
                {"categoria": "Gastos", "monto": max(gastos_grafica, 0)},
                {"categoria": "Restante", "monto": restante_mes},
            ])
            fig_usage = go.Figure(data=[go.Pie(
                labels=uso_df["categoria"],
                values=uso_df["monto"],
                hole=0.58,
                sort=False,
                marker=dict(colors=["#f87171", "#4ade80"], line=dict(color="#0f172a", width=2)),
                textinfo="label+percent",
                textposition="inside",
                hovertemplate="%{label}<br>%{percent}<extra></extra>",
            )])
            fig_usage.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(fig_usage, use_container_width=True)

    with col_m2:
        st.markdown('<div class="section-header">Gastos por etiqueta</div>', unsafe_allow_html=True)
        tag_df = get_expenses_by_tag(start_date=fecha_inicio, end_date=end_exclusive)
        chart_tag = "Todas las categorias"
        if tag_df.empty:
            st.info("Sin gastos etiquetados en este periodo.")
        else:
            fig_tags = px.pie(
                tag_df,
                values="monto",
                names="etiqueta",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig_tags.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                showlegend=True,
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(fig_tags, use_container_width=True)
            chart_tag = st.selectbox(
                "Ver detalle de etiqueta",
                ["Todas las categorias"] + tag_df["etiqueta"].tolist(),
                key=f"mes_a_mes_chart_tag_{fecha_inicio}_{fecha_fin}",
            )

    effective_tags = [chart_tag] if chart_tag != "Todas las categorias" else selected_tags
    filtered_txns = get_transactions_by_tags(
        effective_tags,
        fecha_inicio,
        end_exclusive,
        tipo_value,
    )

    st.markdown('<div class="section-header">Movimientos por fecha y categoria</div>', unsafe_allow_html=True)
    if chart_tag != "Todas las categorias":
        st.caption(f"Mostrando detalle de la grafica: {chart_tag}")
    elif selected_tags:
        st.caption(f"Categorias seleccionadas: {', '.join(selected_tags)}")

    if filtered_txns.empty:
        st.info("Sin movimientos para estos filtros.")
    else:
        total_ingresos = filtered_txns[filtered_txns["tipo"] == "ingreso"]["monto"].sum()
        total_gastos = filtered_txns[filtered_txns["tipo"] == "gasto"]["monto"].sum()
        balance_filtrado = total_ingresos - total_gastos
        st.markdown(metric_html(
            "Total filtrado",
            format_currency(balance_filtrado),
            "positive" if balance_filtrado >= 0 else "negative",
            f"Ingresos: {format_currency(total_ingresos)} - Gastos: {format_currency(total_gastos)} - {len(filtered_txns)} movimientos",
        ), unsafe_allow_html=True)

        grouped_txns = filtered_txns.copy()
        grouped_txns["fecha_dia"] = grouped_txns["fecha"].dt.date
        for fecha_dia, day_df in grouped_txns.groupby("fecha_dia", sort=False):
            day_ingresos = day_df[day_df["tipo"] == "ingreso"]["monto"].sum()
            day_gastos = day_df[day_df["tipo"] == "gasto"]["monto"].sum()
            st.markdown(f"#### {fecha_dia.strftime('%Y-%m-%d')}")
            st.caption(
                f"Ingresos: {format_currency(day_ingresos)} · Gastos: {format_currency(day_gastos)}"
            )
            table = day_df[["tipo", "descripcion", "monto", "etiquetas"]].copy()
            table["tipo"] = table["tipo"].map({"gasto": "Gasto", "ingreso": "Ingreso"}).fillna(table["tipo"])
            table["monto"] = table["monto"].apply(format_currency)
            table = table.rename(columns={
                "tipo": "Tipo",
                "descripcion": "Descripcion",
                "monto": "Monto",
                "etiquetas": "Categorias",
            })
            st.dataframe(table, use_container_width=True, hide_index=True)


elif pagina == "➕ Registrar movimiento":
    st.title("➕ Registrar movimiento")

    show_movement_feedback()

    form_version = st.session_state.get("movement_form_version", 0)
    tipo = movement_type_selector(f"mov_tipo_{form_version}")

    with st.form(f"form_movimiento_{form_version}"):
        col1, col2 = st.columns(2)
        with col1:
            descripcion = st.text_input("Descripción", key=f"mov_desc_{form_version}")
            monto_input = st.number_input(
                "Monto (MXN)",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key=f"mov_monto_{form_version}",
            )
            fecha_mov = st.date_input("Fecha", value=date.today(), key=f"mov_fecha_{form_version}")
        with col2:
            etiquetas = tag_selector("Etiquetas", key=f"mov_etiquetas_{form_version}")
            notas = st.text_input("Notas adicionales (opcional)", key=f"mov_notas_{form_version}")

        submitted = st.form_submit_button("✅ Guardar movimiento", use_container_width=True)

    if submitted:
        descripcion_limpia = descripcion.strip()
        notas_limpias = notas.strip()
        descripcion_final = descripcion_limpia + (f" — {notas_limpias}" if notas_limpias else "")
        tipo_guardado = "gasto" if tipo == "Gasto" else "ingreso"
        tipo_label = "Gasto" if tipo == "Gasto" else "Ingreso"

        if not descripcion_limpia:
            st.error("Agrega una descripción.")
        elif monto_input <= 0:
            st.error("El monto debe ser mayor a 0.")
        else:
            duplicate = find_duplicate_transaction(tipo_guardado, monto_input, fecha_mov, descripcion_final)

            if duplicate:
                st.warning(
                    f"Posible duplicado: ya existe un {tipo_label.lower()} de "
                    f"{format_currency(monto_input)} con la misma descripción y fecha ({fecha_mov}). "
                    "No lo guardé de nuevo."
                )
            else:
                save_transaction({
                    "fecha": str(fecha_mov),
                    "tipo": tipo_guardado,
                    "monto": monto_input,
                    "descripcion": descripcion_final,
                    "etiquetas": tags_to_text(etiquetas),
                    "recurrente_id": "",
                    "moneda_original": "MXN",
                    "monto_original": monto_input,
                })
                snapshot_savings()
                st.session_state["movement_feedback"] = (
                    f"{tipo_label} registrado: {format_currency(monto_input)} · {descripcion_final}"
                )
                st.session_state["movement_form_version"] = form_version + 1
                st.rerun()

elif pagina == "✏️ Editar movimientos":
    st.title("✏️ Editar movimientos")
    show_movement_feedback()

    today = date.today()
    df_years = load_transactions()
    if df_years.empty:
        movement_years = [today.year]
    else:
        df_years["fecha"] = parse_transaction_dates(df_years["fecha"])
        movement_years = sorted(
            [int(year) for year in df_years["fecha"].dt.year.dropna().unique()],
            reverse=True,
        )
        if today.year not in movement_years:
            movement_years.insert(0, today.year)

    col_year, col_filter = st.columns([1, 2])
    with col_year:
        admin_year = st.selectbox("Año de movimientos", movement_years, key="movement_admin_year")
    with col_filter:
        filtro_tipo = segmented_selector(
            "Filtrar por tipo",
            ["Todos", "Gastos", "Ingresos"],
            "movement_edit_filter",
            "Todos",
        )

    df_admin = load_transactions(admin_year)

    if not df_admin.empty:
        df_admin["fecha"] = parse_transaction_dates(df_admin["fecha"])
        if filtro_tipo == "Gastos":
            df_admin = df_admin[df_admin["tipo"] == "gasto"]
        elif filtro_tipo == "Ingresos":
            df_admin = df_admin[df_admin["tipo"] == "ingreso"]

        df_admin = df_admin.sort_values("fecha", ascending=False)
        st.caption(f"{len(df_admin)} movimiento(s) encontrados para el filtro seleccionado.")

        if df_admin.empty:
            st.info("No hay movimientos con ese filtro en el año seleccionado.")
        else:
            st.markdown('<div class="section-header">Seleccionar movimiento</div>', unsafe_allow_html=True)
            opciones = {
                f"{format_transaction_date(row['fecha'], 'sin fecha')} · "
                f"{row['tipo']} · {format_currency(row['monto'])} · {row['descripcion']} · {str(row['id'])[-6:]}": row["id"]
                for _, row in df_admin.head(100).iterrows()
            }

            sel_edit = st.selectbox("Selecciona movimiento a editar", list(opciones.keys()))
            txn_id = opciones[sel_edit]
            row_edit = df_admin[df_admin["id"] == txn_id].iloc[0]
            fecha_actual = row_edit["fecha"].date() if pd.notna(row_edit["fecha"]) else date.today()
            tags_actuales = str(row_edit.get("etiquetas", "") or "").split("|")

            st.markdown('<div class="section-header">Formulario de edición</div>', unsafe_allow_html=True)
            with st.form(f"form_edit_{txn_id}"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    tipo_edit_label = st.selectbox(
                        "Tipo",
                        ["gasto", "ingreso"],
                        index=0 if row_edit["tipo"] == "gasto" else 1,
                        key=f"edit_tipo_{txn_id}",
                    )
                    fecha_edit = st.date_input("Fecha", value=fecha_actual, key=f"edit_fecha_{txn_id}")
                    monto_edit = st.number_input(
                        "Monto (MXN)",
                        min_value=0.01,
                        value=float(row_edit["monto"]),
                        step=0.01,
                        format="%.2f",
                        key=f"edit_monto_{txn_id}",
                    )
                with col_e2:
                    desc_edit = st.text_input(
                        "Descripción",
                        value=str(row_edit.get("descripcion", "") or ""),
                        key=f"edit_desc_{txn_id}",
                    )
                    tags_edit = tag_selector("Etiquetas", key=f"edit_tags_{txn_id}", default=tags_actuales)

                cambio_anio = fecha_edit.year != admin_year
                if cambio_anio:
                    st.warning("Por ahora la edición está limitada al mismo año del archivo CSV seleccionado.")

                submitted_edit = st.form_submit_button(
                    "💾 Guardar cambios",
                    use_container_width=True,
                    disabled=cambio_anio,
                )

            if submitted_edit:
                if not desc_edit.strip():
                    st.error("La descripción no puede quedar vacía.")
                elif monto_edit <= 0:
                    st.error("El monto debe ser mayor a 0.")
                else:
                    try:
                        updated = update_transaction(txn_id, {
                            "fecha": str(fecha_edit),
                            "tipo": tipo_edit_label,
                            "monto": monto_edit,
                            "descripcion": desc_edit.strip(),
                            "etiquetas": tags_to_text(tags_edit),
                            "moneda_original": "MXN",
                            "monto_original": monto_edit,
                        })
                        if updated:
                            snapshot_savings()
                            st.session_state["movement_feedback"] = (
                                f"Movimiento actualizado: {tipo_edit_label} · "
                                f"{format_currency(monto_edit)} · {desc_edit.strip()}"
                            )
                            st.rerun()
                        else:
                            st.error("No encontré el movimiento para actualizarlo.")
                    except ValueError as exc:
                        st.warning(str(exc))

            st.markdown('<div class="section-header">Eliminar movimiento</div>', unsafe_allow_html=True)
            sel_del = st.selectbox("Selecciona movimiento a eliminar", list(opciones.keys()), key="delete_txn_select")
            if st.button("🗑️ Eliminar", type="secondary"):
                deleted = delete_transaction(opciones[sel_del])
                if deleted:
                    snapshot_savings()
                    st.session_state["movement_feedback"] = "Movimiento eliminado."
                    st.rerun()
                else:
                    st.error("No encontré el movimiento para eliminarlo.")
    else:
        st.info("Sin movimientos registrados para editar o eliminar en este año.")


# ─── RECURRENTES ─────────────────────────────────────────────────────────────

elif pagina == "🔄 Recurrentes":
    st.title("🔄 Gastos recurrentes")

    tab_ver, tab_nuevo = st.tabs(["📋 Activos", "➕ Nuevo recurrente"])

    with tab_ver:
        recurrentes_feedback = st.session_state.get("recurrentes_feedback")
        if recurrentes_feedback:
            if recurrentes_feedback["type"] == "success":
                st.success(recurrentes_feedback["message"])
                st.toast(recurrentes_feedback["message"], icon="🔄")
            else:
                st.info(recurrentes_feedback["message"])
            del st.session_state["recurrentes_feedback"]

        if st.button("🔄 Procesar recurrentes del mes", use_container_width=True):
            procesados = process_due_recurrentes()
            cycle_year, cycle_month = get_current_budget_cycle(date.today())
            cycle_start, cycle_end = get_budget_period(cycle_year, cycle_month)
            programados = process_planned_recurrentes_for_cycle(cycle_start, cycle_end)
            todos_procesados = procesados + programados
            if todos_procesados:
                snapshot_savings()
                st.session_state["recurrentes_feedback"] = {
                    "type": "success",
                    "message": f"Recurrentes agregados o programados: {', '.join(todos_procesados)}",
                }
            else:
                st.session_state["recurrentes_feedback"] = {
                    "type": "info",
                    "message": "No había recurrentes pendientes por procesar este mes.",
                }
            st.rerun()

        df_rec = load_recurrentes()
        activos = df_rec[df_rec["activo"] == True] if not df_rec.empty else pd.DataFrame()
        inactivos = df_rec[df_rec["activo"] == False] if not df_rec.empty else pd.DataFrame()

        if activos.empty:
            st.info("No tienes recurrentes activos.")
        else:
            for _, rec in activos.iterrows():
                with st.expander(f"{'🔁' if rec['tipo_recurrencia'] == 'suscripcion' else '📅'} {rec['nombre']} · {format_currency(float(rec['monto']))} · inicia {rec['fecha_inicio']}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if rec["tipo_recurrencia"] == "mensualidades":
                            pagados = int(rec.get("meses_pagados", 0) or 0)
                            total = int(rec.get("meses_total", 0) or 0)
                            st.markdown(f"**Progreso:** {pagados}/{total} meses")
                            if bool(rec.get("tiene_pago_inicial", False)):
                                monto_inicial = float(rec.get("monto_pago_inicial", 0) or 0)
                                estado_inicial = "registrado" if bool(rec.get("pago_inicial_registrado", False)) else "pendiente"
                                st.markdown(f"**Enganche:** {format_currency(monto_inicial)} · {estado_inicial}")
                            pct = int((pagados / total) * 100) if total > 0 else 0
                            st.markdown(
                                f'<div class="goal-bar-outer"><div class="goal-bar-inner" style="width:{pct}%"></div></div>',
                                unsafe_allow_html=True
                            )
                            restante = (total - pagados) * float(rec["monto"])
                            st.markdown(f"**Restante de mensualidades:** {format_currency(restante)}")
                        else:
                            st.markdown("**Tipo:** Suscripción indefinida 🔁")
                        tags_html = "".join([
                            f'<span class="tag-pill">{t.strip()}</span>'
                            for t in str(rec.get("etiquetas", "") or "").split("|") if t.strip()
                        ])
                        st.markdown(tags_html, unsafe_allow_html=True)
                    with col_b:
                        if st.button(f"❌ Cancelar", key=f"cancel_{rec['id']}"):
                            cancel_recurrente(rec["id"])
                            st.success(f"'{rec['nombre']}' cancelado.")
                            st.rerun()

        if not inactivos.empty:
            with st.expander("📦 Recurrentes cancelados/terminados"):
                for _, rec in inactivos.iterrows():
                    st.markdown(f"~~{rec['nombre']}~~ · {format_currency(float(rec['monto']))} · cancelado")

    with tab_nuevo:
        tipo_rec = st.radio(
            "Tipo",
            ["Suscripción (indefinida)", "Mensualidades (número fijo)"],
            horizontal=True,
            key="tipo_recurrente_nuevo",
        )

        with st.form("form_recurrente"):
            nombre = st.text_input("Nombre del gasto", placeholder="Netflix, Gym, iPhone 12 meses...")
            monto_rec = st.number_input("Monto mensual (MXN)", min_value=0.01, step=0.01, format="%.2f")
            meses = None
            es_mensualidad = tipo_rec == "Mensualidades (número fijo)"
            if es_mensualidad:
                meses = st.number_input("Número de meses", min_value=1, max_value=120, step=1, value=12)
            etiquetas_rec = st.text_input("Etiquetas (separadas por coma)", placeholder="electronica, entretenimiento...")
            fecha_inicio = st.date_input(
                "Fecha de inicio / primer cobro",
                value=date.today(),
                help="Esta fecha se registra como el primer cargo. Los siguientes se crean cada mes en la misma fecha.",
            )
            primera_mensualidad_pagada = False
            fecha_primera_mensualidad = fecha_inicio
            tiene_pago_inicial = False
            monto_pago_inicial = 0.0
            fecha_pago_inicial = fecha_inicio
            descripcion_pago_inicial = ""
            etiquetas_pago_inicial = ""

            if es_mensualidad:
                primera_mensualidad_pagada = st.checkbox(
                    "Ya se pagó la primera mensualidad",
                    help="La registra como mensualidad normal, la cuenta en el progreso y conserva su fecha real.",
                )
                if primera_mensualidad_pagada:
                    fecha_primera_mensualidad = st.date_input(
                        "Fecha del primer pago mensual",
                        value=fecha_inicio,
                    )

                tiene_pago_inicial = st.checkbox("Tiene un pago extra inicial / enganche (no cuenta como mensualidad)")
                if tiene_pago_inicial:
                    monto_pago_inicial = st.number_input(
                        "Monto del pago inicial (MXN)",
                        min_value=0.01,
                        step=0.01,
                        format="%.2f",
                    )
                    fecha_pago_inicial = st.date_input("Fecha del pago inicial", value=fecha_inicio)
                    descripcion_pago_inicial = st.text_input(
                        "Descripción del pago inicial",
                        placeholder="[Enganche] Carro",
                    )
                    etiquetas_pago_inicial = st.text_input(
                        "Etiquetas del pago inicial (separadas por coma)",
                        placeholder="enganche, carro...",
                    )

            submitted_rec = st.form_submit_button("✅ Agregar recurrente", use_container_width=True)

        if submitted_rec:
            if not nombre:
                st.error("Agrega un nombre.")
            elif primera_mensualidad_pagada and fecha_primera_mensualidad > date.today():
                st.error("La fecha de una mensualidad ya pagada no puede estar en el futuro.")
            else:
                etiq = "|".join([e.strip() for e in etiquetas_rec.split(",") if e.strip()])
                etiq_inicial = "|".join([e.strip() for e in etiquetas_pago_inicial.split(",") if e.strip()])
                rec_id = save_recurrente({
                    "nombre": nombre,
                    "monto": monto_rec,
                    "tipo_recurrencia": "suscripcion" if "Suscripción" in tipo_rec else "mensualidades",
                    "meses_total": meses,
                    "meses_pagados": 0,
                    "fecha_inicio": str(fecha_inicio),
                    "activo": True,
                    "etiquetas": etiq,
                    "tiene_pago_inicial": bool(tiene_pago_inicial),
                    "monto_pago_inicial": monto_pago_inicial if tiene_pago_inicial else 0,
                    "fecha_pago_inicial": str(fecha_pago_inicial) if tiene_pago_inicial else "",
                    "pago_inicial_registrado": False,
                    "descripcion_pago_inicial": descripcion_pago_inicial.strip(),
                    "etiquetas_pago_inicial": etiq_inicial,
                })
                primera_mensualidad_registrada = (
                    register_first_installment_for_recurrente(rec_id, fecha_primera_mensualidad)
                    if primera_mensualidad_pagada else False
                )
                pago_inicial_registrado = register_initial_payment_for_recurrente(rec_id)
                mensualidades_registradas = process_due_recurrentes(recurrente_id=rec_id)
                cycle_year, cycle_month = get_current_budget_cycle(date.today())
                cycle_start, cycle_end = get_budget_period(cycle_year, cycle_month)
                mensualidades_programadas = process_planned_recurrentes_for_cycle(
                    cycle_start, cycle_end, recurrente_id=rec_id
                )
                if (
                    primera_mensualidad_registrada or pago_inicial_registrado or
                    mensualidades_registradas or mensualidades_programadas
                ):
                    snapshot_savings()
                    detalles = []
                    if primera_mensualidad_registrada:
                        detalles.append("primera mensualidad")
                    if pago_inicial_registrado:
                        detalles.append("pago inicial")
                    if mensualidades_registradas:
                        detalles.append("mensualidades vencidas")
                    if mensualidades_programadas:
                        detalles.append("cobros del ciclo programados")
                    st.success(f"Recurrente '{nombre}' agregado y {' y '.join(detalles)} registrado ✅")
                else:
                    st.success(f"Recurrente '{nombre}' agregado ✅")
                st.rerun()


# ─── INGRESOS RECURRENTES ─────────────────────────────────────────────────────

elif pagina == "💵 Ingresos recurrentes":
    st.title("💵 Ingresos recurrentes")

    tab_ver, tab_nuevo = st.tabs(["📋 Semanales", "➕ Nuevo ingreso"])

    with tab_ver:
        ingresos_feedback = st.session_state.get("ingresos_recurrentes_feedback")
        if ingresos_feedback:
            if ingresos_feedback["type"] == "success":
                st.success(ingresos_feedback["message"])
                st.toast(ingresos_feedback["message"], icon="💵")
            else:
                st.info(ingresos_feedback["message"])
            del st.session_state["ingresos_recurrentes_feedback"]

        if st.button("💵 Procesar ingresos semanales pendientes", use_container_width=True):
            procesados = process_due_ingresos_recurrentes()
            if procesados:
                snapshot_savings()
                st.session_state["ingresos_recurrentes_feedback"] = {
                    "type": "success",
                    "message": f"Ingresos recurrentes agregados: {', '.join(procesados)}",
                }
            else:
                st.session_state["ingresos_recurrentes_feedback"] = {
                    "type": "info",
                    "message": "No había ingresos semanales pendientes por procesar.",
                }
            st.rerun()

        df_ing = load_ingresos_recurrentes()
        activos = df_ing[df_ing["activo"] == True] if not df_ing.empty else pd.DataFrame()
        inactivos = df_ing[df_ing["activo"] == False] if not df_ing.empty else pd.DataFrame()

        st.markdown('<div class="section-header">Activos</div>', unsafe_allow_html=True)
        if activos.empty:
            st.info("No tienes ingresos recurrentes activos.")
        else:
            for _, ingreso in activos.iterrows():
                dia_nombre = nombre_dia_semana(ingreso.get("dia_semana", 0))
                fecha_inicio_txt = format_transaction_date(ingreso.get("fecha_inicio"))
                fecha_fin_txt = format_transaction_date(ingreso.get("fecha_fin"), "sin fecha fin")
                with st.expander(f"💵 {ingreso['nombre']} · {format_currency(float(ingreso['monto']))} · {dia_nombre}"):
                    col_info, col_edit = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**Día:** {dia_nombre}")
                        st.markdown(f"**Inicio:** {fecha_inicio_txt}")
                        st.markdown(f"**Fin:** {fecha_fin_txt}")
                        tags_html = "".join([
                            f'<span class="tag-pill">{t.strip()}</span>'
                            for t in str(ingreso.get("etiquetas", "") or "").split("|") if t.strip()
                        ])
                        st.markdown(tags_html, unsafe_allow_html=True)
                    with col_edit:
                        with st.form(f"edit_ingreso_rec_{ingreso['id']}"):
                            monto_edit = st.number_input(
                                "Monto semanal",
                                min_value=0.01,
                                value=float(ingreso["monto"]),
                                step=0.01,
                                format="%.2f",
                                key=f"ing_rec_monto_{ingreso['id']}",
                            )
                            dia_edit = st.selectbox(
                                "Día de pago",
                                list(DIAS_SEMANA.keys()),
                                index=list(DIAS_SEMANA.keys()).index(dia_nombre),
                                key=f"ing_rec_dia_{ingreso['id']}",
                            )
                            submitted_ing_edit = st.form_submit_button("💾 Actualizar", use_container_width=True)

                        if submitted_ing_edit:
                            updated = update_ingreso_recurrente(ingreso["id"], {
                                "monto": monto_edit,
                                "dia_semana": DIAS_SEMANA[dia_edit],
                            })
                            if updated:
                                st.success("Ingreso recurrente actualizado.")
                                st.rerun()
                            else:
                                st.error("No encontré el ingreso recurrente para actualizarlo.")

                        if st.button("❌ Desactivar", key=f"cancel_ing_rec_{ingreso['id']}", type="secondary"):
                            cancel_ingreso_recurrente(ingreso["id"])
                            st.success(f"'{ingreso['nombre']}' desactivado.")
                            st.rerun()

        if not inactivos.empty:
            with st.expander("📦 Ingresos recurrentes inactivos"):
                for _, ingreso in inactivos.iterrows():
                    col_i1, col_i2 = st.columns([3, 1])
                    with col_i1:
                        st.markdown(
                            f"~~{ingreso['nombre']}~~ · {format_currency(float(ingreso['monto']))} · "
                            f"{nombre_dia_semana(ingreso.get('dia_semana', 0))}"
                        )
                    with col_i2:
                        if st.button("Reactivar", key=f"reactivar_ing_rec_{ingreso['id']}"):
                            update_ingreso_recurrente(ingreso["id"], {"activo": True})
                            st.rerun()

    with tab_nuevo:
        with st.form("form_ingreso_recurrente"):
            nombre_ing = st.text_input("Nombre / descripción", placeholder="Apoyo semanal, pago freelance, beca...")
            monto_ing = st.number_input("Monto semanal (MXN)", min_value=0.01, step=0.01, format="%.2f")
            dia_ing = st.selectbox("Día de la semana", list(DIAS_SEMANA.keys()), index=4)
            fecha_inicio_ing = st.date_input("Fecha de inicio", value=date.today())
            fecha_fin_ing = st.date_input("Fecha de fin (opcional)", value=None)
            activo_ing = st.checkbox("Activo", value=True)
            etiquetas_ing = tag_selector("Etiquetas", key="ingreso_recurrente_tags")

            submitted_ing = st.form_submit_button("✅ Agregar ingreso recurrente", use_container_width=True)

        if submitted_ing:
            if not nombre_ing.strip():
                st.error("Agrega un nombre o descripción.")
            elif fecha_fin_ing and fecha_fin_ing < fecha_inicio_ing:
                st.error("La fecha de fin no puede ser anterior a la fecha de inicio.")
            else:
                save_ingreso_recurrente({
                    "nombre": nombre_ing.strip(),
                    "monto": monto_ing,
                    "dia_semana": DIAS_SEMANA[dia_ing],
                    "fecha_inicio": str(fecha_inicio_ing),
                    "fecha_fin": str(fecha_fin_ing) if fecha_fin_ing else "",
                    "activo": activo_ing,
                    "etiquetas": tags_to_text(etiquetas_ing),
                })
                st.success(f"Ingreso recurrente '{nombre_ing.strip()}' agregado ✅")
                st.rerun()


# ─── METAS ────────────────────────────────────────────────────────────────────

elif pagina == "🎯 Metas":
    st.title("🎯 Metas de ahorro")

    tab_metas, tab_nueva = st.tabs(["📋 Mis metas", "➕ Nueva meta"])

    with tab_metas:
        df_metas = load_metas()
        ahorro_disponible = get_savings_with_extras()

        st.markdown(
            f'<div class="alert-info">Ahorro real disponible: <strong>{format_currency(ahorro_disponible)}</strong> aprox. {format_currency(mxn_to_usd(ahorro_disponible), "USD")}</div>',
            unsafe_allow_html=True
        )

        if df_metas.empty:
            st.info("No tienes metas registradas.")
        else:
            activas = df_metas[df_metas["completada"] == False]
            completadas = df_metas[df_metas["completada"] == True]

            for _, meta in activas.iterrows():
                objetivo = float(meta["monto_objetivo"])
                actual = float(meta.get("monto_actual", 0) or 0)
                pct = min(int((actual / objetivo) * 100), 100) if objetivo > 0 else 0

                with st.expander(f"🎯 {meta['nombre']} — {pct}% completada"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**Objetivo:** {format_currency(objetivo)}")
                        st.markdown(f"**Acumulado:** {format_currency(actual)} de {format_currency(objetivo)}")
                        st.markdown(f"**Falta:** {format_currency(max(objetivo - actual, 0))}")
                        st.markdown(
                            f'<div class="goal-bar-outer"><div class="goal-bar-inner" style="width:{pct}%"></div></div>',
                            unsafe_allow_html=True
                        )
                        if meta.get("fecha_objetivo"):
                            st.markdown(f"**Fecha objetivo:** {meta['fecha_objetivo']}")
                        if meta.get("descripcion"):
                            st.caption(meta["descripcion"])
                    with col2:
                        nuevo_actual = st.number_input(
                            "Actualizar monto ahorrado",
                            min_value=0.0, value=float(actual), step=100.0,
                            key=f"meta_actual_{meta['id']}"
                        )
                        if st.button("💾 Actualizar", key=f"update_meta_{meta['id']}"):
                            completada = nuevo_actual >= objetivo
                            update_meta(meta["id"], {"monto_actual": nuevo_actual, "completada": completada})
                            if completada:
                                st.balloons()
                                st.success("🎉 ¡Meta completada!")
                            else:
                                st.success("Meta actualizada.")
                            st.rerun()
                        if st.button("🗑️ Eliminar", key=f"del_meta_{meta['id']}", type="secondary"):
                            delete_meta(meta["id"])
                            st.rerun()

            if not completadas.empty:
                with st.expander("✅ Metas completadas"):
                    for _, meta in completadas.iterrows():
                        st.markdown(f"✅ ~~{meta['nombre']}~~ · {format_currency(float(meta['monto_objetivo']))}")

    with tab_nueva:
        with st.form("form_meta"):
            nombre_meta = st.text_input("Nombre de la meta", placeholder="Laptop, Viaje a Japón, Fondo de emergencia...")
            monto_objetivo = st.number_input("Monto objetivo (MXN)", min_value=1.0, step=100.0, format="%.2f")
            monto_inicial = st.number_input("Ya tengo ahorrado (MXN)", min_value=0.0, step=100.0, format="%.2f", value=0.0)
            fecha_obj = st.date_input("Fecha objetivo (opcional)", value=None)
            desc_meta = st.text_input("Descripción (opcional)")
            submitted_meta = st.form_submit_button("✅ Crear meta", use_container_width=True)

        if submitted_meta:
            if not nombre_meta:
                st.error("Agrega un nombre.")
            else:
                save_meta({
                    "nombre": nombre_meta,
                    "monto_objetivo": monto_objetivo,
                    "monto_actual": monto_inicial,
                    "fecha_objetivo": str(fecha_obj) if fecha_obj else "",
                    "completada": monto_inicial >= monto_objetivo,
                    "descripcion": desc_meta,
                })
                st.success(f"Meta '{nombre_meta}' creada ✅")
                st.rerun()


# ─── AHORROS ─────────────────────────────────────────────────────────────────

elif pagina == "💾 Ahorros":
    st.title("💾 Ahorros")

    ahorro_salario = get_cumulative_savings()
    ahorro_real = get_savings_with_extras()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="label">Ahorro (solo salario)</div>'
            f'<div class="value accent">{format_currency(ahorro_salario)}</div>'
            f'<div class="sub">≈ {format_currency(mxn_to_usd(ahorro_salario), "USD")}</div></div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="label">Ahorro real (incluyendo extras)</div>'
            f'<div class="value positive">{format_currency(ahorro_real)}</div>'
            f'<div class="sub">≈ {format_currency(mxn_to_usd(ahorro_real), "USD")}</div></div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.markdown('<div class="section-header">Historial de snapshots (ahorros.csv)</div>', unsafe_allow_html=True)
    df_sav = load_savings()
    if df_sav.empty:
        st.info("Sin snapshots guardados. Usa el botón en el sidebar para guardar uno.")
    else:
        df_sav = df_sav.sort_values("fecha", ascending=False)
        df_sav["ahorro_usd"] = df_sav["ahorro_acumulado"].apply(mxn_to_usd)
        st.dataframe(
            df_sav[["fecha", "ahorro_acumulado", "ahorro_usd", "salario_base"]].rename(columns={
                "fecha": "Fecha",
                "ahorro_acumulado": "Ahorro MXN",
                "ahorro_usd": "Ahorro USD",
                "salario_base": "Salario base",
            }),
            use_container_width=True,
            hide_index=True,
        )

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_sav.sort_values("fecha")["fecha"],
            y=df_sav.sort_values("fecha")["ahorro_acumulado"],
            mode="lines+markers",
            fill="tozeroy",
            fillcolor="rgba(96,165,250,0.15)",
            line=dict(color="#60a5fa", width=2),
            name="Ahorro acumulado",
        ))
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            xaxis=dict(gridcolor="#1e293b"),
            yaxis=dict(gridcolor="#1e293b"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
        )
        st.plotly_chart(fig3, use_container_width=True)


# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────

elif pagina == "⚙️ Configuración":
    st.title("⚙️ Configuración")

    # Salario
    st.markdown('<div class="section-header">Salario base mensual</div>', unsafe_allow_html=True)

    salario_actual = get_current_salary()
    st.markdown(f"**Salario vigente:** {format_currency(salario_actual)}")

    with st.form("form_salario"):
        nuevo_salario = st.number_input(
            "Nuevo salario (MXN)",
            min_value=0.01,
            value=float(salario_actual) if salario_actual > 0 else 1.0,
            step=100.0, format="%.2f"
        )
        fecha_vigencia = st.date_input(
            "Vigente desde (inicio del mes recomendado)",
            value=date.today().replace(day=1)
        )
        submitted_sal = st.form_submit_button("💾 Actualizar salario", use_container_width=True)

    if submitted_sal:
        set_salary(nuevo_salario, fecha_vigencia)
        snapshot_savings()
        st.success(f"Salario actualizado a {format_currency(nuevo_salario)} desde {fecha_vigencia} ✅")
        st.rerun()

    # Historial de salarios
    df_sal = load_salary_history()
    if not df_sal.empty:
        with st.expander("📜 Historial de salarios"):
            st.dataframe(
                df_sal.rename(columns={"fecha_desde": "Vigente desde", "monto": "Salario MXN"}),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    st.markdown('<div class="section-header">Bono / extra del mes</div>', unsafe_allow_html=True)

    with st.form("form_bono_mensual"):
        col_bono1, col_bono2 = st.columns(2)
        with col_bono1:
            desc_bono = st.text_input("Descripción", value="Bono / extra del mes")
            monto_bono = st.number_input(
                "Monto extra (MXN)",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="bono_mensual_monto",
            )
            fecha_bono = st.date_input("Fecha del ingreso", value=date.today(), key="bono_mensual_fecha")
        with col_bono2:
            etiquetas_bono = tag_selector("Etiquetas", key="bono_mensual_tags", default=["bono"])

        submitted_bono = st.form_submit_button("💵 Registrar bono / extra", use_container_width=True)

    if submitted_bono:
        descripcion_bono = desc_bono.strip() or "Bono / extra del mes"
        duplicate = find_duplicate_transaction("ingreso", monto_bono, fecha_bono, descripcion_bono)

        if duplicate:
            st.warning("Ya existe un ingreso igual en esa fecha. No lo guardé de nuevo.")
        else:
            save_transaction({
                "fecha": str(fecha_bono),
                "tipo": "ingreso",
                "monto": monto_bono,
                "descripcion": descripcion_bono,
                "etiquetas": tags_to_text(etiquetas_bono),
                "recurrente_id": "",
                "moneda_original": "MXN",
                "monto_original": monto_bono,
            })
            snapshot_savings()
            st.success(f"Ingreso extra registrado: {format_currency(monto_bono)} · {descripcion_bono} ✅")
            st.rerun()

    st.divider()

    # Info archivos CSV
    st.markdown('<div class="section-header">Archivos de datos</div>', unsafe_allow_html=True)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if os.path.exists(data_dir):
        archivos = os.listdir(data_dir)
        if archivos:
            for f in sorted(archivos):
                path_f = os.path.join(data_dir, f)
                size = os.path.getsize(path_f)
                st.markdown(f"📄 `{f}` — {size / 1024:.1f} KB")
        else:
            st.info("Sin archivos aún.")
    else:
        st.info("El directorio data/ se creará al registrar el primer movimiento.")

    st.divider()
    st.markdown('<div class="section-header">Tipo de cambio</div>', unsafe_allow_html=True)
    rate_info = get_rate_info()
    st.markdown(f"🏦 **{rate_info['label']}** (actualizado a las {rate_info['updated']})")
    st.caption("Fuente: open.er-api.com con fallback a frankfurter.app (BCE europeo). Cache de 1 hora.")

    if st.button("🔄 Forzar actualización del tipo de cambio"):
        st.cache_data.clear()
        st.success("Cache limpiado. El tipo de cambio se actualizará en la próxima consulta.")
        st.rerun()
