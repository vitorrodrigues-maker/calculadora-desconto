"""
Refresh data for the Calculadora de Desconto.

Pulls data from 5 Metabase cards and builds data/current_state.json.
New cards return discount PERCENTAGES (not absolute values), so we
reconstruct absolute values using GMV from the trend cards.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

BRT = timezone(timedelta(hours=-3))

from dotenv import load_dotenv

from paths import data_file, data_dir, env_file

load_dotenv(env_file())

log = logging.getLogger(__name__)

DATA_PATH = data_file()

PCT_FIELD_MAP = {
    "%total": "vlr_total",
    "%tag_verde": "vlr_tag_verde",
    "%abre_portas": "vlr_abre_portas",
    "%exclusivo": "vlr_exclusivo",
    "%comercial sups": "vlr_comercial_sups",
    "%adf": "vlr_adf",
    "%ops_realocados": "vlr_ops_realocados",
    "%ops_outros": "vlr_ops_outros",
    "%cupom app": "vlr_cupom_app",
    "%cupom prover": "vlr_cupom_prover",
    "%cupom pap": "vlr_cupom_pap",
    "%cupom ops": "vlr_cupom_ops",
    "%hcd": "vlr_hcd",
    "% comercial vendedores": "vlr_comercial_vendedores",
    "% comissao": "pct_comissao",
}


def _num(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _find_today_row(daily_rows: List[dict]) -> Optional[dict]:
    """Find today's row in the daily percentage card."""
    today = datetime.now(BRT).strftime("%Y-%m-%d")
    for r in daily_rows:
        date_str = str(r.get("order_date_2", ""))[:10]
        if date_str == today:
            return r
    if daily_rows:
        daily_rows_sorted = sorted(daily_rows, key=lambda r: str(r.get("order_date_2", "")))
        return daily_rows_sorted[-1]
    return None


def _find_current_month_row(monthly_rows: List[dict]) -> Optional[dict]:
    """Find the current month's row in the monthly percentage card."""
    now = datetime.now(BRT)
    target = f"{now.year}-{now.month:02d}"
    for r in monthly_rows:
        date_str = str(r.get("order_date_2", ""))[:7]
        if date_str == target:
            return r
    if monthly_rows:
        monthly_sorted = sorted(monthly_rows, key=lambda r: str(r.get("order_date_2", "")))
        return monthly_sorted[-1]
    return None


def _pct_row_to_absolute(pct_row: dict, gmv: float, date_str: str) -> dict:
    """Convert a percentage row + GMV into absolute values matching frontend format."""
    row = {"order_date_2": date_str, "gmv_fp": gmv}

    for pct_col, abs_col in PCT_FIELD_MAP.items():
        pct_val = _num(pct_row.get(pct_col))
        if abs_col == "pct_comissao":
            row["pct_comissao"] = pct_val
            row["valor_comissao_dia"] = gmv * pct_val
            row["gmv_comissionado_dia"] = gmv
        else:
            row[abs_col] = gmv * pct_val

    return row


def build_daily_discounts(
    daily_pct_rows: List[dict],
    monthly_pct_rows: List[dict],
    today_gmv: float,
    mtd_gmv: float,
) -> List[dict]:
    """Build daily_discounts array compatible with the frontend.

    Creates two synthetic rows:
    1. "rest of month" (month totals minus today) - so aggregateMonth() works
    2. today's row with absolute values
    """
    today_pct = _find_today_row(daily_pct_rows)
    month_pct = _find_current_month_row(monthly_pct_rows)

    if not today_pct:
        log.warning("Nenhuma linha para hoje encontrada no card de desconto diario")
        return []

    now = datetime.now(BRT)
    today_str = now.strftime("%Y-%m-%d") + "T00:00:00"
    rest_str = now.strftime("%Y-%m-01") + "T00:00:00"

    today_row = _pct_row_to_absolute(today_pct, today_gmv, today_str)

    rows = []

    if month_pct and mtd_gmv > today_gmv:
        rest_gmv = mtd_gmv - today_gmv
        month_row = _pct_row_to_absolute(month_pct, mtd_gmv, rest_str)

        rest_row = {"order_date_2": rest_str, "gmv_fp": rest_gmv}
        for key in today_row:
            if key in ("order_date_2", "gmv_fp", "gmv_comissionado_dia"):
                continue
            if key == "gmv_comissionado_dia":
                rest_row["gmv_comissionado_dia"] = rest_gmv
            elif key == "pct_comissao":
                rest_row["pct_comissao"] = _num(month_pct.get("% comissao"))
            else:
                month_val = _num(month_row.get(key))
                today_val = _num(today_row.get(key))
                rest_row[key] = max(month_val - today_val, 0)
        rest_row["gmv_comissionado_dia"] = rest_gmv
        rows.append(rest_row)

    rows.append(today_row)
    return rows


