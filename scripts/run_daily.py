#!/usr/bin/env python
"""Ponto de entrada da execução (sob demanda — quantas vezes por semana quiser).

Uso:
    python scripts/run_daily.py "Restaurantes"                    # segmento
    python scripts/run_daily.py "Restaurantes" --bairro Aldeota   # + bairro
    python scripts/run_daily.py                                    # rotação automática

Sem argumento, escolhe um segmento por rotação (dia do ano % número de
segmentos) — só usado no agendamento automático. Rodando manualmente
(rodar_hoje.bat), prefira sempre passar o segmento e, se quiser, o bairro.

Teto de leads é SEMANAL (50/semana, não por execução) e não repete CNPJ já
entregue — pode rodar várias vezes na mesma semana sem duplicar trabalho: o
sistema pula CNPJs checados nos últimos 30 dias automaticamente.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prospector import config, pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "segment", nargs="?", default=None, help="Segmento a prospectar (ver config/segments.yaml)"
    )
    parser.add_argument("--bairro", default=None, help="Filtra por bairro de Fortaleza (opcional)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    valid_segments = config.segment_names()

    segment = args.segment
    if segment is None:
        segment = valid_segments[date.today().timetuple().tm_yday % len(valid_segments)]
        logging.info("Nenhum segmento informado; rotação escolheu: %s", segment)

    if segment not in valid_segments:
        print(f"Segmento inválido: {segment!r}", file=sys.stderr)
        print(f"Válidos: {valid_segments}", file=sys.stderr)
        sys.exit(1)

    pipeline.run_daily(segment, bairro=args.bairro)


if __name__ == "__main__":
    main()
