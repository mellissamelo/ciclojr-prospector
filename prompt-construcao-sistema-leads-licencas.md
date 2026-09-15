# Prompt: Sistema de Geração de Leads Qualificados — Licenças Municipais Vencidas/Ausentes (Fortaleza-CE)

Você vai construir um sistema completo que gera, todo dia, uma lista de até 50 leads qualificados: estabelecimentos comerciais em Fortaleza-CE com pelo menos uma licença municipal vencida ou ausente, prontos para prospecção ativa.

## Visão geral
**Input diário**: um tipo de estabelecimento (segmento da tabela abaixo — ex.: "Restaurantes").

O sistema roda 4 etapas em sequência, automaticamente, todo dia:
1. Prospecção (Google Maps)
2. Identificação do CNPJ e do Instagram
3. Verificação de licenças (Portal SEUMA)
4. Atualização do painel com os leads qualificados do dia

**Saída final por lead qualificado**:
- Nome do estabelecimento
- CNPJ
- @Instagram (quando encontrado)
- Quais serviços são necessários (sigla da licença + nome comercial do serviço)
- Status de cada licença exigida para o segmento (válida / vencida / ausente)

## Etapa 1 — Prospecção (Google Maps)
- Usar a **API oficial do Google Places (New)**: Text Search por "`<tipo de estabelecimento>` em Fortaleza, CE".
- Pedir só campos do tier **Essentials** (nome, endereço, telefone, tipo/categoria) — não pedir rating, reviews, fotos ou outros campos Pro/Enterprise, para manter o consumo dentro da cota gratuita mensal (10.000 chamadas grátis/mês no tier Essentials; o volume deste projeto, ~1.500/mês, fica bem abaixo disso).
- Nota: mesmo dentro da cota gratuita, é preciso ter uma conta Google Cloud com faturamento habilitado (cartão cadastrado, sem cobrança dentro da cota).
- O tipo de estabelecimento informado no input diário é o mesmo valor usado como segmento na Etapa 3 — não depender da categoria interna que o Google retorna.
- Saída: lista de estabelecimentos com nome, endereço, telefone.

## Etapa 2 — Identificação do CNPJ e do Instagram
Para cada estabelecimento da Etapa 1:
- **CNPJ**: buscar pelo nome + endereço numa base gratuita construída sobre dados públicos da Receita Federal (ferramentas de busca por nome baseadas em BrasilAPI/dados abertos). Se a busca retornar mais de uma empresa plausível sem forma clara de desambiguar, ou não retornar nada, descartar o lead nesta etapa.
  - Melhoria futura (não obrigatória na v1): baixar a base de dados abertos da Receita Federal e indexar localmente por nome, eliminando a dependência de terceiros.
- **@Instagram**: tentar nesta ordem, até achar algo — (1) campo "site" retornado pelo Google Maps, se apontar para um perfil do Instagram; (2) busca complementar por "`<nome do estabelecimento>` instagram"; (3) se nada for encontrado, deixar em branco — isso não impede a qualificação do lead.
- Saída: nome, CNPJ, @Instagram (ou vazio), segmento (herdado da Etapa 1).

## Etapa 3 — Verificação de Licenças (Portal SEUMA)
**Portal**: https://portal.seuma.fortaleza.ce.gov.br/fortalezaonline/portal/portaltransparencia.jsf — consulta pública, sem login.

Para cada CNPJ vindo da Etapa 2:
1. Acessar o portal e usar a aba **"Empresa"** da busca (não "Endereço"), pesquisando pelo CNPJ. Se não retornar resultado, tentar pela razão social/nome do estabelecimento.
2. Extrair da tabela de resultado, para cada licença listada: tipo/sigla e data de validade (ou status textual, se não vier como data estruturada).
3. Comparar a data de validade com a data atual: **licença vencida = data de validade anterior a hoje** (sem período de carência).
4. Cruzar as licenças encontradas com o checklist de licenças exigidas para o segmento do estabelecimento (tabela abaixo) e marcar como **ausente** qualquer licença exigida que não apareça no resultado.
5. Se a busca ficar ambígua (mais de uma empresa sem forma clara de identificar a correta) ou não retornar nada, **descartar o lead** — não adicionar à prospecção nem tentar adivinhar.
6. Um lead só é qualificado se tiver pelo menos uma licença marcada com ✅ na tabela (forte possibilidade de demanda) vencida ou ausente.

