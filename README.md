# FourPC

Simulador de montagem de PC feito em Python, que roda no terminal.

Fiz esse projeto pra praticar Python e lógica de programação. Quem vai montar o primeiro PC costuma ter várias dúvidas: esse processador encaixa nessa placa-mãe? Essa memória é compatível? Essa fonte aguenta a placa de vídeo?

No FourPC você escolhe as peças de um catálogo e o programa vai avisando quando alguma coisa não combina. No final ele mostra o orçamento com o preço total e salva em um arquivo TXT, JSON ou CSV.

## O que ele faz

- Mostra um catálogo com 48 peças (processadores, placas-mãe, memórias, placas de vídeo, fontes, SSDs/HDs e gabinetes)
- Dá pra escolher e trocar as peças em qualquer ordem
- Também dá pra remover a peça de uma categoria: quando já tem uma escolhida, a lista ganha a opção "Remover peça atual"
- As opções de cada categoria aparecem do mais barato pro mais caro
- Quando a categoria já tem uma peça escolhida, cada opção mostra a diferença de preço em relação a ela (ex.: `+R$ 300,00` ou `-R$ 150,00`)
- Na lista de peças, as que não combinam com o que você já escolheu aparecem marcadas com `[!]`
- Se você escolher uma peça incompatível mesmo assim, aparece um alerta explicando o problema
- Algumas coisas não são erro, só um aviso: elas aparecem como `[AVISO]` no resumo, mas não impedem de finalizar (ex.: memória com menos de 16 GB ou HD como disco principal)
- Mostra um resumo da montagem com o total em R$ e o consumo de energia
- Abaixo do total aparece o preço à vista no PIX (com 10% de desconto) e o valor de cada parcela em 10x sem juros, tanto no resumo quanto no TXT, no JSON e no CSV
- Dá pra definir um orçamento máximo em R$ (opção `10` do menu). Se o total passar do limite, aparece um aviso no menu e no resumo dizendo quanto passou (ex.: `[!] O total passou do orçamento de R$ 5.000,00 em R$ 400,00.`). É só um aviso, não impede de finalizar
- No resumo de energia também aparece a folga da fonte, que é quanto da potência dela fica sobrando (ex.: `Folga da fonte: 34%`)
- Só deixa finalizar quando todas as peças foram escolhidas e está tudo compatível
- Salva o orçamento em `.txt`, `.json` e/ou `.csv` na pasta `reports/` (no final dá pra escolher um formato só ou todos de uma vez)
- Dá pra carregar de volta uma montagem a partir de um orçamento `.json` salvo antes (opção `11` do menu). As peças vêm do catálogo atual, então o preço já aparece atualizado. Se alguma peça do arquivo não existir mais no catálogo, o programa avisa quais foram e deixa essa categoria vazia pra você escolher outra
- Tem 3 montagens prontas sugeridas (Básica, Intermediária e Avançada) pra quem não sabe por onde começar (opção `12` do menu). Elas ficam no `data/presets.json` e aparecem com o preço total já calculado. Depois de carregar dá pra trocar qualquer peça normalmente
- No terminal as etiquetas aparecem coloridas: `[ OK ]` em verde, `[ERRO]` e `[!]` em vermelho e `[AVISO]` e `[i]` em amarelo. A cor só é usada quando a saída é um terminal mesmo (se mandar pra um arquivo ou pipe, sai sem cor) e o orçamento TXT salvo nunca tem cor
- Dá pra ver a lista dos orçamentos já salvos na pasta `reports/` (opção `13` do menu), do mais novo pro mais antigo. Os arquivos TXT, JSON e CSV gerados juntos aparecem numa linha só, com a data, os formatos e o total (lido do JSON). Digitando o número, a montagem é carregada de volta (só funciona se aquele orçamento tiver o `.json`)

## Regras de compatibilidade

| Regra | Como funciona |
|-------|---------------|
| Soquete | O soquete do processador tem que ser igual ao da placa-mãe (ex.: AM5 com AM5) |
| Memória RAM | A memória tem que ser do mesmo tipo que a placa-mãe aceita (DDR4 ou DDR5) |
| Fonte | A potência da fonte tem que ser maior ou igual ao consumo do processador + placa de vídeo, com 20% de margem |
| Formato | O formato da placa-mãe (ATX, mATX ou ITX) tem que estar na lista de formatos que o gabinete aceita |

Também tem os avisos, que não bloqueiam a montagem, só chamam atenção pra algo que pode ser melhorado:

| Aviso | Como funciona |
|-------|---------------|
| Quantidade de RAM | Com menos de 16 GB de memória o PC funciona, mas pode ficar lento em jogos e com muitos programas abertos |
| Tipo de armazenamento | Se o disco principal for um HD (e não um SSD), o sistema fica mais lento pra ligar e abrir programas. O HD é melhor pra guardar arquivos |

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

Por padrão ele usa o catálogo `data/catalog.json`, mas dá pra passar outro arquivo com o mesmo formato usando `--catalogo`:

```bash
python main.py --catalogo meu_catalogo.json
```

Se o arquivo não existir ou estiver com algum problema, o programa mostra o erro e nem abre o menu. O `python main.py --help` lista as opções.

