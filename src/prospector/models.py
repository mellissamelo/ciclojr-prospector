from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Establishment:
    """Saída da Etapa 1 (Google Maps)."""

    name: str
    address: str
    google_place_id: str
    segment: str


@dataclass
class ProspectLead:
    """Saída da Etapa 2 (CNPJ + Instagram)."""

    name: str
    address: str
    segment: str
    cnpj: str
    instagram: str | None
    google_place_id: str
    bairro: str = ""
    owner_name: str = ""


# Status que tornam um lead prospectável: já vencida, ausente, ou vencendo
# dentro da janela de antecedência (decisão do usuário — até 3 meses antes já
# vale abordar, ver VENCENDO_EM_BREVE_DIAS em etapa3_seuma.py).
PROSPECTAVEL_STATUSES = ("vencida", "ausente", "vencendo_em_breve")


@dataclass
class LicenseStatus:
    sigla: str
    nome_comercial: str
    status: str  # "valida" | "vencendo_em_breve" | "vencida" | "ausente" | "isento" | "nao_verificavel"
    data_validade: str | None = None
    forte_demanda: bool = False


@dataclass
class QualifiedLead:
    """Saída final da Etapa 3, pronta para o painel (Etapa 4)."""

    name: str
    cnpj: str
    instagram: str | None
    segment: str
    bairro: str = ""
    owner_name: str = ""
    licenses: list[LicenseStatus] = field(default_factory=list)

    @property
    def pending_licenses(self) -> list[LicenseStatus]:
        return [l for l in self.licenses if l.status in PROSPECTAVEL_STATUSES]

    @property
    def is_qualified(self) -> bool:
        return any(l.status in PROSPECTAVEL_STATUSES and l.forte_demanda for l in self.licenses)
