"""Etapa 1 — Prospecção via Google Places API (New), Text Search.

Usa apenas campos do tier Pro (nome, endereço, tipo). Telefone foi removido do
escopo por decisão do usuário: não aparece em nenhum output final e exigiria o
tier Enterprise (bem mais caro, cota gratuita menor).
"""
from __future__ import annotations

import logging
import time

import requests

from prospector.models import Establishment

log = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Campos do tier Pro. Ver: https://developers.google.com/maps/documentation/places/web-service/data-fields
# websiteUri e nationalPhoneNumber são Enterprise (mais caro, cota grátis
# menor) e foram deixados de fora de propósito — nenhum dos dois é usado no
# output final nem é necessário para achar CNPJ/Instagram (isso é feito via
# Custom Search na Etapa 2).
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.types",
        "nextPageToken",
    ]
)

MAX_PAGES = 3  # até 60 resultados (20 por página)
PAGE_DELAY_SECONDS = 2.0


def search_establishments(segment: str, api_key: str, city: str = "Fortaleza, CE") -> list[Establishment]:
    query = f"{segment} em {city}"
    results: list[Establishment] = []
    page_token: str | None = None

    for page in range(MAX_PAGES):
        body: dict = {"textQuery": query, "languageCode": "pt-BR"}
        if page_token:
            body["pageToken"] = page_token

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }

        resp = requests.post(SEARCH_URL, json=body, headers=headers, timeout=30)
        if resp.status_code != 200:
            log.error("Google Places retornou %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()
        places = data.get("places", [])
        log.info("Página %d: %d estabelecimentos ('%s')", page + 1, len(places), query)

        for place in places:
            results.append(
                Establishment(
                    name=place.get("displayName", {}).get("text", "").strip(),
                    address=place.get("formattedAddress", "").strip(),
                    google_place_id=place.get("id", ""),
                    segment=segment,
                )
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        # o Google exige um pequeno intervalo para o pageToken ficar válido
        time.sleep(PAGE_DELAY_SECONDS)

    # dedup por place_id (a Text Search pode repetir resultados entre páginas)
    seen: set[str] = set()
    deduped: list[Establishment] = []
    for e in results:
        if e.google_place_id and e.google_place_id not in seen:
            seen.add(e.google_place_id)
            deduped.append(e)

    return deduped
