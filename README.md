# CicloJr Prospector — Leads de licenças municipais vencidas/ausentes (Fortaleza-CE)

Gera uma lista de estabelecimentos em Fortaleza-CE com licenças municipais
vencidas ou ausentes, prontos para prospecção — a fonte dos estabelecimentos
é um extrato local da Receita Federal (`data/rf_fortaleza_*.csv`, já incluído
no repositório), verificados um a um no Portal SEUMA via automação
(Playwright). Ver
[prompt-construcao-sistema-leads-licencas.md](prompt-construcao-sistema-leads-licencas.md)
para o escopo original.

**Nenhuma chave de API é obrigatória.** O sistema funciona sem nenhum
arquivo `.env` — não precisa de conta Google Cloud, faturamento nem nada
pago pra rodar do zero.

## Pré-requisitos

- **Python 3.12+** — baixe em https://www.python.org/downloads/ e marque
  **"Add python.exe to PATH"** no instalador. Confirme com `python --version`.
- **Node.js 18+** (só pro painel web) — baixe em https://nodejs.org/
  (versão LTS) ou instale com `winget install OpenJS.NodeJS.LTS`. Confirme
  com `node --version`.

## Setup (do zero, em qualquer máquina)

```bash
git clone https://github.com/mellissamelo/ciclojr-prospector.git
cd ciclojr-prospector

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Pronto — já dá pra usar. Não precisa criar `.env`, configurar API key nem
buildar o painel manualmente (o passo abaixo faz isso sozinho).

## Como rodar

**Painel web (recomendado):** dê duplo-clique em `iniciar_painel.bat` (ou
rode `python scripts\iniciar_painel.py`). Na primeira vez ele builda o
painel React sozinho (`npm install` + `npm run build` dentro de
`frontend/`, por isso precisa do Node.js) e confirma que o Chromium do
Playwright está instalado — pode demorar um minuto na primeira execução.
Depois disso abre o navegador em http://127.0.0.1:5000/, onde dá pra
escolher setor + bairro e clicar em "Prospectar" direto na página.

**Linha de comando (alternativa):**

```bash
python scripts\run_daily.py "Restaurantes" --log-level DEBUG
```

Recomendo rodar a primeira vez com `SEUMA_HEADLESS=false` num `.env`
(`copy .env.example .env` e editar) pra observar o navegador e confirmar
que os seletores do Portal SEUMA ainda batem com a estrutura real (governos
mudam esses portais sem aviso).

## Agendar execução diária (opcional)

```powershell
.\scripts\setup_task_scheduler.ps1
```

Por padrão roda às 06:00 com rotação automática entre os 14 segmentos (um
por dia). Para fixar um segmento: `.\scripts\setup_task_scheduler.ps1 -Segment "Restaurantes"`.

## Painel

O painel é um app React (`frontend/`, Tailwind + shadcn/ReUI), buildado uma
vez para `frontend/dist` e servido pelo Flask (`web_server.py`) em
http://127.0.0.1:5000/. Os dados vêm de `GET /api/dashboard` (sem arquivo
estático gerado por execução) — três áreas: leads da execução atual +
histórico, calendário de entregas por dia, e dashboard por setor/bairro
(abre em aba própria).

## Estrutura

```
config/segments.yaml          # segmento -> licenças exigidas (✅/⚠️)
config/licencas_nomes.yaml    # sigla -> nome comercial
config/rf_sources.yaml        # segmento -> CSV da Receita Federal + CNAE
data/rf_fortaleza_*.csv       # extrato local da Receita Federal (fonte dos leads)
src/prospector/
  rf_source.py                 # carrega prospects dos CSVs da Receita Federal
  etapa3_seuma.py              # automação Playwright do Portal SEUMA
  seuma_selectors.py           # IDs/seletores do portal (confirmados ao vivo)
  instagram_lookup.py          # busca de @ do Instagram (Bing + verificação)
  dashboard_data.py            # monta os dados do painel (GET /api/dashboard)
  web_server.py                # Flask: API + serve o painel React buildado
  pipeline.py                  # orquestra a geração de leads
  db.py                        # SQLite: histórico + dedup
  etapa1_maps.py, etapa2_cnpj.py  # legado/opcional — ver .env.example
