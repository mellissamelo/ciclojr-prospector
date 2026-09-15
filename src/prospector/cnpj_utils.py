"""Extração e validação de números de CNPJ em texto livre."""
from __future__ import annotations

import re

_CNPJ_PATTERN = re.compile(
    r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b"
)

_WEIGHTS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_WEIGHTS_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def normalize(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def is_valid_cnpj(digits: str) -> bool:
    """Valida os dígitos verificadores (módulo 11) para descartar falsos positivos."""
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def _check_digit(base: str, weights: list[int]) -> int:
        total = sum(int(d) * w for d, w in zip(base, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    d1 = _check_digit(digits[:12], _WEIGHTS_1)
    if d1 != int(digits[12]):
        return False
    d2 = _check_digit(digits[:13], _WEIGHTS_2)
    return d2 == int(digits[13])


def extract_cnpj_candidates(text: str) -> list[str]:
    """Retorna CNPJs válidos (14 dígitos, dígito verificador correto), sem duplicatas."""
    seen: list[str] = []
    for match in _CNPJ_PATTERN.findall(text):
        digits = normalize(match)
        if is_valid_cnpj(digits) and digits not in seen:
            seen.append(digits)
    return seen


def format_cnpj(digits: str) -> str:
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
