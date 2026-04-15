import logging
from typing import Dict, List

import requests

log = logging.getLogger(__name__)

CARD_IDS = {
    "daily_discounts": 50332,
    "pct_desconto_historico": 50334,
    "trend_diario": 50336,
    "trend_mensal_semanal": 50335,
    "intraday": 50333,
}


class MetabaseClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def query_card(self, card_id: int) -> List[dict]:
        """Execute a saved card/question and return rows as list of dicts."""
        resp = requests.post(
            f"{self.base_url}/api/card/{card_id}/query",
            headers=self._headers(),
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()

        cols = [c["name"] for c in payload["data"]["cols"]]
        return [dict(zip(cols, row)) for row in payload["data"]["rows"]]

    def query_all_cards(self) -> Dict[str, List[dict]]:
        """Query all configured cards and return {name: rows}."""
        results = {}
        for name, card_id in CARD_IDS.items():
            try:
                results[name] = self.query_card(card_id)
                log.info("Metabase: card %s (%d) -> %d rows", name, card_id, len(results[name]))
            except Exception:
                log.exception("Metabase: falha ao consultar card %s (%d)", name, card_id)
                results[name] = []
        return results