frontend/                     # painel React + Tailwind + shadcn/ReUI
scripts/run_daily.py          # CLI de entrada
scripts/iniciar_painel.py     # sobe o servidor + builda o painel se precisar
scripts/setup_task_scheduler.ps1
```

## Notas técnicas da construção

Detalhes de decisões e bugs encontrados ao vivo durante o desenvolvimento —
útil pra quem for mexer no código, não necessário só pra usar o sistema.

<details>
<summary>Decisões tomadas durante a construção</summary>

O escopo original tinha algumas premissas que não bateram com a realidade
técnica das APIs/portais envolvidos. Foram verificadas ao vivo e ajustadas
com a aprovação do usuário:

1. **CNPJ por nome**: a BrasilAPI só permite consulta por número de CNPJ já
   conhecido, não por nome. Isso motivou a troca da fonte de leads pro
   extrato local da Receita Federal (`rf_source.py`), que já vem com CNPJ,
   nome e bairro prontos — os módulos antigos `etapa1_maps.py`/`etapa2_cnpj.py`
   (Google Places + Google Custom Search) ficaram como legado opcional.
2. **Taxonomia real do Portal SEUMA**: o portal só rastreia digitalmente 11
   tipos de documento no total. Das 10 siglas da tabela de segmentos, só
   **AF** (Alvará de Funcionamento), **LS** (Licença Sanitária) e
   **PGRS/PGRSS** (Plano de Resíduos) têm correspondência clara e são
   verificadas de verdade. **AS, CCB, LAR, LPP, MBP, POP e Outorga** não
   aparecem na lista do portal (provavelmente emitidas por outros órgãos —
   Corpo de Bombeiros, COGERH/ANA etc.) e aparecem no output como
   `nao_verificavel`, sem travar a qualificação do lead. Ver
   [config/segments.yaml](config/segments.yaml) e
   [src/prospector/seuma_selectors.py](src/prospector/seuma_selectors.py).
3. **Bug confirmado no próprio Portal SEUMA**: no painel de detalhe do
   Alvará de Funcionamento, os valores aparecem desalinhados dos rótulos a
   partir do campo "Cep" (o texto de status real aparece sob o rótulo
   "Cep:", não "Status:"). A extração (`etapa3_seuma.py`) não confia em
   posição — varre todos os valores do painel procurando datas e palavras de
   status.
4. **Nomes comerciais das licenças** ([config/licencas_nomes.yaml](config/licencas_nomes.yaml)):
   preenchido com placeholders (nome por extenso) — troque pelos nomes
   comerciais reais antes de operar em produção, se necessário.

</details>

<details>
<summary>Estado da automação do Portal SEUMA — testada ao vivo</summary>

A Etapa 3 (`etapa3_seuma.py`) rodou de ponta a ponta contra o portal real
(não é só teoria) para dois CNPJs conhecidos — um com Alvará de
Funcionamento válido e um sem nenhum documento — em sequência, dentro da
mesma sessão de navegador (o jeito que o pipeline usa de verdade). Bugs reais
encontrados e corrigidos nesse processo, todos no arquivo `etapa3_seuma.py`:

- Esperar por `page.expect_response` (resposta de rede) é **intermitente**
  neste portal — às vezes o clique não dispara a requisição na primeira
  tentativa, sem erro nenhum. Trocado por comparação do HTML antes/depois da
  ação.
- Esperar por um texto aparecer (ex.: "Total:") não funciona quando esse
  texto **já existe** na página antes da ação (estado inicial zerado) — a
  espera retornava na hora, lendo resultado desatualizado.
- O portal é genuinamente lento: um modal "Processando..." fica bloqueando
  fisicamente os próximos cliques por vários segundos (confirmado pelo
  próprio erro do Playwright: "intercepts pointer events"). A extração
  espera esse overlay sumir antes de clicar de novo.
- O painel de "Status/Data de validade" de um registro aberto (botão
  "Abrir") vive num dialog **irmão**, fora do container que a extração
  varria originalmente — corrigido para varrer o modal inteiro.
- Fechar os diálogos: pode haver dois empilhados (o da empresa + o do
  registro aberto por dentro dele) — fechar só o de fora travava. Corrigido
  para fechar do mais interno pro mais externo.

O layout de Licença Sanitária e Plano de Resíduos foi confirmado no caminho
"ausente" (a sigla não aparece no dropdown da empresa testada, que não tem
nenhuma das duas). O caminho "válida"/"vencida" desses dois tipos
especificamente (diferente do de Alvará de Funcionamento) ainda não foi
visto com um CNPJ de exemplo real — a extração usa o mesmo código tolerante
a posição do Alvará, então deve funcionar, mas vale conferir no primeiro dia
de operação real.

</details>
