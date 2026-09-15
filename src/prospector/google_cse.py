"""Wrapper fino sobre a Google Custom Search JSON API (oficial).

Cota gratuita: 100 buscas/dia por padrão. Acima disso a API responde 429 e o
cliente para de tentar pelo resto da execução (fica para o próximo dia).
"""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class QuotaExceeded(Exception):
    pass


class GoogleCSEClient:
    def __init__(self, api_key: str, cx: str, min_interval_seconds: float = 1.0):
        self.api_key = api_key
        self.cx = cx
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0
        self._quota_exhausted = False

    def search(self, query: str, num: int = 10) -> list[dict]:
        """Retorna lista de {title, snippet, link}. Lista vazia se nada encontrado."""
        if self._quota_exhausted:
            return []

        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)

        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num, 10),
        }
        resp = requests.get(SEARCH_URL, params=params, timeout=20)
        self._last_call = time.monotonic()

        if resp.status_code == 429:
            log.warning("Cota diária da Google Custom Search API esgotada.")
            self._quota_exhausted = True
            raise QuotaExceeded("Cota diária da Custom Search API esgotada")

        if resp.status_code != 200:
            log.error("Google CSE retornou %s para '%s': %s", resp.status_code, query, resp.text)
            return []

        data = resp.json()
        items = data.get("items", [])
        return [
            {
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
            }
            for item in items
        ]

    @property
    def quota_exhausted(self) -> bool:
        return self._quota_exhausted
