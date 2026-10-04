# FourPC — Simulador de Montagem de PC

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-brightgreen)
![Tipagem](https://img.shields.io/badge/tipagem-mypy%20--strict-informational)
![Estilo](https://img.shields.io/badge/estilo-PEP%208-informational)

Aplicação de linha de comando (CLI) em Python que permite montar um computador
escolhendo peças de um catálogo, **valida automaticamente a compatibilidade
entre os componentes** e gera um orçamento final em R$, exportável em TXT ou JSON.

## O problema

Quem monta o próprio PC pela primeira vez costuma cometer erros caros:

- comprar um processador AM5 para uma placa-mãe AM4 (o processador não encaixa);
- comprar memória DDR5 para uma placa que só aceita DDR4;
- economizar na fonte e ficar com potência insuficiente para o processador e a placa de vídeo.

O FourPC evita esses erros: ele verifica a compatibilidade **a cada peça
escolhida**, sinaliza as opções incompatíveis **antes** de o usuário
selecioná-las e só libera o orçamento final quando a montagem está completa
e sem conflitos.

## Funcionalidades

- Catálogo com 41 peças reais em 7 categorias, carregado de um arquivo JSON.
- Menu interativo para escolher (e trocar) as peças em qualquer ordem.
- Opções incompatíveis marcadas com `[!]` na listagem, antes da escolha.
- Alertas claros com o motivo do problema e uma sugestão de correção.
- Resumo detalhado com preços, consumo de energia e status de cada regra.
- Preços formatados em reais (ex.: `R$ 10.979,30`), calculados com `Decimal`.
- Exportação do orçamento em `.txt`, `.json` ou ambos, na pasta `reports/`.

## Regras de compatibilidade

| # | Regra | Peças envolvidas | Condição para aprovar | Exemplo de erro |
|---|-------|------------------|-----------------------|-----------------|
| 1 | Soquete CPU x Placa-Mãe | Processador, Placa-Mãe | `cpu.socket == placa.socket` | Ryzen 7 7800X3D (AM5) + B550M (AM4) |
| 2 | Tecnologia de RAM x Placa-Mãe | Memória RAM, Placa-Mãe | `ram.tipo == placa.tipo_ram` (DDR4/DDR5) | Memória DDR5 + placa B760M DDR4 |
| 3 | Dimensionamento da Fonte | Processador, Placa de Vídeo, Fonte | `fonte ≥ (TDP da CPU + consumo da GPU) × 1,20` | 120 W + 304 W = 424 W → exige 509 W; fonte de 450 W reprovada |

Cada regra tem três estados possíveis: **`[ OK ]`** aprovada, **`[ERRO]`**
violada e **`[ -- ]`** pendente (ainda faltam peças para avaliar). O resultado
da regra 3 é arredondado para cima (`361,2 W` → `362 W`).

## Como executar

**Pré-requisito:** Python 3.10 ou superior. Não há dependências externas — apenas
a biblioteca padrão (`json`, `pathlib`, `dataclasses`, `decimal`, `typing`...).

```bash
# 1. Clone o repositório
git clone https://github.com/Fournier-dev/FourPC.git

# 2. Entre na pasta do projeto
cd FourPC

# 3. Execute o simulador
python main.py
```

> No Windows, se o comando `python` não for reconhecido, use `py main.py`.

Para rodar os testes automatizados:

```bash
python -m unittest -v
```

## Demonstração

As opções incompatíveis com as peças já escolhidas são sinalizadas na listagem:

```text
------------------------------------------------------------------------
PLACA-MÃE - escolha uma opção
------------------------------------------------------------------------
   1) Gigabyte B550M Aorus Elite           AM4 · DDR4          R$ 799,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   2) ASRock B650M Pro RS                  AM5 · DDR5        R$ 1.099,90
   3) MSI MAG B650 Tomahawk WiFi           AM5 · DDR5        R$ 1.699,90
   4) MSI PRO B760M-A DDR4                 LGA1700 · DDR4      R$ 899,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   ...
   0) Voltar
```

Se o usuário escolher mesmo assim, o alerta explica o problema e sugere a correção:

```text
ALERTA DE COMPATIBILIDADE
  [ERRO] Soquete CPU x Placa-Mãe
         O processador AMD Ryzen 7 7800X3D usa o soquete AM5, mas a
         placa-mãe Gigabyte B550M Aorus Elite é AM4.
         Sugestão: escolha uma placa-mãe AM5 ou um processador AM4.
```

```text
ALERTA DE COMPATIBILIDADE
  [ERRO] Dimensionamento da Fonte
         A fonte Corsair CV450 80+ Bronze (450 W) é insuficiente: CPU
         (120 W) + GPU (304 W) + 20% de margem exigem 509 W.
         Sugestão: escolha uma fonte de pelo menos 509 W.
```

Enquanto houver peças faltando ou incompatibilidades, a opção **Finalizar**
lista o que precisa ser corrigido e não gera o orçamento.

## Exemplo de relatório gerado

Arquivo `reports/orcamento_20261004_040801.txt`:

```text
========================================================================
                  FourPC - Orçamento de Montagem de PC
========================================================================
Gerado em 04/10/2026 às 04:08

COMPONENTES
------------------------------------------------------------------------
Processador     AMD Ryzen 7 7800X3D                          R$ 2.599,90
                AM5 · 120 W
Placa-Mãe       ASRock B650M Pro RS                          R$ 1.099,90
                AM5 · DDR5
Memória RAM     Corsair Vengeance 2x16GB 6000MHz               R$ 799,90
                DDR5 · 32 GB
Placa de Vídeo  AMD Radeon RX 9070 XT 16GB                   R$ 4.999,90
                304 W
Fonte           MSI MAG A650BN 80+ Bronze                      R$ 379,90
                650 W
Armazenamento   WD Black SN770 1TB                             R$ 499,90
                SSD NVMe · 1 TB
Gabinete        Lian Li Lancool 216                            R$ 599,90
------------------------------------------------------------------------
TOTAL                                                       R$ 10.979,30

ENERGIA
------------------------------------------------------------------------
  Consumo estimado (CPU + GPU)                                     424 W
  Fonte mínima recomendada (+20%)                                  509 W
  Fonte selecionada                                                650 W

COMPATIBILIDADE
------------------------------------------------------------------------
  [ OK ] Soquete CPU x Placa-Mãe
         Processador e placa-mãe usam o soquete AM5.
  [ OK ] Tecnologia de RAM x Placa-Mãe
         Memória e placa-mãe usam o padrão DDR5.
  [ OK ] Dimensionamento da Fonte
         A fonte de 650 W atende ao mínimo de 509 W (consumo de 424 W +
         20% de margem).

========================================================================
Status: Montagem completa e compatível. Pronta para compra!
Preços e consumos são estimativas para fins de simulação.
========================================================================
```

A versão JSON traz os mesmos dados de forma estruturada (trecho):

```json
{
  "project": "FourPC",
  "generated_at": "2026-10-04T04:08:01",
  "components": [
    {
      "category": "cpu",
      "category_label": "Processador",
      "id": "cpu-r7-7800x3d",
      "name": "AMD Ryzen 7 7800X3D",
      "price": "2599.90",
      "socket": "AM5",
      "tdp_watts": 120
    }
  ],
  "power": {
    "estimated_load_watts": 424,
    "required_psu_watts": 509,
    "psu_watts": 650
  },
  "total_price": "10979.30",
  "total_price_formatted": "R$ 10.979,30"
}
```

## Estrutura do projeto

```text
FourPC/
├── main.py              # Ponto de entrada e interface interativa (CLI)
├── core/
│   ├── models.py        # Peças (dataclasses) e a montagem (Build)
│   ├── catalog.py       # Leitura e validação do catálogo JSON
│   ├── validators.py    # Regras de compatibilidade
│   └── report.py        # Resumo, formatação em R$ e exportação TXT/JSON
├── data/
│   └── catalog.json     # Catálogo de peças
├── tests/               # Testes automatizados (unittest)
└── reports/             # Orçamentos exportados (criada automaticamente)
```

## Decisões de arquitetura

- **Lógica de negócio separada da interface.** Todo o domínio fica em `core/`
  e não usa `print` nem `input`; o `main.py` apenas orquestra a interação.
  Isso permite reaproveitar o núcleo em uma API ou interface gráfica.
- **Regras como funções puras.** Cada regra recebe uma `Build` e devolve um
  `RuleResult` (OK, ERRO ou PENDENTE). Para criar uma nova regra basta
  escrever uma função e adicioná-la à tupla `RULES` em `validators.py`.
- **Montagem imutável.** `Build.with_component()` devolve uma nova montagem.
  É assim que a CLI "simula" cada opção da lista para marcar as incompatíveis
  sem alterar a montagem real.
- **Dinheiro com `Decimal`.** Preços nunca usam `float`, evitando erros de
  arredondamento (`0.1 + 0.2 != 0.3`). O mesmo vale para o cálculo da fonte:
  com `float`, `300 * 1.2` resulta em `360.00000000000006`, o que exigiria
  uma fonte de 361 W em vez de 360 W — há um teste cobrindo esse caso.
- **Catálogo orientado a dados.** Novas peças são adicionadas só editando o
  JSON. O carregamento valida campos obrigatórios, tipos, IDs duplicados e
  padrões de RAM desconhecidos, com mensagens de erro que apontam a peça.
- **CLI testável.** As funções de entrada e saída são injetadas na
  `FourPCApp`, o que permite testes de ponta a ponta simulando o usuário.

## Qualidade de código

- Type hints em todas as funções, classes e métodos (validado com `mypy --strict`).
- Código aderente à PEP 8 (validado com `pycodestyle`).
- 59 testes automatizados cobrindo modelos, catálogo, regras, relatórios e a
  CLI — incluindo testes de integridade do próprio catálogo (todo processador
  tem ao menos uma placa-mãe compatível, por exemplo).

## Adicionando peças ao catálogo

Edite `data/catalog.json` e inclua um objeto na lista da categoria desejada.
Todos os itens têm `id` (único), `name` e `price`; os demais campos dependem
da categoria:

| Categoria (`chave`) | Campos específicos |
|---------------------|--------------------|
| Processador (`cpu`) | `socket`, `tdp_watts` |
| Placa-Mãe (`motherboard`) | `socket`, `ram_type` (`"DDR4"` ou `"DDR5"`) |
| Memória RAM (`ram`) | `ram_type`, `capacity_gb` |
| Placa de Vídeo (`gpu`) | `power_watts` |
| Fonte (`psu`) | `wattage` |
| Armazenamento (`storage`) | `kind` (ex.: `"SSD NVMe"`, `"HD"`), `capacity_gb` |
| Gabinete (`case`) | — |

```json
{"id": "cpu-r5-9600x", "name": "AMD Ryzen 5 9600X", "socket": "AM5", "tdp_watts": 65, "price": 1599.90}
```

## Próximos passos

- Compatibilidade de formato (ATX, mATX, ITX) entre placa-mãe e gabinete.
- Suporte a mais de um dispositivo de armazenamento por montagem.
- Montagens sugeridas por faixa de orçamento.
- Interface web consumindo o mesmo núcleo (`core/`).

## Autor

Desenvolvido por [Fournier-dev](https://github.com/Fournier-dev).

> Os preços e consumos do catálogo são aproximados e servem apenas para fins
> de simulação.
