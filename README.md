# morfocampo

`morfocampo` e um sistema de coleta de dados morfometricos de arvores para uso em campo, composto de:

- **Nucleo C++20** (`src/`, `include/`) — interpreta fala estruturada transcrita, normaliza, valida e exporta CSV/JSONL. Auditavel, testavel, sem dependencias externas.
- **Interface web** (`web/`) — SPA mobile-first com gravacao de audio, transcricao local (Whisper), persistencia em SQLite3 e painel de administracao via browser.

O papel continua como base documental fisica de referencia. A interface digital complementa e acelera o registro sem substituir o protocolo em papel.

## Escopo atual

- Interpretar frases curtas de fala estruturada ja transcrita.
- Preservar a frase original em `raw_input`; marcar origem em `source` e confianca em `confidence_flag`.
- Gerar pacote de campanha com planilha digital CSV e listas de apoio.
- Normalizar textos, condicoes e numeros com virgula ou ponto decimal.
- Calcular DAP a partir de CAP, ou CAP a partir de DAP.
- Validar regras explicitas de campos obrigatorios, faixas numericas, datas ISO e duplicidades.
- Exportar CSV normalizado e JSONL.
- Gerar relatorio Markdown de validacao.
- **Interface web mobile**: gravar audio → transcrever → interpretar → confirmar → SQLite3.
- **Registros exclusivos por observador** na coleta; validacao consolidada por campanha.
- **Painel de administracao web**: visao de todos os observadores, flags de confianca, validar e exportar.

## Fora do escopo atual

Integracao nativa com ODK/Kobo, QField/QGIS, app mobile nativo, banco remoto, autenticacao multiusuario. A arquitetura deixa espaco para integrar `whisper.cpp`, Vosk, ODK, KoboToolbox, QField ou app mobile depois.

## Fluxos de coleta

### Fluxo CLI (texto transcrito)

```text
fala em campo -> transcricao manual -> morfocampo parse-voice -> CSV -> validate -> relatorio
```

### Fluxo Web (audio direto no celular)

```text
celular: microfone -> Web Speech API (online) -> texto
                   -> blob audio -> servidor -> Whisper (offline)
                                    -> morfocampo C++ -> interpretar -> confirmar -> SQLite3
```

A separacao nucleo C++ / interface e proposital: o nucleo fica auditavel e testavel independente de como os dados chegam.

## Interface Web — rodar e administrar via browser

### Iniciar o servidor

```sh
cd web
pip install -r requirements.txt

python server.py \
  --db campo.db \
  --bin ../build/morfocampo \
  --port 8000
```

### Acessar no celular

O celular deve estar na mesma rede WiFi do notebook (ou USB tethering):

```sh
# Descobrir o IP do notebook:
ip addr show | grep "inet " | grep -v 127.0.0.1

# Abrir no celular:
http://<IP-do-notebook>:8000
```

### Telas disponíveis

| Tela | Acesso | Função |
|---|---|---|
| **Home** | `/` raiz | Lista campanhas; criar nova campanha |
| **Coleta** | botao Coletar | Gravar audio, interpretar, confirmar — registros exclusivos por observador |
| **Registros** | aba Registros | Lista e corrige registros do observador atual |
| **Validar** | aba Validar | Valida todos os observadores da campanha; exporta ZIP |
| **⚙ Admin** | botao Admin | Visao consolidada: todos os observadores, flags, validar, exportar, excluir |

### Painel de administracao (`⚙ Admin`)

Acessivel na tela inicial ao lado de cada campanha. Mostra:

- Total de registros e distribuicao de flags (OK / Revisar / Incompleto / Erro)
- Registros agrupados por observador (expandiveis)
- Ultima validacao (data, erros, avisos)
- Botoes: **Validar campanha** (todos os observadores) e **Exportar ZIP** (CSV + relatorio)

### Transcrição de audio

| Situacao | Motor | Requisito |
|---|---|---|
| Com internet | Web Speech API (browser, tempo real) | Nenhum |
| Sem internet | faster-whisper no servidor | `pip install faster-whisper` |
| Sem microfone | Digitacao manual na tela | — |

Para transcrição offline (campo remoto sem internet):

```sh
pip install faster-whisper
# Modelo 'small' (~460 MB) baixado automaticamente na primeira transcricao
```

### Documentação interativa da API

```
http://localhost:8000/docs
```


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

Validar com limites de faixa configuraveis (avisos, nao erros):

```sh
./build/morfocampo validate \
  --input out/dados_por_voz.csv \
  --out out \
  --max-cap 600 \
  --max-dap 200 \
  --max-height 30 \
  --max-crown 20
```

Sessao interativa simples:

```sh
./build/morfocampo session \
  --project MORFO_2026 \
  --campaign C01 \
  --plot P01 \
  --observer Pedro \
  --date 2026-07-01 \
  --out sessao_voz.csv \
  --max-cap 600 \
  --max-height 30
```

Na sessao, digite frases como:

```text
arvore A-023 CAP 42,5 altura total 4,8 condicao viva
```

Para corrigir um registro ja confirmado na mesma sessao, prefixe com `corrigir`:

```text
corrigir arvore A-023 CAP 43,0
```

O sistema localiza o registro com o mesmo `tree_id` e o substitui. Se a arvore nao foi registrada ainda na sessao, adiciona como novo registro com aviso.

Saidas geradas:

- `out/arvores_normalizadas.csv`
- `out/arvores_normalizadas.jsonl`
- `out/relatorio_validacao.md` (inclui secao **Registros para revisar**)

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

## Limitacoes do parser de voz

O parser e deterministico e usa regex. Ele funciona bem para fala estruturada e padronizada, mas **falha silenciosamente** em varios padroes naturais da fala. Treine os observadores para usar o protocolo abaixo.

### O que o parser reconhece

```text
arvore A-023 CAP 42,5 altura total 4,8 condicao viva
arvore A-023; especie Butia odorata; CAP 42,5 cm; condicao viva
nova arvore A-023 DAP 13,5
corrigir arvore A-023 CAP 43,0
```

- Numeros com virgula (`42,5`) ou ponto decimal (`42.5`).
- Palavras-chave em qualquer ordem, separadas por espaco ou ponto-e-virgula.
- Prefixo `nova`, `novo`, `salvar` (ignorados).
- Prefixo `corrigir` (substitui registro com mesmo `tree_id` na sessao).

### O que o parser NAO reconhece (limitacoes conhecidas)

```text
# Numero por extenso — NAO funciona
a arvore tem quarenta e dois de CAP

# Ordem das palavras sem palavra-chave — NAO funciona
42,5 e a circunferencia da arvore 023

# Fracao oral — NAO funciona
CAP quarenta e dois e meio

# Identificador com espaco — NAO funciona
arvore A 023 (use A-023 ou A023)

# Condicao com acento nao mapeado — cuidado
condição abatida (nao esta na lista controlada)
```

### Protocolo de fala recomendado para treinamento de observadores

1. Sempre identifique a arvore primeiro: `arvore [ID]`
2. Informe CAP ou DAP com numero: `CAP 42,5` ou `DAP 13,4`
3. Use virgula ou ponto decimal, nunca por extenso.
4. Informe condicao com uma das palavras controladas: `viva`, `morta`, `rebrote`, `dano`, `desconhecida`.
5. Para corrigir: `corrigir arvore [ID] [campo] [valor]`
6. Fale devagar e com pausas entre os campos.

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
