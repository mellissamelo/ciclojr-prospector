"""Fonte primária de leads: extrato local dos Dados Abertos do CNPJ da Receita
Federal (via basedosdados.org / BigQuery), filtrado por Fortaleza-CE e CNAE do
segmento.

Substitui o par "Google Maps (Etapa 1) + busca de CNPJ via Custom Search
(Etapa 2)" do desenho original. Motivo: a Google Custom Search JSON API foi
fechada para clientes novos em 2026 (confirmado — "This project does not have
the access to Custom Search JSON API", erro que ocorre mesmo com a API
ativada e faturamento em dia), então não há como buscar CNPJ por nome nem
achar Instagram via essa API. A base da Receita já traz nome + CNPJ +
endereço direto da fonte oficial, então nem precisa mais adivinhar.

Instagram: sem provedor de busca gratuito disponível no momento, fica sempre
em branco (`instagram=None`). Isso é aceito pelo desenho original ("não
impede a qualificação do lead") — se surgir uma alternativa viável, plugar
aqui depois.

Como atualizar/adicionar segmentos: ver README.md, seção "Atualizando a base
da Receita Federal local".
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from prospector.cnpj_utils import format_cnpj, is_valid_cnpj, normalize
from prospector.models import ProspectLead

log = logging.getLogger(__name__)


def list_bairros(csv_path: Path) -> list[str]:
    """Bairros distintos presentes no extrato, ou [] se o arquivo não existir
    ou não tiver coluna `bairro` (segmentos extraídos só com cnpj+socio_nome)."""
    if not csv_path.exists():
        return []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "bairro" not in (reader.fieldnames or []):
            return []
        bairros = {(row.get("bairro") or "").strip() for row in reader}
    bairros.discard("")
    return sorted(bairros)


def load_prospects(csv_path: Path, segment: str, bairro: str | None = None) -> list[ProspectLead]:
    """bairro: filtro opcional (case-insensitive, exato) pelo campo `bairro`
    do extrato da Receita — ex.: "MEIRELES", "ALDEOTA"."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Extrato da Receita Federal não encontrado para o segmento '{segment}': {csv_path}\n"
            f"Rode a extração no BigQuery (ver README) e salve o CSV nesse caminho."
        )

    bairro_norm = bairro.strip().upper() if bairro else None

    prospects: list[ProspectLead] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if bairro_norm and "bairro" not in (reader.fieldnames or []):
            raise ValueError(
                f"Segmento '{segment}' não tem coluna 'bairro' no extrato ({csv_path.name}) "
                f"— filtro por bairro não é suportado para esse segmento."
            )
        for row in reader:
            if bairro_norm and (row.get("bairro") or "").strip().upper() != bairro_norm:
                continue

            cnpj_digits = normalize(row["cnpj"])
            if not is_valid_cnpj(cnpj_digits):
                log.warning("CNPJ inválido no extrato, pulando: %r", row.get("cnpj"))
                continue

            nome = (row.get("nome_fantasia") or "").strip() or (row.get("razao_social") or "").strip()
            endereco_partes = [
                row.get("logradouro", "").strip(),
                row.get("numero", "").strip(),
                row.get("bairro", "").strip(),
            ]
            address = ", ".join(p for p in endereco_partes if p)

            prospects.append(
                ProspectLead(
                    name=nome,
                    address=address,
                    segment=segment,
                    cnpj=format_cnpj(cnpj_digits),
                    instagram=None,
                    google_place_id="",
                    bairro=(row.get("bairro") or "").strip(),
                    owner_name=(row.get("socio_nome") or "").strip(),
                )
            )

    log.info(
        "Carregados %d estabelecimentos do extrato da Receita para '%s'%s",
        len(prospects),
        segment,
        f" (bairro: {bairro})" if bairro else "",
    )
    return prospects