Se preferir sem cores, é só definir a variável de ambiente `NO_COLOR` (segui a convenção do [no-color.org](https://no-color.org)):

```bash
NO_COLOR=1 python main.py
```

No PowerShell: `$env:NO_COLOR = "1"; python main.py`.

### Usando o menu

- `1` a `7`: escolhe a peça de cada categoria
- `8`: mostra o resumo com os preços e a compatibilidade
- `9`: finaliza e salva o orçamento
- `10`: define o orçamento máximo (aceita `5000`, `5.000,00` etc.; deixando vazio tira o limite)
- `11`: carrega um orçamento `.json` salvo (pode digitar o caminho completo ou só o nome do arquivo que está em `reports/`)
- `12`: mostra as montagens prontas sugeridas e carrega a que você escolher
- `13`: lista os orçamentos salvos em `reports/` e deixa carregar um deles
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
   1) Gigabyte B550M Aorus Elite      AM4 · DDR4 · mATX        R$ 799,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   2) MSI PRO B760M-A DDR4            LGA1700 · DDR4 · mATX    R$ 899,90
      [!] Incompatível: Soquete CPU x Placa-Mãe
   3) ASRock B650M Pro RS             AM5 · DDR5 · mATX      R$ 1.099,90
   4) MSI MAG B650 Tomahawk WiFi      AM5 · DDR5 · ATX       R$ 1.699,90
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
                AM5 · DDR5 · mATX
Memória RAM     Corsair Vengeance 2x16GB 6000MHz               R$ 799,90
                DDR5 · 32 GB
Placa de Vídeo  AMD Radeon RX 9070 XT 16GB                   R$ 4.999,90
                304 W
Fonte           MSI MAG A650BN 80+ Bronze                      R$ 379,90
                650 W
Armazenamento   WD Black SN770 1TB                             R$ 499,90
                SSD NVMe · 1 TB
Gabinete        Lian Li Lancool 216                            R$ 599,90
                ATX, mATX, ITX
------------------------------------------------------------------------
TOTAL                                                       R$ 10.979,30
À vista no PIX  (10% de desconto)                            R$ 9.881,37
Ou parcelado    10x sem juros de                             R$ 1.097,93

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
  [ OK ] Formato da Placa-Mãe x Gabinete
         O gabinete aceita placas-mãe mATX.
  [ OK ] Quantidade de Memória RAM
         32 GB de memória é suficiente para o uso comum e jogos.
  [ OK ] Tipo de Armazenamento
         O disco principal é um SSD NVMe, bom para o sistema ficar
         rápido.

========================================================================
Status: Montagem completa e compatível. Pronta para compra!
Preços e consumos são estimativas para fins de simulação.
========================================================================
```

O `.json` tem as mesmas informações, só que organizadas pra ser lidas por outro programa.

Já o `.csv` é pra abrir numa planilha (Excel, LibreOffice ou Google Planilhas). Ele tem uma linha por peça e, no final, o total, o preço no PIX e o valor da parcela. Usei `;` como separador e vírgula nos centavos porque é assim que o Excel em português espera:

```text
Categoria;Peça;Especificações;Preço (R$)
Processador;AMD Ryzen 7 7800X3D;AM5 · 120 W;2599,90
Placa-Mãe;ASRock B650M Pro RS;AM5 · DDR5 · mATX;1099,90
...
Gabinete;Lian Li Lancool 216;ATX, mATX, ITX;599,90
Total;;;10979,30
À vista no PIX;;10% de desconto;9881,37
Parcelado;;10x sem juros de;1097,93
```

## Estrutura do projeto

```text
FourPC/
├── main.py              # menu e interação com o usuário
├── core/
│   ├── models.py        # classes das peças e da montagem
│   ├── catalog.py       # lê o catálogo de peças do JSON
│   ├── validators.py    # regras de compatibilidade
│   ├── pricing.py       # PIX, parcelamento e orçamento máximo
│   ├── report.py        # resumo, formatação em R$ e exportação
│   ├── colors.py        # cores das etiquetas no terminal
│   ├── saved_build.py   # carrega uma montagem de um orçamento JSON
│   ├── saved_reports.py # lista os orçamentos salvos em reports/
│   └── presets.py       # lê as montagens prontas sugeridas
├── data/
│   ├── catalog.json     # catálogo de peças
│   └── presets.json     # montagens prontas (Básica, Intermediária...)
└── tests/               # testes
```

Pra adicionar uma peça nova é só colocar ela no `data/catalog.json`, seguindo o formato das outras da mesma categoria. As placas-mãe têm o campo `form_factor` (`ATX`, `mATX` ou `ITX`) e os gabinetes têm a lista `supported_form_factors` com os formatos de placa que cabem neles.

As montagens prontas usam só os IDs das peças do catálogo, uma por categoria. Tem um teste que confere se todas estão completas e sem nenhuma incompatibilidade, então se alguém mudar o catálogo e quebrar uma delas, o teste avisa.

## O que eu aprendi

- Separar a lógica do programa (pasta `core/`) da parte que conversa com o usuário (`main.py`)
- Usar `dataclasses` e `Enum` pra organizar os dados das peças
- Não usar `float` pra dinheiro: com float, `0.1 + 0.2` dá `0.30000000000000004`. Por isso usei `Decimal` nos preços e no cálculo da fonte
- Ler e validar um arquivo JSON
- Escrever testes com `unittest`, inclusive simulando alguém usando o menu

## Ideias pra melhorar

- Permitir mais de um SSD/HD na mesma montagem
- Fazer uma versão com interface gráfica ou web

## Autor

Feito por [Fournier-dev](https://github.com/Fournier-dev).

Obs.: os preços e consumos das peças são aproximados, servem só pra simulação.
