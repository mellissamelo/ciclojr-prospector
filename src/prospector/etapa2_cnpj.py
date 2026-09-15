"""Etapa 2 — Identificação de CNPJ e Instagram.

CNPJ: a BrasilAPI só permite consulta por número de CNPJ já conhecido, não por
nome (verificado — não existe endpoint de busca por nome na API oficial).
Por decisão do usuário, a estratégia é: buscar candidatos a CNPJ via Google
Custom Search API (oficial) por "<nome> <endereço> CNPJ Fortaleza" e validar
cada candidato consultando a BrasilAPI por número, comparando o nome
retornado com o nome do estabelecimento. Mesma regra de descarte por
ambiguidade da Etapa 3 se aplica aqui.
"""
from __future__ import annotations

import logging
import re
import time

import requests
from rapidfuzz import fuzz

from prospector.cnpj_utils import extract_cnpj_candidates, format_cnpj
from prospector.google_cse import GoogleCSEClient, QuotaExceeded
from prospector.models import Establishment, ProspectLead

log = logging.getLogger(__name__)

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
BRASILAPI_MIN_INTERVAL_SECONDS = 1.0

ACCEPT_SCORE_THRESHOLD = 65
AMBIGUITY_MARGIN = 12

_INSTAGRAM_URL_RE = re.compile(
    r"instagram\.com/([A-Za-z0-9_.]+)", re.IGNORECASE
)
_INSTAGRAM_RESERVED_PATHS = {
    "p", "reel", "reels", "explore", "accounts", "stories", "tv", "direct", "about",
}

_last_brasilapi_call = 0.0


BRASILAPI_MAX_RETRIES = 3


def _brasilapi_lookup(cnpj_digits: str) -> dict | None:
    """Consulta a BrasilAPI por número de CNPJ. A API aplica rate limit real
    (429, confirmado em teste ao vivo) além do intervalo mínimo entre
    chamadas — em caso de 429, espera com backoff e tenta de novo antes de
    desistir, para não descartar um lead válido por causa de uma janela de
    limite temporária."""
    global _last_brasilapi_call

    backoff = BRASILAPI_MIN_INTERVAL_SECONDS
    for attempt in range(BRASILAPI_MAX_RETRIES):
        elapsed = time.monotonic() - _last_brasilapi_call
        if elapsed < BRASILAPI_MIN_INTERVAL_SECONDS:
            time.sleep(BRASILAPI_MIN_INTERVAL_SECONDS - elapsed)

        try:
            resp = requests.get(BRASILAPI_URL.format(cnpj=cnpj_digits), timeout=15)
        finally:
            _last_brasilapi_call = time.monotonic()

        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            log.warning(
                "BrasilAPI retornou 429 (rate limit) para CNPJ %s, tentativa %d/%d",
                cnpj_digits,
                attempt + 1,
                BRASILAPI_MAX_RETRIES,
            )
            time.sleep(backoff)
            backoff *= 2
            continue
        if resp.status_code != 200:
            log.warning("BrasilAPI retornou %s para CNPJ %s", resp.status_code, cnpj_digits)
            return None
        return resp.json()

    log.warning("BrasilAPI seguiu com 429 após %d tentativas para CNPJ %s, desistindo.", BRASILAPI_MAX_RETRIES, cnpj_digits)
    return None


def _name_score(establishment_name: str, company: dict) -> int:
    candidates = [company.get("razao_social") or "", company.get("nome_fantasia") or ""]
    return max(
        (fuzz.token_set_ratio(establishment_name, c) for c in candidates if c),
        default=0,
    )


def resolve_cnpj(establishment: Establishment, cse: GoogleCSEClient) -> str | None:
    query = f'"{establishment.name}" {establishment.address} CNPJ'
    try:
        results = cse.search(query)
    except QuotaExceeded:
        raise

    text_blob = " ".join(f"{r['title']} {r['snippet']}" for r in results)
    candidates = extract_cnpj_candidates(text_blob)
    if not candidates:
        log.info("Nenhum candidato a CNPJ encontrado para '%s'", establishment.name)
        return None

    scored: list[tuple[str, int]] = []
    for digits in candidates:
        company = _brasilapi_lookup(digits)
        if company is None:
            continue
        score = _name_score(establishment.name, company)
        scored.append((digits, score))

    accepted = [c for c in scored if c[1] >= ACCEPT_SCORE_THRESHOLD]
    if not accepted:
        log.info("Nenhum candidato a CNPJ passou no score mínimo para '%s'", establishment.name)
        return None

    accepted.sort(key=lambda c: c[1], reverse=True)
    if len(accepted) > 1 and (accepted[0][1] - accepted[1][1]) < AMBIGUITY_MARGIN:
        log.info(
            "CNPJ ambíguo para '%s' (%s), descartando lead",
            establishment.name,
            [format_cnpj(c[0]) for c in accepted[:3]],
        )
        return None

    return accepted[0][0]


def _extract_instagram_handle(url: str) -> str | None:
    match = _INSTAGRAM_URL_RE.search(url)
    if not match:
        return None
    handle = match.group(1).strip("/").split("/")[0]
    if not handle or handle.lower() in _INSTAGRAM_RESERVED_PATHS:
        return None
    return handle


def resolve_instagram(establishment: Establishment, cse: GoogleCSEClient) -> str | None:
    try:
        results = cse.search(f"{establishment.name} Fortaleza instagram")
    except QuotaExceeded:
        raise

    for r in results:
        handle = _extract_instagram_handle(r["link"])
        if handle:
            return handle
        handle = _extract_instagram_handle(r["snippet"])
        if handle:
            return handle

    return None


def process_establishment(establishment: Establishment, cse: GoogleCSEClient) -> ProspectLead | None:
    cnpj_digits = resolve_cnpj(establishment, cse)
    if cnpj_digits is None:
        return None

    instagram = resolve_instagram(establishment, cse)

    return ProspectLead(
        name=establishment.name,
        address=establishment.address,
        segment=establishment.segment,
        cnpj=format_cnpj(cnpj_digits),
        instagram=instagram,
        google_place_id=establishment.google_place_id,
    )


def process_establishments(
    establishments: list[Establishment], cse: GoogleCSEClient
) -> list[ProspectLead]:
    leads: list[ProspectLead] = []
    for e in establishments:
        try:
            lead = process_establishment(e, cse)
        except QuotaExceeded:
            log.warning(
                "Cota da Custom Search API esgotada; %d/%d estabelecimentos processados nesta execução.",
                len(leads),
                len(establishments),
            )
            break
        if lead is not None:
            leads.append(lead)
    return leads
