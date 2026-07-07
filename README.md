# Morfocampo

[![CI](https://github.com/jpereiratrindade/morfocampo/actions/workflows/ci.yml/badge.svg)](https://github.com/jpereiratrindade/morfocampo/actions/workflows/ci.yml)

`morfocampo` é uma ferramenta para coleta, normalização, importação e validação de dados morfométricos e silvipastoris em campo.

O projeto combina um núcleo C++20, usado pela CLI e pelos testes, com uma interface web mobile em Python/FastAPI para coleta em campo com SQLite, áudio e integração com o binário principal.

## Componentes

- `src/` e `include/`: núcleo C++20, parser de voz, importadores CSV, validação e relatórios.
- `tests/`: testes automatizados do núcleo.
- `examples/`: arquivos pequenos para validar fluxos de entrada e saída.
- `web/`: aplicação FastAPI, frontend mobile, persistência SQLite e bridge para o binário C++.
- `deploy/`: artefatos iniciais para implantação MorfoNode em Raspberry Pi.
- `run.sh`: script operacional para compilar o núcleo e subir o servidor web local.

Arquivos gerados localmente, como `build/`, bancos SQLite, certificados, ambientes Python e áudios de campo, não fazem parte do repositório.

## Requisitos

Para o núcleo C++:

- CMake 3.20 ou superior
- Compilador C++ com suporte a C++20

Para a interface web:

- Python 3
- Dependências listadas em `web/requirements.txt`
- `openssl`, quando for usar HTTPS local pelo `run.sh`

A transcrição offline usa `faster-whisper`. O modelo padrão é `small` e pode ser alterado com `MORFOCAMPO_WHISPER_MODEL`. Em instalação MorfoNode, o instalador baixa o modelo antes do uso em campo. Se o Hugging Face limitar downloads anônimos, use `MORFOCAMPO_HF_TOKEN` somente durante a instalação.

## Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

O binário principal fica em:

```bash
build/morfocampo
```

## Testes

```bash
ctest --test-dir build --output-on-failure
```

O conjunto atual cobre normalização, validação, parser de transcrições, parser de comandos de voz e fluxos básicos da CLI.

## Uso Pela CLI

Validar uma planilha:

```bash
./build/morfocampo validate --input examples/template_arvores.csv --out out
```

Interpretar frases estruturadas de voz:

```bash
./build/morfocampo parse-voice --input examples/fala_estruturada.txt --out out/dados_por_voz.csv
```

Converter transcrições em lote:

```bash
./build/morfocampo parse-transcript --input examples/transcricoes_exemplo.txt --out out/transcricao_convertida.csv
```

Importar uma planilha silvipastoril legada:

```bash
./build/morfocampo import-silvipastoril --input planilha_silvipastoril.csv \
  --project MORFO-2026 --campaign C01 --area "Arboreto" --out resultado_importado
```

## Interface Web

Para iniciar o ambiente web local:

```bash
./run.sh
```

O script:

1. compila o binário C++ quando necessário;
2. instala ou verifica dependências Python;
3. cria certificados locais autoassinados quando ausentes;
4. sobe o servidor HTTPS na porta `8011`.

Depois de iniciado, acesse:

```text
https://localhost:8011
```

`localhost` funciona apenas no próprio computador que está executando o servidor. Para acesso por celular, mantenha o celular na mesma rede e use um dos endereços informados pelo script:

```text
https://morfocampo.local:8011
https://<hostname>.local:8011
https://<IP-do-equipamento>:8011
```

O nome `morfocampo.local` depende de mDNS/Avahi e é configurado automaticamente no modo MorfoNode. Em uma máquina de desenvolvimento, o endereço pode ser o hostname real do computador, por exemplo `https://fedora.local:8011`. Use o IP informado pelo script se nenhum nome `.local` resolver. O aviso de certificado do navegador é esperado por se tratar de certificado local autoassinado.

Quando houver IP local detectado, o `run.sh` também imprime um QR code no terminal para abrir o endereço no celular. Para ocultar o QR code:

```bash
MORFOCAMPO_SHOW_QR=0 ./run.sh
```

Para forçar outro endereço no QR code:

```bash
MORFOCAMPO_QR_URL='https://morfocampo.local:8011' ./run.sh
```

Em uma máquina de desenvolvimento Linux com Avahi, você pode publicar o alias local com:

```bash
sudo deploy/configure_mdns_alias.sh
```

Para proteger rotas `/api` em rede local, defina um token antes de iniciar:

```bash
MORFOCAMPO_AUTH_TOKEN='token-longo-local' ./run.sh
```

Esse token local é separado de `MORFOCAMPO_HF_TOKEN`, usado apenas para download de modelo no instalador MorfoNode.

Mais detalhes estão em `web/README_WEB.md`.

## Privacidade E LGPD

O Morfocampo não usa cookies de rastreamento ou analytics. A interface web usa `localStorage` apenas para token local, nome do observador e reconhecimento do aviso de privacidade no aparelho.

Como o sistema pode armazenar nome do observador, áudios, transcrições e registros de campo, a instituição responsável pela campanha deve definir base legal, informação aos participantes, retenção e descarte. Consulte `PRIVACY_LGPD.md` para o checklist operacional.

## MorfoNode

O modo MorfoNode transforma um Raspberry Pi em um equipamento local de coleta:

```text
Wi-Fi: MORFOCAMPO
https://morfocampo.local:8011
```

Os artefatos iniciais de implantação ficam em `deploy/`. A visão de evolução do produto está em `ROADMAP.md`.

Para preparar um Raspberry Pi em modo headless, use o instalador dedicado:

```bash
sudo deploy/install_morfonode.sh
```

Depois da instalação, o Raspberry deve iniciar o serviço automaticamente no boot e criar o Wi-Fi de campo.

Como o MorfoNode normalmente opera sem tela, o instalador gera QR codes persistentes em:

```text
/var/lib/morfocampo/morfonode-access-qr.svg
/var/lib/morfocampo/morfonode-site-qr.png
/var/lib/morfocampo/morfonode-access-qr.png
/var/lib/morfocampo/morfonode-wifi-qr.png
```

Use `morfonode-wifi-qr.png` para conectar o celular à rede `MORFOCAMPO` e `morfonode-site-qr.png` para abrir `https://morfocampo.local:8011`. O QR do Wi-Fi pode aparecer no celular como opção de salvar/conectar rede; isso é esperado. Android/iOS podem exigir confirmação do usuário e não permitem que o QR habilite o Wi-Fi sozinho. Esses arquivos são adequados para imprimir etiquetas e colar no equipamento. Para outro endereço no QR do site, defina `MORFOCAMPO_QR_URL` antes de rodar o instalador.

O MorfoNode também instala um atualizador protegido. Por padrão ele fica em modo somente manual:

```bash
sudo morfocampo-update
```

A atualização automática pode ser habilitada em `/etc/morfocampo/morfonode.env` com `MORFOCAMPO_UPDATE_ENABLED=1`. O atualizador só instala tags `v*`, exige CI aprovado no GitHub Actions para o commit candidato, faz backup antes da troca, compila e testa em staging, reinicia o serviço e tenta restaurar a versão anterior se a nova não subir. Detalhes operacionais estão em `deploy/README_MORFONODE.md`.

## Protocolo De Voz

Exemplo de frase completa:

```text
arvore A-023 espécie Butia odorata latitude -30,5 longitude -54,2 CAP 42,5 altura total 4,8 altura da copa 2,2 copa ns 3,5 copa lo 3,1 condição viva HF 2,5 HIC 1,5 densicopa 4 forma TL posição dossel característica PF característica 2 seca
```

O comando `corrigir` altera campos de um registro existente:

```text
corrigir arvore A-023 CAP 43,0
```

Os descritores silvipastoris adicionais são opcionais e podem conviver com os campos dendrométricos tradicionais.

## Fluxo De Desenvolvimento

Antes de abrir uma tag ou release:

1. confirme que o repositório está limpo com `git status`;
2. compile com `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`;
3. rode `ctest --test-dir build --output-on-failure`;
4. revise se apenas código, configurações, exemplos e documentação necessários estão versionados;
5. crie ou atualize `RELEASE_NOTES_vX.Y.Z.md`;
6. commite as notas de release junto com o estado que será versionado;
7. envie `master` e aguarde o CI passar;
8. crie a tag anotada `vX.Y.Z` somente depois de validar o estado acima;
9. envie a tag e aguarde o CI da tag passar;
10. crie a GitHub Release usando a tag e o conteúdo de `RELEASE_NOTES_vX.Y.Z.md`.

Tags publicadas não devem ser movidas. Se uma tag sair sem algum ajuste documental, prefira corrigir em `master` e publicar uma nova versão patch.

## Filosofia De Campo

A interface digital complementa a coleta física, mas não substitui papel, marcações no terreno ou outros mecanismos de segurança documental. O objetivo é reduzir retrabalho de digitação, padronizar campos e facilitar validação rápida ao final do dia.

## Licença

Este projeto é distribuído sob a GNU General Public License v3.0 somente. Consulte `LICENSE` para o texto completo.