def transform_gmv_trend(
    trend_mensal_semanal: List[dict],
    trend_diario: List[dict],
    intraday_rows: List[dict],
) -> dict:
    """Combine trend cards into gmv_trend dict for the frontend."""
    ms = trend_mensal_semanal[0] if trend_mensal_semanal else {}
    dia = trend_diario[0] if trend_diario else {}

    realizado_mtd = _num(ms.get("realizado_mtd"))
    trend_mensal = _num(ms.get("trend_mensal"))
    realizado_hoje = _num(dia.get("gmv_prover_hoje_ate_agora"))
    realizado_horas_fechadas = _num(dia.get("gmv_prover_hoje_horas_fechadas"))
    trend_fechamento_dia = _num(dia.get("trend_prover_fechamento_dia"))

    pct_dia_decorrido = 0.0
    if trend_fechamento_dia > 0:
        pct_dia_decorrido = realizado_horas_fechadas / trend_fechamento_dia

    hora_atual = None
    intraday = []
    for r in intraday_rows:
        hora = int(_num(r.get("hora", 0)))
        if hora_atual is None:
            hora_atual = int(_num(r.get("hora_atual_sp", 0)))
        intraday.append({
            "hora": hora,
            "realizado": _num(r.get("gmv_realizado_hora")),
            "realizado_acum": _num(r.get("gmv_realizado_acumulado")),
            "media": _num(r.get("media_gmv_hora")),
            "media_acum": _num(r.get("media_gmv_acumulado")),
        })

    return {
        "meta_mensal": _num(ms.get("meta_mensal")),
        "realizado_mtd": realizado_mtd,
        "realizado_hoje": realizado_hoje,
        "atingimento_mensal": _num(ms.get("atingimento_mensal")),
        "trend_mensal": trend_mensal,
        "trend_meta_mensal": _num(ms.get("trend_meta_mensal")),
        "meta_semana": _num(ms.get("meta_semana")),
        "realizado_semana": _num(ms.get("realizado_semana")),
        "atingimento_semana": _num(ms.get("atingimento_semana")),
        "trend_semana": _num(ms.get("trend_semana")),
        "trend_meta_semana": _num(ms.get("trend_meta_semana")),
        "total_pesos_mes": trend_mensal,
        "pesos_passados": realizado_mtd,
        "total_pesos_semana": _num(ms.get("trend_semana")),
        "pesos_semana_passados": _num(ms.get("realizado_semana")),
        "peso_hoje": 0,
        "total_pesos_restantes": 0,
        "meta_prover_dia": _num(dia.get("meta_prover_dia")),
        "percentual_dia_decorrido": pct_dia_decorrido,
        "realizado_horas_fechadas": realizado_horas_fechadas,
        "trend_fechamento_dia": trend_fechamento_dia,
        "hora_atual_sp": hora_atual or 0,
        "intraday": intraday,
    }


def build_state(daily_discounts, gmv_trend):
    return {
        "updated_at": datetime.now(BRT).isoformat(),
        "daily_discounts": daily_discounts,
        "gmv_trend": gmv_trend if isinstance(gmv_trend, dict) else gmv_trend[0],
    }


def save_state(state):
    os.makedirs(data_dir(), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    log.info(
        "Dados salvos em %s  (%d dias, meta R$ %s)",
        DATA_PATH,
        len(state["daily_discounts"]),
        f"{state['gmv_trend'].get('meta_mensal', 0):,.0f}",
    )


def refresh_from_metabase() -> Optional[dict]:
    """Pull all cards from Metabase, transform, save, and return the state."""
    from metabase_client import MetabaseClient

    url = os.getenv("METABASE_URL", "")
    api_key = os.getenv("METABASE_API_KEY", "")

    if not all([url, api_key]):
        log.error("METABASE_URL ou METABASE_API_KEY ausente no .env")
        return None

    client = MetabaseClient(url, api_key)
    cards = client.query_all_cards()

    trend = transform_gmv_trend(
        cards.get("trend_mensal_semanal", []),
        cards.get("trend_diario", []),
        cards.get("intraday", []),
    )

    today_gmv = trend.get("realizado_hoje", 0)
    mtd_gmv = trend.get("realizado_mtd", 0)

    daily = build_daily_discounts(
        cards.get("daily_discounts", []),
        cards.get("pct_desconto_historico", []),
        today_gmv,
        mtd_gmv,
    )

    if not daily:
        log.warning("Nenhum dado de desconto retornado — mantendo dados anteriores")
        return None

    state = build_state(daily, trend)
    save_state(state)
    return state


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if "--manual" in sys.argv:
        print("Cole o JSON dos descontos diários e pressione Enter + Ctrl-D:")
        daily_raw = sys.stdin.read()
        daily = json.loads(daily_raw)

        print("Cole o JSON do trend GMV e pressione Enter + Ctrl-D:")
        trend_raw = input()
        trend = json.loads(trend_raw)

        state = build_state(daily, trend)
        save_state(state)
    else:
        result = refresh_from_metabase()
        if result:
            print(f"OK — {len(result['daily_discounts'])} dias atualizados")
        else:
            print("Falha ao atualizar. Verifique os logs.")
