# morfocampo

`morfocampo` e um MVP em C++20 para reduzir digitacao em campo, interpretando fala estruturada ja transcrita como texto e convertendo esses comandos em registros de morfometria de arvores.

O problema inicial e simples: escrever ou digitar medidas durante a coleta aumenta risco de erro, retrabalho e perda de rastreabilidade. Este MVP nao grava audio e nao transcreve audio; ele assume que a fala ja chegou como texto curto e padronizado, entao interpreta, normaliza, valida e exporta dados auditaveis.

## Escopo do MVP

- Interpretar frases curtas de fala estruturada ja transcrita.
- Preservar a frase original em `raw_input`.
- Marcar origem em `source` e confianca em `confidence_flag`.
- Gerar template CSV de coleta.
- Gerar pacote de campanha com planilha digital CSV e listas de apoio.
- Ler CSV preenchido.
- Normalizar textos, condicoes e numeros com virgula ou ponto decimal.
- Calcular DAP a partir de CAP, ou CAP a partir de DAP.
- Validar regras explicitas de campos obrigatorios, faixas numericas, datas ISO e duplicidades.
- Exportar CSV normalizado e JSONL.
- Gerar relatorio Markdown de validacao.
- Converter transcricoes de texto controladas para CSV intermediario com regex.

## Fora do MVP

Este MVP nao implementa app mobile, interface grafica, banco remoto, IA, API externa, gravacao de audio, leitura direta de audio, Whisper ou transcricao automatica. A arquitetura deixa espaco para integrar `whisper.cpp`, Vosk, ODK, KoboToolbox, QField ou app mobile depois.

## Aceita audio?

Nao. O MVP atual nao recebe `.wav`, `.mp3`, microfone ou qualquer arquivo de som.

Ele recebe texto que representa uma fala ja transcrita:

```text
arvore A-023 CAP 42,5 altura total 4,8 condicao viva
```

O fluxo atual e:

```text
fala em campo -> transcricao por outro sistema -> morfocampo parse-voice -> CSV -> validate -> relatorio
```

O fluxo futuro pode ser:

```text
audio -> whisper.cpp/Vosk/app mobile -> texto -> morfocampo
```

Essa separacao e proposital: o nucleo C++ fica pequeno, auditavel e testavel antes de acoplar reconhecimento de voz.

## Compilar e testar

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## Uso

Gerar exemplos:

```sh
./build/morfocampo init --dir examples
```

Gerar uma planilha digital de campanha:

```sh
./build/morfocampo init-campaign \
  --dir campo_C01 \
  --project MORFO_CAMPO_2026 \
  --campaign C01 \
  --area "Butiazal Sao Miguel" \
  --plots P01,P02,P03 \
  --observers Pedro,Ana,Carla \
  --rows 50
```

Esse comando gera:

- `campo_C01/coleta_arvores.csv`
- `campo_C01/protocolo_campo.md`
- `campo_C01/README_PLANILHA.md`
- `campo_C01/listas/condicoes.csv`
- `campo_C01/listas/parcelas.csv`
- `campo_C01/listas/observadores.csv`

`coleta_arvores.csv` e a planilha digital simples para abrir no LibreOffice, Excel, Google Sheets, OnlyOffice ou editor CSV em celular/tablet. Ela nao usa macros. A validacao oficial continua sendo o comando `validate`.

Validar CSV:

```sh
./build/morfocampo validate --input examples/template_arvores.csv --out out
```

Converter fala estruturada ja transcrita:

```sh
./build/morfocampo parse-voice --input examples/fala_estruturada.txt --out out/dados_por_voz.csv
./build/morfocampo validate --input out/dados_por_voz.csv --out out
```

Sessao interativa simples:

```sh
./build/morfocampo session \
  --project MORFO_2026 \
  --campaign C01 \
  --plot P01 \
  --observer Pedro \
  --date 2026-07-01 \
  --out sessao_voz.csv
```

Na sessao, digite frases como:

```text
arvore A-023 CAP 42,5 altura total 4,8 condicao viva
```

Saidas geradas:

- `out/arvores_normalizadas.csv`
- `out/arvores_normalizadas.jsonl`
- `out/relatorio_validacao.md`

Converter transcricoes controladas:

```sh
./build/morfocampo parse-transcript --input examples/transcricoes_exemplo.txt --out out/transcricao_convertida.csv
```

Ajuda:

```sh
./build/morfocampo help
```

## Formato do CSV

Colunas esperadas:

```text
project_id,campaign_id,area,plot,transect,tree_id,species,cap_cm,dap_cm,total_height_m,crown_height_m,crown_diameter_ns_m,crown_diameter_ew_m,condition,observer,date,latitude,longitude,notes,source,confidence_flag,raw_input
```

Campos obrigatorios:

- `project_id`
- `campaign_id`
- `plot`
- `tree_id`
- `observer`
- `date`

Pelo menos um entre `cap_cm` e `dap_cm` deve estar preenchido. Numeros podem usar virgula decimal (`42,5`) ou ponto decimal (`42.5`). A data deve estar em ISO `YYYY-MM-DD`.

Condicoes aceitas:

- `viva`
- `morta`
- `rebrote`
- `dano`
- `desconhecida`

Duplicidade e detectada pela chave:

```text
project_id + campaign_id + plot + tree_id
```

## JSONL

O JSONL inclui `cap_source` e `dap_source` com os valores:

- `observed`: valor informado no CSV ou na transcricao.
- `derived`: valor calculado pelo `morfocampo`.
- `missing`: valor ausente.

## Parser de transcricoes

O comando principal para fala estruturada e `parse-voice`. Ele e deterministico, usa apenas regex e depende de fala padronizada. O comando antigo `parse-transcript` permanece como alias compativel.

Exemplo:

```text
arvore A-023; especie Butia odorata; CAP 42,5 cm; altura total 4,8 m; altura da copa 2,1 m; copa norte-sul 3,4 m; copa leste-oeste 2,9 m; condicao viva; observador Pedro
```

Sinonimos reconhecidos incluem `CAP`, `circunferencia`, `DAP`, `diametro`, `altura`, `altura total`, `copa ns`, `copa norte-sul`, `copa ew`, `copa leste-oeste` e `copa leste oeste`.

O CSV gerado deve passar pelo fluxo principal de validacao.

## Fluxo de campo recomendado

1. Antes da saida, gere a campanha com `init-campaign`.
2. Abra `coleta_arvores.csv` em uma planilha digital.
3. Use as listas em `listas/` como apoio para menus suspensos quando o aplicativo permitir.
4. Preencha os dados em campo.
5. No intervalo ou fim do dia, rode `validate`.
6. Corrija erros ainda no campo quando possivel.

Exemplo:

```sh
./build/morfocampo validate --input campo_C01/coleta_arvores.csv --out campo_C01/validacao
```

## Estrutura

```text
CMakeLists.txt
include/morfocampo/
src/
tests/
examples/
```

## Proximos passos possiveis

- Integracao com ODK/Kobo via XLSForm.
- Integracao com QField/QGIS.
- Persistencia em SQLite.
- Interface grafica.
- App mobile.
- Leitura direta de audio.
- Transcricao automatica com Whisper ou outra ferramenta.
- Integracao futura com SisTer/SAMA-D.
- Geracao de protocolos de campo versionados.
