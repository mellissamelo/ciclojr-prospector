# Status do sistema — 09/09/2026

## Onde estamos

- **43 de 50 leads da semana já entregues** (semana começou 07/09). No total,
  já foram 45 leads entregues desde o início e 310 CNPJs checados no Portal
  SEUMA.
- O painel (`dashboard/index.html`) já mostra esses 43 leads com nome, CNPJ e
  as licenças pendentes (na maioria: AF, LS e PGRS/PGRSS ausentes).
- A extração de dados da Receita Federal (Fortaleza + CNAE de Restaurantes,
  6.986 estabelecimentos) está pronta e não precisa ser refeita — só o
  Portal SEUMA é consultado a cada execução.

## Problema conhecido: demora

Rodar até bater os 50 leads da semana está levando **bem mais que 1 hora**
em alguns casos — o processo desta semana rodou por várias horas sem
terminar sozinho (foi interrompido pelo fim da sessão, não por erro).

Causa: o Portal SEUMA às vezes trava numa busca específica e o sistema
espera até 20 segundos, tenta de novo, espera mais 20s, e só depois desiste
e marca como "não encontrado" — isso está acontecendo com frequência
suficiente pra somar bastante tempo ao longo de milhares de CNPJs.
Isso é uma lentidão real do próprio portal da prefeitura (fora do nosso
controle), mas dá pra amenizar no código (ex.: rodar buscas em paralelo em
vez de uma de cada vez, ou reduzir o tempo de espera por tentativa).

## Pedido pra ajustar: busca por região + setor, não só "50 aleatórios"

Hoje, quando você roda sem escolher um bairro, o sistema embaralha **todos**
os 6.986 restaurantes de Fortaleza e vai checando até bater 50 — ou seja, os
50 saem meio aleatórios, espalhados pela cidade inteira.

Já existe a opção de filtrar por bairro (`rodar_hoje.bat` pergunta o bairro),
mas isso ainda não resolve completamente o que você quer. Preciso entender
melhor: você quer poder **escolher setor + bairro juntos toda vez que roda**
(isso já dá pra fazer), ou quer algo a mais — tipo rodar vários
bairros/setores em sequência numa lista, ou ver os 50 leads distribuídos
entre bairros diferentes automaticamente (cota por bairro), em vez de
escolher um bairro de cada vez?

## Próximos passos (aguardando sua confirmação)

1. Otimizar a velocidade da Etapa 3 (SEUMA) — reduzir o tempo perdido em
   buscas que travam.
2. Ajustar a lógica de seleção de leads pra region+setor conforme o que você
   definir no ponto acima.
