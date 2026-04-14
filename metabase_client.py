import logging
from typing import Dict, List, Optional

import requests

log = logging.getLogger(__name__)

CARD_IDS = {
    "intraday": 36322,
    "trend_mensal_semanal": 36318,
    "trend_diario": 34789,
    "daily_discounts": 36673,
    "pct_desconto_historico": 42479,
}


class MetabaseClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None

    def _authenticate(self):
        resp = requests.post(
            f"{self.base_url}/api/session",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        resp.raise_for_status()
        self.session_token = resp.json()["id"]
        log.info("Metabase: autenticado com sucesso")

    def _headers(self) -> dict:
        if not self.session_token:
            self._authenticate()
        return {"X-Metabase-Session": self.session_token}

    def query_card(self, card_id: int) -> List[dict]:
        """Execute a saved card/question and return rows as list of dicts."""
        for attempt in range(2):
            resp = requests.post(
                f"{self.base_url}/api/card/{card_id}/query/json",
                headers=self._headers(),
                timeout=120,
            )
            if resp.status_code == 401 and attempt == 0:
                log.warning("Metabase: token expirado, re-autenticando...")
                self.session_token = None
                continue
            resp.raise_for_status()
            return resp.json()
        return []

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