**Restrições técnicas do portal**:
- É um sistema JSF: formulários funcionam por postback/AJAX com sessão (`jsessionid`) e ViewState, que muda a cada interação — requisições HTTP diretas não são confiáveis. Implementar com navegador headless (Playwright ou Selenium): abrir a página, clicar na aba "Empresa", preencher a busca, aguardar o carregamento assíncrono e extrair os dados renderizados.
- Tratar "Sessão Expirada": ao encontrar essa mensagem, reabrir a sessão/página e tentar de novo antes de desistir do CNPJ.
- Adicionar intervalo entre consultas consecutivas, para não sobrecarregar um portal público de prefeitura.

## Tabela de segmentos e licenças exigidas
(✅ = forte possibilidade de demanda; ⚠️ = depende da atividade, estrutura ou situação do estabelecimento)

| Segmento | AF | AS | CCB | LAR | LPP | LS | MBP | POP | PGRS/PGRSS | Outorga |
|---|---|---|---|---|---|---|---|---|---|---|
| Restaurantes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Clínicas odontológicas | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Clínicas veterinárias | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Escolas | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Indústrias | ✅ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ |
| Hotéis/pousadas | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Farmácias | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| Laboratórios | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Salões/estética | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| Academias | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| Supermercados | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Padarias | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Oficinas mecânicas | ✅ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ |
| Construtoras | ✅ | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ |

**Mapeamento para "serviço"**: quando uma licença aparecer vencida ou ausente, reportar tanto a sigla (ex.: "LS") quanto o nome comercial do serviço correspondente. O nome comercial de cada sigla deve vir de uma tabela de configuração separada, a ser fornecida por quem estiver rodando o sistema (ainda não definida nesta versão).

## Etapa 4 — Painel (Dashboard)
- Painel simples, atualizado diariamente, mostrando os leads qualificados do dia: nome, CNPJ, @Instagram, licenças pendentes (sigla + nome do serviço), segmento.
- Guardar histórico de leads já entregues: não repetir o mesmo CNPJ em dias diferentes, a menos que o status de alguma licença tenha mudado desde a última entrega.
- Não precisa de infraestrutura paga — pode ser uma página web simples lendo de um banco local (ex.: SQLite) atualizado pelas Etapas 1–3.

## Execução diária e hospedagem
- O sistema inteiro é código independente: não precisa de nenhuma IA para rodar depois de pronto (a IA só é usada para construí-lo).
- Agendar a execução das Etapas 1–4 uma vez por dia (cron job, Task Scheduler, ou equivalente) em qualquer máquina com Python/Node.js e navegador headless instalado — computador próprio ligado ou servidor/VPS de baixo custo.
- O painel pode, opcionalmente, ficar hospedado separado (ex.: hospedagem estática gratuita), lendo os dados que as Etapas 1–3 atualizam.

## Premissas assumidas nesta primeira versão (ajustar se necessário)
- Maps: API oficial do Google Places (Essentials), não scraping direto.
- CNPJ: ferramenta de busca por nome baseada em dados abertos da Receita Federal (upgrade futuro: indexação local da base completa).
- Mapeamento estabelecimento → segmento: usa o tipo informado no input diário, não a categoria do Maps.
- Campo "serviços": sigla + nome comercial (nome comercial vem de tabela de configuração a ser fornecida).
- "Vencida" = data de validade anterior à data atual, sem carência.
- Dedup: CNPJ já entregue não repete em dias seguintes, salvo mudança de status de licença.
- Nenhum segmento fixado como piloto — o sistema aceita qualquer um dos 14 da tabela desde o início.
