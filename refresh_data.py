"""
Refresh data for the Calculadora de Desconto.

Pulls data from 5 Metabase cards and builds data/current_state.json.
Can also be run standalone:
  python3 refresh_data.py            # uses .env credentials
  python3 refresh_data.py --manual   # paste JSON manually
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

from paths import data_file, data_dir, env_file

load_dotenv(env_file())

log = logging.getLogger(__name__)

DATA_PATH = data_file()

DISCOUNT_FIELD_MAP = {
    "order_date_2": "order_date_2",
    "gmv fp": "gmv_fp",
    "desconto total": "vlr_total",
    "tag verde": "vlr_tag_verde",
    "abre portas": "vlr_abre_portas",
    "exclusivo": "vlr_exclusivo",
    "comercial sups": "vlr_comercial_sups",
    "adf": "vlr_adf",
    "ops realocados": "vlr_ops_realocados",
    "ops outros": "vlr_ops_outros",
    "cupom app": "vlr_cupom_app",
    "cupom prover": "vlr_cupom_prover",
    "cupom pap": "vlr_cupom_pap",
    "cupom ops": "vlr_cupom_ops",
    "hcd": "vlr_hcd",
    "comercial vendedores": "vlr_comercial_vendedores",
    "comissao": "valor_comissao_dia",
}


def _num(v):
    """Safely coerce to float, treating None/null as 0."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def transform_daily_discounts(raw_rows: List[dict]) -> List[dict]:
    """Card 36673 -> daily_discounts in the format the frontend expects."""
    now = datetime.now()
    current_month = (now.year, now.month)

    rows = []
    for raw in raw_rows:
        date_str = str(raw.get("order_date_2", ""))[:10]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if (dt.year, dt.month) != current_month:
            continue

        row = {}
        for src_key, dst_key in DISCOUNT_FIELD_MAP.items():
            val = raw.get(src_key)
            row[dst_key] = val if dst_key == "order_date_2" else _num(val)

        if not date_str.endswith("T00:00:00"):
            row["order_date_2"] = date_str + "T00:00:00"

        gmv = row.get("gmv_fp") or 1
        comissao = row.get("valor_comissao_dia", 0)
        row["gmv_comissionado_dia"] = gmv
        row["pct_comissao"] = comissao / gmv if gmv else 0

        rows.append(row)

    rows.sort(key=lambda r: r["order_date_2"])
    return rows


def transform_gmv_trend(
    trend_mensal_semanal: List[dict],
    trend_diario: List[dict],
    intraday_rows: List[dict],
) -> dict:
    """Combine cards 36318 + 34789 + 36322 -> gmv_trend dict."""
    ms = trend_mensal_semanal[0] if trend_mensal_semanal else {}
    dia = trend_diario[0] if trend_diario else {}

    realizado_mtd = _num(ms.get("realizado_mtd"))
    trend_mensal = _num(ms.get("trend_mensal"))
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
            "realizado_acum": _num(r.get("gmv_realizado_acumulado (R$)")),
            "media": _num(r.get("media_gmv_hora")),
            "media_acum": _num(r.get("media_gmv_acumulado (R$)")),
        })

    result = {
        "meta_mensal": _num(ms.get("meta_mensal")),
        "realizado_mtd": realizado_mtd,
        "realizado_hoje": _num(dia.get("gmv_prover_hoje_ate_agora")),
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
    return result


def build_state(daily_discounts, gmv_trend):
    return {
        "updated_at": datetime.now().isoformat(),
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
    user = os.getenv("METABASE_USER", "")
    pwd = os.getenv("METABASE_PASSWORD", "")

    if not all([url, user, pwd]):
        log.error("Metabase credentials missing in .env")
        return None

    client = MetabaseClient(url, user, pwd)
    cards = client.query_all_cards()

    daily = transform_daily_discounts(cards.get("daily_discounts", []))
    trend = transform_gmv_trend(
        cards.get("trend_mensal_semanal", []),
        cards.get("trend_diario", []),
        cards.get("intraday", []),
    )

    if not daily:
        log.warning("Nenhum dado de desconto diario retornado — mantendo dados anteriores")
        return None

    state = build_state(daily, trend)
    save_state(state)
    return state


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if "--manual" in sys.argv:
        print("Cole o JSON dos descontos diários (Query A) e pressione Enter + Ctrl-D:")
        daily_raw = sys.stdin.read()
        daily = json.loads(daily_raw)

        print("Cole o JSON do trend GMV (Query B) e pressione Enter + Ctrl-D:")
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
