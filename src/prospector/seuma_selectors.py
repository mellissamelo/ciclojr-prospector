"""IDs e seletores do Portal SEUMA, coletados por inspeção ao vivo do portal real
(não são suposições) em 2026-08-30. JSF regenera esses ids de forma
determinística a partir da árvore de componentes da view, então devem ser
estáveis entre execuções — mas se a prefeitura atualizar o portal, vão quebrar
e precisam ser recoletados (inspecionar a página com o DevTools/JS, como foi
feito para montar este arquivo).
"""

PORTAL_URL = "https://portal.seuma.fortaleza.ce.gov.br/fortalezaonline/portal/portaltransparencia.jsf"

EMPRESA_TAB_LINK = 'a[href="#tvTransparencia:tab02"]'

CNPJ_INPUT_ID = "tvTransparencia:formPortalTransparenciaEmpresa:cnpjEstabelecimento"
NOME_FANTASIA_INPUT_ID = "tvTransparencia:formPortalTransparenciaEmpresa:nomeFantasia"
PESQUISAR_BUTTON_ID = "tvTransparencia:formPortalTransparenciaEmpresa:btnLocalizarPesquisarEmpresas"
LIMPAR_BUTTON_ID = "tvTransparencia:formPortalTransparenciaEmpresa:btnLimparPesquisaPortalTransparenciaEmpresa"

RESULTS_TABLE_ID = "tvTransparencia:formPortalTransparenciaEmpresa:dtListaEmpresas"
RESULTS_TABLE_BODY_ID = RESULTS_TABLE_ID + "_data"
# Linha de resultado tem 3 colunas fixas: CPF/CNPJ, Nome do Licenciado,
# botão Visualizar (confirmado por inspeção ao vivo em 2026-09-11).
RESULT_NAME_CELL_SUFFIX = " tr:first-child td:nth-child(2)"


def visualizar_button_id(row_index: int) -> str:
    return f"tvTransparencia:formPortalTransparenciaEmpresa:dtListaEmpresas:{row_index}:row2"


# Modal "Detalhes da Transparência" (aberto pelo botão Visualizar de uma linha)
NO_DOCS_TEXT = "Nenhum Documento emitido para esta Empresa"
TIPO_SERVICO_SELECT_SELECTOR = 'select[id$="codigoTipoServicoPortalEmpresaLocalizar_input"]'
DETALHE_PANEL_SELECTOR = '[id$="frgDetalhePortalTransparencia"]'
# Container que a AJAX de "Visualizar"/"Abrir" atualiza inteiro (inclui o
# modal "Detalhes da Transparência" e o modal de registro aberto por dentro
# dele) — usado para detectar que uma dessas ações realmente mudou algo.
FRAG_INCLUDES_SELECTOR = "#fragIncludes"
MODAL_FECHAR_BUTTON_SELECTOR = 'button[id$=":btnFechar"]'

# Textos das opções do dropdown de tipo de serviço (universo fixo dos ~11 tipos
# rastreados pelo portal inteiro, confirmado por inspeção). Os únicos usados
# na v1 (decisão do usuário: só verificar o que bate claramente) são estes 3.
LICENSE_TYPE_LABELS = {
    "AF": "Alvará de Funcionamento",
    "LS": "Licença Sanitária",
    "PGRS_PGRSS": "Plano de Residuos",
}
EXEMPTION_LABELS = {
    "LS": "Isenção de Licença Sanitária",
    "PGRS_PGRSS": "Isenção de Plano de Gerenciamento de Resíduos",
}

# Siglas do documento original que não têm correspondência neste portal
# (provavelmente emitidas por outros órgãos: Corpo de Bombeiros, COGERH/ANA
# para Outorga, documentos internos como MBP/POP não são licenças públicas
# consultáveis aqui). Decisão do usuário: reportar como "não verificável".
NOT_VERIFIABLE_SIGLAS = ["AS", "CCB", "LAR", "LPP", "MBP", "POP", "Outorga"]

SESSION_EXPIRED_TEXT = "Sessão Expirada"

# Dentro do painel de detalhe (após clicar "Abrir" num registro específico, ou
# direto no frgDetalhePortalTransparencia dependendo do tipo), os valores
# ficam em <div><label>valor</label></div> ao lado de <div><label>Rótulo:</label></div>.
# CONFIRMADO POR INSPEÇÃO: para Alvará de Funcionamento, a partir do campo
# "Cep" os valores vêm desalinhados uma posição para a esquerda em relação ao
# rótulo (bug do próprio portal) — o texto de status real aparece onde o
# rótulo diz "Cep:", não onde diz "Status:". Por isso a extração não confia em
# posição: varre todos os valores do painel procurando por padrões (datas,
# palavras de status) em vez de usar o rótulo adjacente.
PANEL_LABEL_VALUE_ROW_SELECTOR = ".ui-panelgrid-cell label"
