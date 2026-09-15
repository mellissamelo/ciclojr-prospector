"""Orquestra a geração de leads para um segmento (e opcionalmente um bairro),
sob demanda — pode ser rodado quantas vezes o usuário quiser, sem teto de
quantidade (decisão do usuário: só ele decide quando parar, pelo botão
"Parar" — ver `should_stop`).

Etapas 1+2 do desenho original (Google Maps + busca de CNPJ) foram
substituídas por um extrato local da Receita Federal — ver rf_source.py para
o porquê. O que resta em pipeline é: carregar prospects (nome+CNPJ prontos),
pular CNPJs já checados recentemente (cache — a maioria dos CNPJs não está no
SEUMA, então reconsultar toda vez desperdiça tempo, e evita reprocessar o
mesmo lead em execuções repetidas), checar licenças no SEUMA, aplicar dedup e
atualizar o painel.
"""
from __future__ import annotations

import logging
import random
from datetime import date, datetime
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from prospector import config, db, etapa3_seuma, instagram_lookup, rf_source
from prospector.models import QualifiedLead

log = logging.getLogger(__name__)

RECHECK_AFTER_DAYS = 30  # não reconsulta um CNPJ (achado ou não) antes disso


def run_daily(
    segment: str,
    bairro: str | None = None,
    should_stop: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int, int], None] | None = None,
) -> None:
    """should_stop: checado entre um lead e outro — se retornar True, para a
    execução no lead atual (usado pelo botão "Parar" do app).
    on_progress(checados, total, entregues): chamado depois de cada CNPJ
    processado — usado pelo painel pra mostrar o progresso ao vivo."""
    settings = config.load_settings()
    segments = config.load_segments()
    license_names = config.load_license_names()
    rf_sources = config.load_rf_sources()

    if segment not in segments:
        raise ValueError(f"Segmento desconhecido: {segment!r}. Válidos: {list(segments)}")
    if segment not in rf_sources:
        raise ValueError(
            f"Sem extrato da Receita Federal configurado para '{segment}' "
            f"(config/rf_sources.yaml). Válidos: {list(rf_sources)}"
        )

    seg_config = segments[segment]
    required_siglas = {s: True for s in seg_config["forte_demanda"]}
    required_siglas.update({s: False for s in seg_config["condicional"]})

    db.init_db(settings.db_path)
    today = date.today()
    # identifica ESTA execução (não o dia): rodar de novo, mesmo no mesmo
    # dia, cria um run_id novo e os leads de agora passam a ser "a
    # execução mais recente" no painel — os de antes viram histórico.
    run_id = datetime.now().isoformat(timespec="seconds")

    log.info("Carregando prospects de '%s' a partir do extrato local da Receita Federal...", segment)
    csv_path = config.ROOT_DIR / rf_sources[segment]["csv"]
    prospects = rf_source.load_prospects(csv_path, segment, bairro=bairro)
    random.shuffle(prospects)  # evita sempre bater nos mesmos primeiros CNPJs do extrato

    with db.connect(settings.db_path) as conn:
        already_checked = db.get_recently_checked_cnpjs(conn, segment, RECHECK_AFTER_DAYS)

    pending = [p for p in prospects if p.cnpj not in already_checked]
    log.info(
        "%d prospects carregados, %d já checados nos últimos %d dias (pulando), %d a checar.",
        len(prospects),
        len(prospects) - len(pending),
        RECHECK_AFTER_DAYS,
        len(pending),
    )

    log.info("Verificando licenças no Portal SEUMA...")
    playwright, browser, page = etapa3_seuma.open_browser(headless=settings.seuma_headless)
    ig_page = instagram_lookup.open_search_page(browser)
    delivered = 0
    checked_count = 0
    try:
        for attempt in range(2):
            try:
                etapa3_seuma.goto_portal(page)
                break
            except PlaywrightTimeoutError:
                if attempt == 1:
                    raise
                log.warning("Portal SEUMA demorou pra carregar, tentando de novo...")

        for prospect in pending:
            if should_stop and should_stop():
                log.info("Interrompido pelo usuário.")
                break

            statuses = etapa3_seuma.check_lead_licenses(
                page, prospect, required_siglas, license_names, settings.seuma_request_delay_seconds
            )
            checked_count += 1

            with db.connect(settings.db_path) as conn:
                if statuses is None:
                    db.record_check(conn, prospect.cnpj, segment, "descartado", today, prospect.bairro)
                else:
                    lead = QualifiedLead(
                        name=prospect.name,
                        cnpj=prospect.cnpj,
                        instagram=prospect.instagram,
                        segment=prospect.segment,
                        bairro=prospect.bairro,
                        owner_name=prospect.owner_name,
                        licenses=statuses,
                    )
                    if not lead.is_qualified:
                        db.record_check(conn, prospect.cnpj, segment, "nao_qualificado", today, prospect.bairro)
                    else:
                        db.record_check(conn, prospect.cnpj, segment, "qualificado", today, prospect.bairro)
                        if db.should_deliver(conn, lead):
                            lead.instagram = instagram_lookup.find_instagram(ig_page, browser, lead.name, lead.bairro)
                            db.record_delivery(conn, lead, run_id, today)
                            delivered += 1
                            log.info("Lead qualificado e entregue: %s (%s)", lead.name, lead.cnpj)

            if on_progress:
                on_progress(checked_count, len(pending), delivered)
    finally:
        instagram_lookup.close_search_page(ig_page)
        etapa3_seuma.close_browser(playwright, browser)

    log.info(
        "Concluído: %d CNPJs checados, %d leads novos/atualizados entregues.",
        checked_count,
        delivered,
    )
