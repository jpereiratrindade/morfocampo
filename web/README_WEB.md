# morfocampo Web — Interface de campo mobile

Interface web mobile-first para coleta de dados morfométricos com áudio, transcrição local e persistência em SQLite3.

## Arquitetura

```
celular/tablet (browser)
  ↓ WiFi local ou USB tethering
notebook do pesquisador / Raspberry Pi
  ├── server.py (FastAPI)
  ├── transcriber.py (faster-whisper, offline)
  ├── morfocampo_bridge.py → ../build/morfocampo (núcleo C++)
  └── campo.db (SQLite3)
```

O papel continua como referência documental física. A interface digital complementa e acelera, nunca substitui.

## Pré-requisitos

```sh
# Binário C++ já compilado (raiz do projeto):
cmake -S .. -B ../build && cmake --build ../build

# Dependências Python:
pip install -r requirements.txt

# Transcrição offline:
pip install -r requirements.txt
# O modelo padrão é 'small' e pode ser alterado com MORFOCAMPO_WHISPER_MODEL.
```

## Executar

```sh
cd morfocampo/web

python server.py \
  --db campo.db \
  --bin ../build/morfocampo \
  --port 8000
```

Para proteger as rotas `/api` em rede local, defina um token:

```sh
MORFOCAMPO_AUTH_TOKEN='token-longo-local' python server.py \
  --db campo.db \
  --bin ../build/morfocampo \
  --port 8000
```

Quando o token está ativo, o frontend envia `X-Morfocampo-Token` nas chamadas da API. No primeiro acesso protegido, o navegador solicita o token e o salva localmente no aparelho.

## Acessar no celular

O celular deve estar na mesma rede WiFi do notebook (ou conectado via USB tethering).

```
http://<IP-do-notebook>:8000
```

Com HTTPS local:

```text
https://morfocampo.local:8011
https://<hostname>.local:8011
https://<IP-do-equipamento>:8011
```

`localhost` só funciona no próprio equipamento que está rodando o servidor. No MorfoNode, o instalador configura hostname `morfocampo` e Avahi para publicar `morfocampo.local`. Em execução manual fora do Raspberry, o nome real da máquina também pode funcionar, como `fedora.local`. Use o IP se nenhum nome `.local` resolver.

Para publicar `morfocampo.local` em uma máquina Linux de desenvolvimento:

```sh
sudo ../deploy/configure_mdns_alias.sh
```

Para descobrir o IP do notebook:
```sh
ip addr show | grep "inet " | grep -v 127.0.0.1
```

## Fluxo de uso

1. **Antes de sair para campo**: crie a campanha na tela inicial e gere a planilha impressa com `morfocampo init-campaign` no terminal.
2. **No campo**: abra o browser no celular → selecione campanha → informe observador e parcela.
3. **Coleta**: toque no botão 🎙 → fale a frase → confirme os campos interpretados → salvo no SQLite.
4. **Registro exclusivo por observador**: cada observador vê apenas seus próprios registros na sessão. A validação final consolida todos.
5. **Fim do dia**: vá para a aba Validar → compare com a planilha impressa (duplo controle) → exporte CSV + relatório.

## Estratégia de transcrição

| Situação | Motor | Requisito |
|---|---|---|
| Com internet | Web Speech API (browser) | Nenhum |
| Sem internet | faster-whisper (servidor) | `pip install -r requirements.txt` |
| Sem microfone | Digitação manual | — |

## Evidência documental

- Cada áudio gravado é salvo em `audio_files/` com timestamp.
- O campo `raw_input` preserva a frase original de cada registro.
- O campo `audio_file` vincula o registro ao arquivo de áudio.
- O CSV exportado é compatível com `morfocampo validate` no terminal.

## Privacidade, LGPD e armazenamento local

- A aplicação não usa cookies HTTP, analytics ou rastreamento de terceiros.
- O navegador usa `localStorage` para token local, nome do observador e reconhecimento do aviso de privacidade.
- O servidor local armazena banco SQLite, áudios e exportações sob os caminhos configurados.
- O operador deve informar a equipe sobre coleta de identificação, áudio e transcrição quando aplicável.
- A política de retenção e descarte deve ser definida pela instituição responsável pela campanha.

Consulte `../PRIVACY_LGPD.md` antes de operar o sistema em campanhas reais.

## Protocolo de fala para observadores

```
arvore A-023 CAP 42,5 altura total 4,8 condição viva
arvore A-023; espécie Butia odorata; CAP 42,5; condição viva
corrigir arvore A-023 CAP 43,0
```

Consulte `../README.md` → seção "Limitações do parser de voz" para o protocolo completo de treinamento.

## Endpoints da API

```
GET  /api/status
GET  /api/campaigns
POST /api/campaigns
GET  /api/campaigns/{id}
GET  /api/campaigns/{id}/records?observer=Pedro&plot=P01
POST /api/campaigns/{id}/validate
GET  /api/campaigns/{id}/validation/last
GET  /api/campaigns/{id}/export
POST /api/transcribe          (áudio → texto via faster-whisper)
POST /api/parse               (texto → campos morfométricos via C++)
POST /api/records
PATCH /api/records/{id}
DELETE /api/records/{id}
POST /api/audio               (salva blob de áudio como evidência)
```

Documentação interativa: `http://localhost:8000/docs`
