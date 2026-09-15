"""Busca do @ do Instagram de um estabelecimento por nome, sem API paga e sem
LLM — decisão do usuário (2026-09-11): nada de ScrapeGraphAI/OpenAI/Ollama
aqui, só uma busca direta num motor de busca com extração do handle por
regex.

Testado ao vivo (2026-09-11): o endpoint de busca do DuckDuckGo
(duckduckgo.com/html/) bloqueia o Playwright headless com uma página de
desafio ("anomaly"/challenge), mesmo com user-agent de navegador real — não
retorna resultados de verdade. O Bing (bing.com/search) funcionou normalmente
no mesmo teste. Por isso a busca é feita no Bing.

O Bing não expõe o link real do Instagram no href de cada resultado (é um elo
de rastreamento bing.com/ck/a?...), mas mostra a URL no `<cite>` de cada
resultado como "https://www.instagram.com › <handle>" (separador U+203A) — é
daí que o handle é extraído.

Confirmado ao vivo (2026-09-14) que o handle mais citado no Bing nem sempre é
o certo: para "AQUATIC ACADEMIA LTDA - ME" o Bing insistiu em "aquaticabrazil"
(perfil de outra empresa, "Aquática Brazil") em vez do real "aquaticlinicacademia"
("Clínica e Academia Aquatic"), mesmo testando várias variações da busca — o
problema era o resultado do Bing, não a query. Por isso agora cada candidato é
verificado de verdade antes de aceitar: visita o perfil e confere se alguma
palavra significativa do nome do estabelecimento aparece no título da página.
Só cai pro próximo candidato (por ordem de quantas vezes apareceu no Bing) se
a verificação falhar — evita mostrar um Instagram de outro negócio como se
fosse do lead.

Só é chamada para leads que já vão ser efetivamente entregues (qualificados +
`db.should_deliver`), não para todo CNPJ checado — é uma etapa por si só mais
lenta (navegação real) e não vale a pena rodar pros ~milhares de descartes.

Reaproveita o `browser` já aberto pelo etapa3_seuma (uma página nova, não uma
sessão de Playwright separada) — descoberto ao vivo que dois `sync_playwright()`
independentes na mesma thread conflitam ("Playwright Sync API inside the
asyncio loop"), então nunca chame `sync_playwright().start()` de novo aqui.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from urllib.parse import quote

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError

log = logging.getLogger(__name__)

SEARCH_TIMEOUT_MS = 15_000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

CITE_RE = re.compile(r"<cite>(.*?)</cite>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
# "instagram.com › handle" — o separador é U+203A (›).
INSTAGRAM_CITE_RE = re.compile(r"instagram\.com\s*›\s*([A-Za-z0-9_.]+)", re.IGNORECASE)

# Segmentos de path do instagram.com que não são um perfil de estabelecimento.
NOT_A_PROFILE = {
    "p",
    "reel",
    "reels",
    "explore",
    "accounts",
    "about",
    "developer",
    "legal",
    "directory",
    "web",
    "stories",
    "popular",
    "tv",
}

# Sufixos de razão social/tipo societário — não ajudam a confirmar que um
# perfil do Instagram é do estabelecimento certo, então saem antes de montar
# a lista de palavras significativas pra verificação.
_LEGAL_SUFFIXES = {
    "ltda", "me", "epp", "eireli", "sa", "s/a", "cia", "mei", "junior", "filho",
}
_MIN_WORD_LEN = 4


def open_search_page(browser: Browser) -> Page:
    return browser.new_page(user_agent=USER_AGENT)


def close_search_page(page: Page) -> None:
    page.close()


def _ranked_candidates(html: str) -> list[str]:
    candidates: list[str] = []
    for cite in CITE_RE.findall(html):
        text = TAG_RE.sub("", cite)
        m = INSTAGRAM_CITE_RE.search(text)
        if m:
            handle = m.group(1).rstrip(".")
            if handle.lower() not in NOT_A_PROFILE:
                candidates.append(handle.lower())
    # perfis reais tendem a aparecer em mais de um resultado (post, reels,
    # stories); ordena do mais citado pro menos citado, mas todos entram —
    # a verificação de título é que decide qual é o certo, não a contagem.
    return [handle for handle, _count in Counter(candidates).most_common()]


def _significant_words(name: str) -> list[str]:
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", name.lower())
    return [w for w in words if len(w) >= _MIN_WORD_LEN and w not in _LEGAL_SUFFIXES]


def _verify_handle(browser: Browser, handle: str, words: list[str]) -> bool:
    """Visita o perfil público e confere se alguma palavra significativa do
    nome do estabelecimento aparece no NOME DE EXIBIÇÃO do perfil — sem isso,
    o handle mais citado no Bing pode ser de uma empresa totalmente diferente
    (visto ao vivo, ver docstring do módulo).

    O título da página vem como "Nome de Exibição (@handle) • Instagram...";
    comparar contra o título inteiro é furada porque o próprio @handle quase
    sempre contém palavras do nome pesquisado (ex.: "aquaticabrazil" contém
    "aquatic" mesmo sendo um perfil de outra empresa) — só a parte antes do
    "(@" é o nome de exibição de verdade.

    Confirmado ao vivo (2026-09-14) que verificar na MESMA página que acabou
    de visitar o Bing dá um título errado do Instagram com bastante
    frequência (~40% das vezes, mesmo mandando `referer=""` explícito no
    goto) — o mesmo handle testado numa aba nova, sem esse histórico, sempre
    veio com o título certo. Por isso abre uma aba nova só pra essa checagem,
    em vez de reusar a página da busca."""
    if not words:
        return True  # nome sem palavra específica o bastante pra verificar
    verify_page = browser.new_page(user_agent=USER_AGENT)
    try:
        try:
            verify_page.goto(f"https://www.instagram.com/{handle}/", timeout=SEARCH_TIMEOUT_MS)
        except Exception:
            return False
        try:
            verify_page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass  # segue com o título que tiver — melhor que travar a execução
        title = verify_page.title() or ""
    finally:
        verify_page.close()
    display_name = title.split(" (@")[0].lower()
    return any(w in display_name for w in words)


def find_instagram(page: Page, browser: Browser, establishment_name: str, bairro: str = "") -> str | None:
    """Retorna o handle (sem "@", mesma convenção usada pelo painel pra montar
    o link https://instagram.com/<handle>) se achar E confirmar um perfil do
    Instagram para o estabelecimento, ou None (não impede a qualificação do
    lead) — sem confirmação, prefere não mostrar nada a mostrar errado.

    `page` faz a busca no Bing; `browser` é usado só pra abrir a aba isolada
    de verificação (ver `_verify_handle`)."""
    if not establishment_name:
        return None

    query = f'"{establishment_name}" Fortaleza instagram'
    if bairro:
        query = f'"{establishment_name}" {bairro} Fortaleza instagram'
    url = f"https://www.bing.com/search?q={quote(query)}"

    try:
        page.goto(url, timeout=SEARCH_TIMEOUT_MS)
        html = page.content()
    except PlaywrightTimeoutError:
        log.warning("Timeout buscando Instagram de '%s'.", establishment_name)
        return None
    except Exception as e:
        log.warning("Falha buscando Instagram de '%s': %s", establishment_name, e)
        return None

    candidates = _ranked_candidates(html)
    if not candidates:
        return None

    words = _significant_words(establishment_name)
    for handle in candidates:
        if _verify_handle(browser, handle, words):
            return handle
    log.info(
        "Achei %d candidato(s) de Instagram pra '%s' mas nenhum bateu com o nome — descartando.",
        len(candidates), establishment_name,
    )
    return None
