# Prospector — Leads de licenças municipais vencidas/ausentes (Fortaleza-CE)

Gera diariamente uma lista de estabelecimentos em Fortaleza-CE com licenças
municipais vencidas ou ausentes, prontos para prospecção. Ver
[prompt-construcao-sistema-leads-licencas.md](prompt-construcao-sistema-leads-licencas.md)
para o escopo original.

## Decisões tomadas durante a construção (leia antes de rodar)

O escopo original tinha algumas premissas que não bateram com a realidade
técnica das APIs/portais envolvidos. Foram verificadas ao vivo e ajustadas
com a aprovação do usuário:

1. **CNPJ por nome**: a BrasilAPI só permite consulta por número de CNPJ já
   conhecido, não por nome. A Etapa 2 usa a Google Custom Search API
   (oficial) para achar candidatos a CNPJ por `"<nome>" <endereço> CNPJ`, e
   valida cada candidato na BrasilAPI comparando o nome retornado (mesma
   regra de descarte por ambiguidade do documento original).
2. **Google Places tier**: nome/endereço/tipo exigem tier Pro (não
   Essentials); telefone e site (`websiteUri`) exigem tier Enterprise, bem
   mais caro. Como nem telefone nem site aparecem em nenhum output final,
   foram removidos do escopo — a Etapa 1 fica só no tier Pro (5.000
   chamadas grátis/mês, cobre o volume do projeto).
3. **Taxonomia real do Portal SEUMA**: o portal só rastreia digitalmente 11
   tipos de documento no total. Das 10 siglas da tabela de segmentos, só
   **AF** (Alvará de Funcionamento), **LS** (Licença Sanitária) e
   **PGRS/PGRSS** (Plano de Resíduos) têm correspondência clara e são
   verificadas de verdade. **AS, CCB, LAR, LPP, MBP, POP e Outorga** não
   aparecem na lista do portal (provavelmente emitidas por outros órgãos —
   Corpo de Bombeiros, COGERH/ANA etc.) e aparecem no output como
   `nao_verificavel`, sem travar a qualificação do lead. Ver
   [config/segments.yaml](config/segments.yaml) e
   [src/prospector/seuma_selectors.py](src/prospector/seuma_selectors.py).
4. **Bug confirmado no próprio Portal SEUMA**: no painel de detalhe do
   Alvará de Funcionamento, os valores aparecem desalinhados dos rótulos a
   partir do campo "Cep" (o texto de status real aparece sob o rótulo
   "Cep:", não "Status:"). A extração (`etapa3_seuma.py`) não confia em
   posição — varre todos os valores do painel procurando datas e palavras de
   status.
5. **Nomes comerciais das licenças** ([config/licencas_nomes.yaml](config/licencas_nomes.yaml)):
   o documento original deixa essa tabela pendente. Preenchi com placeholders
   (nome por extenso) — troque pelos nomes comerciais reais antes de operar
   em produção.

## Estado da automação do Portal SEUMA — testada ao vivo

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
nenhuma das duas). O caminho "válida"/"vencida" desses dois tipos especificamente
(diferente do de Alvará de Funcionamento) ainda não foi visto com um CNPJ de
exemplo real — a extração usa o mesmo código tolerante a posição do Alvará,
então deve funcionar, mas vale conferir no primeiro dia de operação real.

## Setup

O ambiente já foi configurado uma vez durante a construção: Python 3.14
instalado, venv criado em `.venv/` com todas as dependências e o Chromium do
Playwright já baixado. Para continuar usando:

```bash
.venv\Scripts\activate
python scripts\run_daily.py "Restaurantes"
```

Se for configurar do zero em outra máquina, os passos completos:

### 1. Instalar Python

Instale manualmente (baixe o instalador oficial, não use a Microsoft Store —
em ambientes sandboxed tanto `winget` quanto o instalador MSI padrão podem
falhar; o download direto do `.exe` em modo silencioso funcionou aqui):

- Baixe em https://www.python.org/downloads/ (3.12+) e **marque "Add python.exe to PATH"** no instalador.
- Confirme no PowerShell: `python --version`

### 2. Instalar dependências

```bash
cd caminho\para\prospector
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar chaves de API

```bash
copy .env.example .env
```

Preencha `.env` com:
- `GOOGLE_MAPS_API_KEY`: projeto Google Cloud com faturamento ativo e Places
  API (New) habilitada.
- `GOOGLE_CSE_API_KEY` / `GOOGLE_CSE_ID`: crie um mecanismo de busca em
  https://programmablesearchengine.google.com/ configurado para "Search the
  entire web", habilite a Custom Search API no Google Cloud e gere uma chave.
  **Cota grátis: 100 buscas/dia** — pode não ser suficiente para o volume
  cheio do projeto (até ~120 buscas/dia na Etapa 2, dependendo de quantos
  estabelecimentos a Etapa 1 retornar); o cliente para de tentar quando a
  cota estoura e retoma no dia seguinte, sem quebrar a execução.

### 4. Testar manualmente

```bash
python scripts\run_daily.py "Restaurantes" --log-level DEBUG
```

Recomendo rodar a primeira vez com `SEUMA_HEADLESS=false` no `.env` para
observar o navegador e confirmar que os seletores do Portal SEUMA ainda
batem com a estrutura real (governos mudam esses portais sem aviso).

### 5. Agendar execução diária

```powershell
.\scripts\setup_task_scheduler.ps1
```

Por padrão roda às 06:00 com rotação automática entre os 14 segmentos (um
por dia). Para fixar um segmento: `.\scripts\setup_task_scheduler.ps1 -Segment "Restaurantes"`.

## Painel

O painel é um app React (`frontend/`, Tailwind + shadcn/ReUI), buildado uma
vez para `frontend/dist` e servido pelo Flask (`web_server.py`) em
http://127.0.0.1:5000/ — dê duplo-clique em `iniciar_painel.bat` (builda o
front sozinho na primeira vez, precisa de Node.js instalado). Os dados vêm
de `GET /api/dashboard`, sem arquivo estático gerado por execução.

## Estrutura

```
config/segments.yaml          # segmento -> licenças exigidas (✅/⚠️)
config/licencas_nomes.yaml    # sigla -> nome comercial (placeholders, ajustar)
src/prospector/
  etapa1_maps.py              # Google Places Text Search
  etapa2_cnpj.py              # CNPJ (Custom Search + BrasilAPI) + Instagram
  etapa3_seuma.py             # Automação Playwright do Portal SEUMA
  seuma_selectors.py          # IDs/seletores do portal (confirmados ao vivo)
  dashboard_data.py           # monta os dados do painel (GET /api/dashboard)
  web_server.py               # Flask: API + serve o painel React buildado
  pipeline.py                 # orquestra as 4 etapas
  db.py                       # SQLite: histórico + dedup
frontend/                     # painel React + Tailwind + shadcn/ReUI
scripts/run_daily.py          # CLI de entrada
scripts/iniciar_painel.py     # sobe o servidor + builda o painel se precisar
scripts/setup_task_scheduler.ps1
```
