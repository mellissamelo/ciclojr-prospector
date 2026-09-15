from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"

load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    # Não exigidas mais pelo pipeline padrão (a fonte de leads é o extrato
    # local da Receita Federal, ver rf_source.py) — ficam disponíveis só
    # para quem quiser reativar os módulos etapa1_maps.py/etapa2_cnpj.py.
    google_maps_api_key: str
    google_cse_api_key: str
    google_cse_id: str
    db_path: Path
    frontend_dist_dir: Path
    seuma_request_delay_seconds: float
    seuma_headless: bool


def load_settings() -> Settings:
    def _optional(name: str) -> str:
        return os.environ.get(name, "").strip()

    return Settings(
        google_maps_api_key=_optional("GOOGLE_MAPS_API_KEY"),
        google_cse_api_key=_optional("GOOGLE_CSE_API_KEY"),
        google_cse_id=_optional("GOOGLE_CSE_ID"),
        db_path=ROOT_DIR / os.environ.get("DB_PATH", "data/leads.db"),
        frontend_dist_dir=ROOT_DIR / os.environ.get("FRONTEND_DIST_DIR", "frontend/dist"),
        seuma_request_delay_seconds=float(
            os.environ.get("SEUMA_REQUEST_DELAY_SECONDS", "4")
        ),
        seuma_headless=os.environ.get("SEUMA_HEADLESS", "true").strip().lower()
        != "false",
    )


def load_segments() -> dict:
    with open(CONFIG_DIR / "segments.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["segments"]


def load_rf_sources() -> dict:
    with open(CONFIG_DIR / "rf_sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_license_names() -> dict:
    with open(CONFIG_DIR / "licencas_nomes.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def segment_names() -> list[str]:
    return list(load_segments().keys())
