"""
currency.py
Tipo de cambio MXN/USD interbancario en tiempo real.
Usa exchangerate-api (free tier, 1500 req/mes) con fallback a Fixer.
"""

import requests
import streamlit as st
from datetime import datetime

CACHE_TTL = 3600  # 1 hora


@st.cache_data(ttl=CACHE_TTL)
def get_usd_mxn_rate() -> float:
    """
    Obtiene el tipo de cambio USD → MXN.
    Retorna cuántos pesos vale 1 dólar.
    """
    try:
        # exchangerate-api free endpoint (no key required para open access)
        r = requests.get(
            "https://open.er-api.com/v6/latest/USD",
            timeout=5
        )
        data = r.json()
        if data.get("result") == "success":
            rate = data["rates"]["MXN"]
            return float(rate)
    except Exception:
        pass

    try:
        # Fallback: frankfurter.app (BCE europeo, sin key)
        r = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=MXN",
            timeout=5
        )
        data = r.json()
        return float(data["rates"]["MXN"])
    except Exception:
        pass

    # Fallback hardcodeado si todo falla
    return 17.5


def mxn_to_usd(monto_mxn: float) -> float:
    rate = get_usd_mxn_rate()
    return monto_mxn / rate


def usd_to_mxn(monto_usd: float) -> float:
    rate = get_usd_mxn_rate()
    return monto_usd * rate


def format_currency(monto: float, moneda: str = "MXN", show_both: bool = False) -> str:
    if moneda == "MXN":
        base = f"${monto:,.2f} MXN"
        if show_both:
            usd = mxn_to_usd(monto)
            base += f"  ≈  ${usd:,.2f} USD"
        return base
    else:
        base = f"${monto:,.2f} USD"
        if show_both:
            mxn = usd_to_mxn(monto)
            base += f"  ≈  ${mxn:,.2f} MXN"
        return base


def get_rate_info() -> dict:
    rate = get_usd_mxn_rate()
    return {
        "rate": rate,
        "label": f"1 USD = ${rate:.4f} MXN",
        "updated": datetime.now().strftime("%H:%M"),
    }