"""Etapa 3 — Verificação de Licenças no Portal SEUMA.

Portal JSF sem API pública: automação via Playwright (navegador headless).
Estrutura e IDs (ver seuma_selectors.py) foram confirmados por inspeção ao
vivo do portal real, não são suposições. Pontos confirmados na exploração:

  - Buscar por CNPJ retorna 0, 1 ou N linhas; "Visualizar" abre um modal
    específico daquela empresa (dropdown com os tipos de licença QUE ELA TEM,
    ou a mensagem "Nenhum Documento emitido para esta Empresa!").
  - Selecionar um tipo no dropdown carrega uma tabela com o(s) registro(s)
    daquele tipo. Dois layouts confirmados ao vivo pro botão de ação de cada
    registro:
      1. "Abrir" (registros antigos/legado): mostra um dialog com o detalhe
         (status, datas) como texto na própria página.
      2. "Download" (registros atuais — CONFIRMADO com CNPJ
         61.351.766/0001-05, Alvará de Funcionamento): a data de validade só
         existe dentro do PDF baixável, a página não mostra status/data
         nenhum pro usuário. Isso explica por que, antes desse fix, o
         sistema só encontrava licenças "ausente" (empresa sem nenhum
         registro) e nunca "vencida"/"vencendo": para qualquer empresa com
         um Alvará de verdade, a data ficava invisível pro scraper. Agora
         baixa o PDF e lê o texto (pypdf) — o texto vem fora de ordem de
         leitura nesse gerador de PDF específico da prefeitura (datas coladas
         sem separador: "<validade><emissão><número/ano>"), então a extração
         usa um regex posicional pra isso (ver PDF_GLUED_DATES_RE), não busca
         por rótulo.
      Pode haver mais de um registro do mesmo tipo (renovações) — usa o de
      emissão mais recente como o vigente.
  - BUG CONFIRMADO do portal: no painel de detalhe "Abrir" (legado) do
    Alvará de Funcionamento, os valores aparecem desalinhados dos rótulos a
    partir do campo "Cep" (ex.: o texto de status real aparece sob o rótulo
    "Cep:", não "Status:"). Por isso a extração varre TODOS os valores do
    painel por padrão (data / palavra de status), nunca por rótulo adjacente.
  - O formato do PDF de Licença Sanitária e Plano de Resíduos NÃO foi
    confirmado ao vivo (só o de Alvará de Funcionamento foi, por falta de um
    CNPJ de exemplo com registro real desses dois tipos) — o parser de datas
    pode não bater com o layout desses PDFs; quando falha, o código assume
    "valida" por segurança (não alega vencimento sem confirmar) e loga um
    aviso. Testar com um CNPJ real desses tipos antes de confiar cegamente.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
from pypdf import PdfReader

from prospector import seuma_selectors as sel
from prospector.cnpj_utils import normalize
from prospector.models import LicenseStatus, ProspectLead

log = logging.getLogger(__name__)

AJAX_TIMEOUT_MS = 15000
# O carregamento inicial do portal (goto_portal) monta o ViewState JSF do
# zero no servidor — bem mais lento que uma requisição AJAX numa sessão já
# aberta. 15s era curto demais aqui (visto ao vivo: um carregamento normal já
# levou 11.4s, sem margem nenhuma) e derrubava a execução inteira por causa
# de uma única lentidão passageira do portal.
PORTAL_LOAD_TIMEOUT_MS = 30000
DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

STATUS_VENCIDA_KEYWORDS = ["vencid", "expirad", "cancelad", "indeferid", "suspens"]
STATUS_VALIDA_KEYWORDS = ["permitid", "deferid", "valid", "ativ", "regular", "concluíd", "concluid"]

# Quantos dias antes do vencimento já vale prospectar (decisão do usuário:
# "até 3 meses antes já podemos começar a prospectar").
VENCENDO_EM_BREVE_DIAS = 90

# CONFIRMADO ao vivo (CNPJ 61.351.766/0001-05, Alvará de Funcionamento): a
# data de validade real de um documento com registro ativo só existe dentro
# do PDF baixável (botão "Download" na tabela de registros) — a página em si
# não expõe essa data em texto. O texto extraído do PDF vem fora de ordem de
# leitura (é assim que o pypdf extrai esse layout de tabela específico do
# gerador de PDF da prefeitura): "<validade><emissão><número/ano>" colados
# sem separador, ex.: "30/10/202630/10/2025AF00165685/2025".
PDF_GLUED_DATES_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})(\d{2}/\d{2}/\d{4})[A-Z]{1,4}\d+/\d{4}"
)


def _classify_by_date(validade: date) -> str:
    hoje = date.today()
    if validade < hoje:
        return "vencida"
    if validade <= hoje + timedelta(days=VENCENDO_EM_BREVE_DIAS):
        return "vencendo_em_breve"
    return "valida"


class SeumaSearchResult:
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    OK = "ok"


def open_browser(headless: bool):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    return playwright, browser, page


def close_browser(playwright, browser) -> None:
    try:
        browser.close()
    finally:
        playwright.stop()


def goto_portal(page: Page) -> None:
    page.goto(sel.PORTAL_URL, wait_until="domcontentloaded")
    page.click(sel.EMPRESA_TAB_LINK)
    page.wait_for_selector(f"#{_css_escape(sel.CNPJ_INPUT_ID)}", timeout=PORTAL_LOAD_TIMEOUT_MS)


def _css_escape(jsf_id: str) -> str:
    return jsf_id.replace(":", r"\:")


def _is_session_expired(page: Page) -> bool:
    return sel.SESSION_EXPIRED_TEXT in page.inner_text("body")


PROCESSING_OVERLAY_TIMEOUT_MS = 20000


def _wait_processing_overlay_gone(page: Page) -> None:
    """O portal mostra um modal "Processando..." (`.ui-widget-overlay.ui-dialog-mask`)
    durante/depois de cada ação AJAX que, em teste ao vivo, ficou visível por
    bem mais que alguns milissegundos — o suficiente para BLOQUEAR
    fisicamente o próximo clique (confirmado pelo próprio Playwright: erro
    "intercepts pointer events" nesse elemento). Por isso, antes de clicar em
    qualquer coisa depois de uma ação anterior, espera esse overlay sumir de
    verdade em vez de só dar uma pausa fixa."""
    try:
        page.wait_for_function(
            """() => [...document.querySelectorAll('.ui-widget-overlay.ui-dialog-mask')]
                        .every(el => el.offsetParent === null)""",
            timeout=PROCESSING_OVERLAY_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        log.warning("Overlay 'Processando...' não sumiu a tempo, seguindo mesmo assim.")


def _wait_ajax_settle(page: Page, extra_ms: int = 300) -> None:
    """JSF/PrimeFaces AJAX não expõe um evento simples de 'terminou'; espera o
    overlay de carregamento sumir de verdade e dá uma folga curta extra para
    o DOM assentar antes de ler."""
    _wait_processing_overlay_gone(page)
    page.wait_for_timeout(extra_ms)


def _content_snapshot(page: Page, watch_selector: str) -> str:
    loc = page.locator(watch_selector)
    if loc.count() == 0:
        return ""
    try:
        return loc.first.inner_html()
    except Exception:
        return ""


def _visible_dialog_open(page: Page) -> bool:
    return page.evaluate(
        """() => [...document.querySelectorAll('.ui-dialog-content')]
                    .some(el => el.offsetParent !== null && el.innerText.trim().length > 0)"""
    )


def _act_and_wait_change(
    page: Page,
    action,
    watch_selector: str,
    timeout_per_attempt_ms: int = 20000,
    max_attempts: int = 2,
) -> bool:
    """Executa `action()` (um clique ou uma seleção) e espera o HTML de
    watch_selector mudar em relação ao estado anterior à ação.

    Lições de testes ao vivo contra o portal real que moldaram este design:
    1. Esperar por RESPOSTA de rede (page.expect_response) se mostrou
       intermitente neste portal — às vezes o clique não dispara a
       requisição na primeira tentativa (sem erro no console), então a
       espera por resposta trava até estourar o timeout à toa.
    2. Esperar por TEXTO aparecer (ex.: "Total:") não funciona quando esse
       texto já existe na página antes da ação (estado inicial zerado) — a
       espera retorna na hora, antes da ação terminar de verdade.
    3. O portal é genuinely lento (ações levaram >10s em teste ao vivo) — um
       timeout curto por tentativa combinado com retry agressivo faz o
       código clicar de novo ANTES da primeira ação terminar, e o clique
       duplicado trava contra o modal que a primeira ação acabou de abrir
       (confirmado: erro "intercepts pointer events" do próprio elemento
       recém-aberto). Por isso o timeout por tentativa é generoso e, antes
       de tentar de novo, checa se já apareceu um diálogo visível — se sim,
       trata como sucesso em vez de clicar de novo."""
    for attempt in range(max_attempts):
        _wait_processing_overlay_gone(page)
        if attempt > 0 and _visible_dialog_open(page):
            # a tentativa anterior na verdade funcionou (só não detectamos a
            # tempo) — reclicar agora só bateria contra o diálogo já aberto.
            log.info("Diálogo já aberto antes de tentar de novo — seguindo sem reclicar.")
            return True
        before = _content_snapshot(page, watch_selector)
        try:
            action()
            page.wait_for_function(
                """([sel, prev]) => {
                    const el = document.querySelector(sel);
                    const cur = el ? el.innerHTML : '';
                    return cur !== prev;
                }""",
                arg=[watch_selector, before],
                timeout=timeout_per_attempt_ms,
            )
            _wait_ajax_settle(page)
            return True
        except PlaywrightTimeoutError:
            if _visible_dialog_open(page):
                log.info("Sem diff detectado em '%s', mas um diálogo já está aberto — seguindo.", watch_selector)
                _wait_ajax_settle(page)
                return True
            log.warning(
                "Sem mudança em '%s' após ação (tentativa %d/%d)",
                watch_selector,
                attempt + 1,
                max_attempts,
            )
    return False


def search_by_cnpj(page: Page, cnpj_digits: str) -> str:
    page.fill(f"#{_css_escape(sel.NOME_FANTASIA_INPUT_ID)}", "")
    cnpj_input = page.locator(f"#{_css_escape(sel.CNPJ_INPUT_ID)}")
    cnpj_input.fill(cnpj_digits)

    changed = _act_and_wait_change(
        page,
        lambda: page.click(f"#{_css_escape(sel.PESQUISAR_BUTTON_ID)}"),
        f"#{_css_escape(sel.RESULTS_TABLE_ID)}",
    )
    if not changed:
        log.warning("Timeout esperando resultado da busca por CNPJ %s", cnpj_digits)
        return SeumaSearchResult.NOT_FOUND

    body_text = page.inner_text("body")
    if "Nenhum registro encontrado" in body_text:
        return SeumaSearchResult.NOT_FOUND

    match = re.search(r"Total:\s*(\d+)", body_text)
    total = int(match.group(1)) if match else 0
    if total == 0:
        return SeumaSearchResult.NOT_FOUND
    if total > 1:
        # Regra da Etapa 3, item 5: mais de uma empresa sem forma clara de
        # desambiguar -> descartar. Como a busca foi por CNPJ exato, >1
        # resultado é inesperado e tratado como ambíguo por segurança.
        return SeumaSearchResult.AMBIGUOUS
    return SeumaSearchResult.OK


def get_result_name(page: Page) -> str:
    """Lê o 'Nome do Licenciado' da linha de resultado (2ª coluna da tabela),
    a fonte mais confiável de nome já que vem direto do portal — usado para
    segmentos cujo extrato local não traz nome (só CNPJ)."""
    cell = page.locator(f"#{_css_escape(sel.RESULTS_TABLE_BODY_ID)}{sel.RESULT_NAME_CELL_SUFFIX}")
    if cell.count() == 0:
        return ""
    return cell.first.inner_text().strip()


def open_first_result_details(page: Page) -> None:
    row_button_id = sel.visualizar_button_id(0)
    changed = _act_and_wait_change(
        page,
        lambda: page.click(f"#{_css_escape(row_button_id)}"),
        sel.FRAG_INCLUDES_SELECTOR,
    )
    if not changed:
        log.warning("Timeout esperando modal de detalhes abrir")


def has_no_documents(page: Page) -> bool:
    return sel.NO_DOCS_TEXT in page.inner_text("body")


def get_available_license_types(page: Page) -> list[str]:
    select = page.locator(sel.TIPO_SERVICO_SELECT_SELECTOR)
    if select.count() == 0:
        return []
    options = select.locator("option").all_inner_texts()
    # remove a opção em branco e o contador "( N )" de cada label
    return [re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", o).strip() for o in options if o.strip()]


def _select_license_type(page: Page, type_label_prefix: str) -> bool:
    """Seleciona no dropdown a opção cujo texto começa com type_label_prefix.
    Retorna False se a opção não existir (chamador já deve ter checado com
    get_available_license_types, isso é uma segunda garantia)."""
    select = page.locator(sel.TIPO_SERVICO_SELECT_SELECTOR)
    options = select.locator("option").all_inner_texts()
    for i, opt in enumerate(options):
        if opt.strip().startswith(type_label_prefix):
            changed = _act_and_wait_change(
                page,
                lambda idx=i: select.select_option(index=idx),
                sel.DETALHE_PANEL_SELECTOR,
            )
            if not changed:
                log.warning("Timeout esperando detalhe do tipo de licença '%s'", type_label_prefix)
                return False
            return True
    return False


def _download_pdf_text(page: Page, button) -> str | None:
    try:
        with page.expect_download(timeout=AJAX_TIMEOUT_MS) as dl_info:
            button.click()
        download = dl_info.value
        path = download.path()
        if not path:
            return None
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except PlaywrightTimeoutError:
        log.warning("Timeout baixando PDF do documento.")
        return None
    except Exception as e:  # leitura de PDF pode falhar de várias formas (arquivo corrompido, etc.)
        log.warning("Falha ao baixar/ler PDF do documento: %s", e)
        return None


def _parse_pdf_dates(text: str) -> tuple[date | None, date | None]:
    """Retorna (validade, emissão) a partir do texto extraído do PDF (ver
    PDF_GLUED_DATES_RE)."""
    m = PDF_GLUED_DATES_RE.search(text)
    if not m:
        return None, None

    def _parse(s: str) -> date | None:
        d, mth, y = s.split("/")
        try:
            return date(int(y), int(mth), int(d))
        except ValueError:
            return None

    return _parse(m.group(1)), _parse(m.group(2))


def _record_status_from_table(page: Page) -> tuple[str, str | None]:
    """A partir do painel de detalhe já com uma tabela de registros
    carregada (dropdown de tipo de licença já selecionado), determina o
    status. Pode haver mais de um registro (ex.: renovações de Alvará) — usa
    o de emissão mais recente como o vigente. Retorna (status, data_validade_str).

    Dois layouts confirmados ao vivo:
    - Botão "Abrir": mostra um dialog com texto na própria página (layout
      legado — ver _extract_status_from_panel).
    - Botão "Download": a data de validade só existe dentro do PDF baixável
      (confirmado com CNPJ 61.351.766/0001-05) — baixa e lê o PDF."""
    panel = page.locator(sel.DETALHE_PANEL_SELECTOR)
    count = panel.locator("button").count()
    if count == 0:
        return "indeterminado", None

    label = panel.locator("button").first.inner_text().strip()

    if label == "Abrir":
        changed = _act_and_wait_change(
            page, lambda: panel.locator("button").first.click(), sel.FRAG_INCLUDES_SELECTOR
        )
        if not changed:
            log.warning("Timeout esperando o registro abrir (botão 'Abrir')")
            return "indeterminado", None
        return _extract_status_from_panel(page)

    if label == "Download":
        best_validade: date | None = None
        best_emissao: date | None = None
        for i in range(count):
            _wait_processing_overlay_gone(page)
            btn = panel.locator("button").nth(i)  # relocaliza a cada volta, evita referência velha
            text = _download_pdf_text(page, btn)
            if not text:
                continue
            validade, emissao = _parse_pdf_dates(text)
            if validade is None:
                continue
            if best_emissao is None or (emissao and emissao > best_emissao):
                best_validade, best_emissao = validade, emissao

        if best_validade is None:
            log.warning(
                "Não consegui extrair data de validade de nenhum PDF (%d registro(s) de "
                "'%s'); tratando como 'valida' por segurança — revisar manualmente.",
                count,
                label,
            )
            return "indeterminado", None

        return _classify_by_date(best_validade), best_validade.strftime("%d/%m/%Y")

    log.warning("Botão de ação desconhecido num registro do SEUMA: %r", label)
    return "indeterminado", None


def _classify_status(values: list[str]) -> tuple[str | None, str | None]:
    """Varre os valores do painel (não os rótulos, por causa do bug de
    desalinhamento confirmado) procurando uma data de validade e uma palavra
    de status. Retorna (status_encontrado, data_encontrada)."""
    found_date = None
    found_status_word = None

    for v in values:
        v_clean = v.strip()
        if not v_clean:
            continue
        if found_date is None:
            m = DATE_RE.search(v_clean)
            if m:
                found_date = v_clean

        lower = v_clean.lower()
        if found_status_word is None:
            if any(k in lower for k in STATUS_VENCIDA_KEYWORDS):
                found_status_word = "vencida"
            elif any(k in lower for k in STATUS_VALIDA_KEYWORDS):
                found_status_word = "valida"

    return found_status_word, found_date


def _extract_status_from_panel(page: Page) -> tuple[str, str | None]:
    """Retorna (status, data_validade_str_ou_None). status em {"valida","vencida","indeterminado"}.

    Varre o #fragIncludes INTEIRO, não só o frgDetalhePortalTransparencia:
    confirmado ao vivo que o dialog de detalhe de um registro aberto (botão
    "Abrir", ex.: "Detalhes do Alvará de Funcionamento") é um dialog IRMÃO
    (panelDlgAlvarasLegado), fora do frgDetalhePortalTransparencia — varrer só
    esse último deixa a lista de valores vazia."""
    panel = page.locator(sel.FRAG_INCLUDES_SELECTOR)
    value_texts = panel.locator(sel.PANEL_LABEL_VALUE_ROW_SELECTOR).all_inner_texts()

    status_word, found_date = _classify_status(value_texts)

    if status_word is not None:
        return status_word, found_date

    if found_date is not None:
        try:
            day, month, year = DATE_RE.search(found_date).groups()
            validade = date(int(year), int(month), int(day))
            return _classify_by_date(validade), found_date
        except (ValueError, AttributeError):
            pass

    log.warning(
        "Não foi possível determinar status/validade a partir do painel; "
        "valores encontrados: %s. Tratando como 'valida' por segurança "
        "(evita alegar vencimento sem confirmação) — revisar manualmente.",
        value_texts,
    )
    return "indeterminado", None


def check_license(page: Page, sigla: str) -> tuple[str, str | None]:
    """Verifica uma sigla checável (AF, LS, PGRS_PGRSS) para a empresa cujo
    modal de detalhes já está aberto. Retorna (status, data_validade)."""
    available = get_available_license_types(page)

    exemption_label = sel.EXEMPTION_LABELS.get(sigla)
    if exemption_label and any(a.startswith(exemption_label) for a in available):
        return "isento", None

    type_label = sel.LICENSE_TYPE_LABELS[sigla]
    if not any(a.startswith(type_label) for a in available):
        return "ausente", None

    if not _select_license_type(page, type_label):
        return "ausente", None

    status, data_validade = _record_status_from_table(page)
    if status == "indeterminado":
        status = "valida"
    return status, data_validade


def close_details_modal(page: Page) -> None:
    """Fecha os diálogos abertos. Pode haver mais de um empilhado — ex.: o de
    detalhes da empresa e, por dentro dele, o de um registro aberto via
    'Abrir' — confirmado ao vivo (o botão Fechar de fora fica bloqueado pelo
    diálogo interno ainda aberto por cima). Fecha do mais interno pro mais
    externo, um de cada vez."""
    for _ in range(4):
        if not _visible_dialog_open(page):
            return
        buttons = page.locator('button[id*="Fechar"]')
        closed_one = False
        for i in range(buttons.count() - 1, -1, -1):
            btn = buttons.nth(i)
            if not btn.is_visible():
                continue
            try:
                btn.click(timeout=5000)
                _wait_ajax_settle(page)
                closed_one = True
                break
            except PlaywrightTimeoutError:
                continue
        if not closed_one:
            log.warning("Não consegui fechar todos os diálogos abertos do Portal SEUMA.")
            return


def check_lead_licenses(
    page: Page,
    lead: ProspectLead,
    required_siglas: dict[str, bool],
    license_names: dict[str, str],
    request_delay_seconds: float,
) -> list[LicenseStatus] | None:
    """required_siglas: {sigla: forte_demanda_bool} — todas as siglas do
    segmento (✅ e ⚠️). Retorna None se o lead deve ser descartado (CNPJ não
    encontrado ou ambíguo no portal)."""
    cnpj_digits = normalize(lead.cnpj)

    for attempt in range(2):
        result = search_by_cnpj(page, cnpj_digits)
        if _is_session_expired(page):
            log.warning("Sessão expirada ao buscar CNPJ %s; reabrindo portal.", lead.cnpj)
            goto_portal(page)
            continue
        break
    else:
        return None

    if result in (SeumaSearchResult.NOT_FOUND, SeumaSearchResult.AMBIGUOUS):
        log.info("CNPJ %s: %s no Portal SEUMA, descartando lead.", lead.cnpj, result)
        return None

    if not lead.name:
        portal_name = get_result_name(page)
        if portal_name:
            lead.name = portal_name

    open_first_result_details(page)

    statuses: list[LicenseStatus] = []
    if has_no_documents(page):
        for sigla, forte_demanda in required_siglas.items():
            if sigla in sel.NOT_VERIFIABLE_SIGLAS:
                status = "nao_verificavel"
            else:
                status = "ausente"
            statuses.append(
                LicenseStatus(
                    sigla=sigla,
                    nome_comercial=license_names.get(sigla, sigla),
                    status=status,
                    forte_demanda=forte_demanda,
                )
            )
    else:
        for sigla, forte_demanda in required_siglas.items():
            if sigla in sel.NOT_VERIFIABLE_SIGLAS:
                statuses.append(
                    LicenseStatus(
                        sigla=sigla,
                        nome_comercial=license_names.get(sigla, sigla),
                        status="nao_verificavel",
                        forte_demanda=forte_demanda,
                    )
                )
                continue

            status, validade = check_license(page, sigla)
            statuses.append(
                LicenseStatus(
                    sigla=sigla,
                    nome_comercial=license_names.get(sigla, sigla),
                    status=status,
                    data_validade=validade,
                    forte_demanda=forte_demanda,
                )
            )

    close_details_modal(page)
    page.wait_for_timeout(int(request_delay_seconds * 1000))
    return statuses
