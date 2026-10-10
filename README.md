# FourPC

Simulador de montagem de PC feito em Python, que roda no terminal.

Fiz esse projeto pra praticar Python e lógica de programação. Quem vai montar o primeiro PC costuma ter várias dúvidas: esse processador encaixa nessa placa-mãe? Essa memória é compatível? Essa fonte aguenta a placa de vídeo?

No FourPC você escolhe as peças de um catálogo e o programa vai avisando quando alguma coisa não combina. No final ele mostra o orçamento com o preço total e salva em um arquivo TXT ou JSON.

## O que ele faz

- Mostra um catálogo com 41 peças (processadores, placas-mãe, memórias, placas de vídeo, fontes, SSDs/HDs e gabinetes)
- Dá pra escolher e trocar as peças em qualquer ordem
- Também dá pra remover a peça de uma categoria: quando já tem uma escolhida, a lista ganha a opção "Remover peça atual"
- As opções de cada categoria aparecem do mais barato pro mais caro
- Quando a categoria já tem uma peça escolhida, cada opção mostra a diferença de preço em relação a ela (ex.: `+R$ 300,00` ou `-R$ 150,00`)
- Na lista de peças, as que não combinam com o que você já escolheu aparecem marcadas com `[!]`
- Se você escolher uma peça incompatível mesmo assim, aparece um alerta explicando o problema
- Mostra um resumo da montagem com o total em R$ e o consumo de energia
- No resumo de energia também aparece a folga da fonte, que é quanto da potência dela fica sobrando (ex.: `Folga da fonte: 34%`)
- Só deixa finalizar quando todas as peças foram escolhidas e está tudo compatível
- Salva o orçamento em `.txt` e/ou `.json` na pasta `reports/`

## Regras de compatibilidade

| Regra | Como funciona |
|-------|---------------|
| Soquete | O soquete do processador tem que ser igual ao da placa-mãe (ex.: AM5 com AM5) |
| Memória RAM | A memória tem que ser do mesmo tipo que a placa-mãe aceita (DDR4 ou DDR5) |
| Fonte | A potência da fonte tem que ser maior ou igual ao consumo do processador + placa de vídeo, com 20% de margem |

Exemplo da regra da fonte: um Ryzen 7 7800X3D (120 W) com uma RX 9070 XT (304 W) consome 424 W. Somando 20% de margem dá 508,8 W, então a fonte precisa ter pelo menos 509 W. Uma fonte de 450 W não passa.

## Como rodar

Precisa ter o Python 3.10 ou mais novo instalado. Não precisa instalar nenhuma biblioteca, o projeto só usa o que já vem com o Python.

1. Clone o repositório:

```bash
git clone https://github.com/Fournier-dev/FourPC.git
```

2. Entre na pasta do projeto:

```bash
cd FourPC
```

3. Rode o programa:

```bash
python main.py
```

No Windows, se o comando `python` não funcionar, tente `py main.py`.

### Usando o menu

- `1` a `7`: escolhe a peça de cada categoria
- `8`: mostra o resumo com os preços e a compatibilidade
- `9`: finaliza e salva o orçamento
- `0`: sai do programa

### Testes

Também fiz alguns testes com o `unittest` pra conferir as regras, os preços e o menu. Pra rodar:

```bash
python -m unittest
```

## Como ficou

Depois de escolher um processador AM5, as placas-mãe de outro soquete aparecem marcadas na lista:

```text
------------------------------------------------------------------------
PLACA-MÃE - escolha uma opção
------------------------------------------------------------------------
   1) Gigabyte B550M Aorus Elite           AM4 · DDR4          R$ 799,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   2) MSI PRO B760M-A DDR4                 LGA1700 · DDR4      R$ 899,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   3) ASRock B650M Pro RS                  AM5 · DDR5        R$ 1.099,90
   4) MSI MAG B650 Tomahawk WiFi           AM5 · DDR5        R$ 1.699,90
   ...
   0) Voltar
```

Se escolher uma delas mesmo assim, aparece o alerta:

```text
ALERTA DE COMPATIBILIDADE
  [ERRO] Soquete CPU x Placa-Mãe
         O processador AMD Ryzen 7 7800X3D usa o soquete AM5, mas a
         placa-mãe Gigabyte B550M Aorus Elite é AM4.
         Sugestão: escolha uma placa-mãe AM5 ou um processador AM4.
```

E o mesmo acontece com a fonte:

```text
ALERTA DE COMPATIBILIDADE
  [ERRO] Dimensionamento da Fonte
         A fonte Corsair CV450 80+ Bronze (450 W) é insuficiente: CPU
         (120 W) + GPU (304 W) + 20% de margem exigem 509 W.
         Sugestão: escolha uma fonte de pelo menos 509 W.
```

## Exemplo de orçamento gerado

Esse é o arquivo `.txt` que o programa salva na pasta `reports/`:

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
  Folga da fonte                                                     34%

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

O `.json` tem as mesmas informações, só que organizadas pra ser lidas por outro programa.

## Estrutura do projeto

```text
FourPC/
├── main.py              # menu e interação com o usuário
├── core/
│   ├── models.py        # classes das peças e da montagem
│   ├── catalog.py       # lê o catálogo de peças do JSON
│   ├── validators.py    # regras de compatibilidade
│   └── report.py        # resumo, formatação em R$ e exportação
├── data/
│   └── catalog.json     # catálogo de peças
└── tests/               # testes
```

Pra adicionar uma peça nova é só colocar ela no `data/catalog.json`, seguindo o formato das outras da mesma categoria.

## O que eu aprendi

- Separar a lógica do programa (pasta `core/`) da parte que conversa com o usuário (`main.py`)
- Usar `dataclasses` e `Enum` pra organizar os dados das peças
- Não usar `float` pra dinheiro: com float, `0.1 + 0.2` dá `0.30000000000000004`. Por isso usei `Decimal` nos preços e no cálculo da fonte
- Ler e validar um arquivo JSON
- Escrever testes com `unittest`, inclusive simulando alguém usando o menu

## Ideias pra melhorar

- Verificar se a placa-mãe cabe no gabinete (ATX, mATX, ITX)
- Permitir mais de um SSD/HD na mesma montagem
- Fazer uma versão com interface gráfica ou web

## Autor

Feito por [Fournier-dev](https://github.com/Fournier-dev).

Obs.: os preços e consumos das peças são aproximados, servem só pra simulação.
