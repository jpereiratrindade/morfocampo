# MorfoNode

MorfoNode é o modo appliance do Morfocampo em Raspberry Pi. A ideia é que o usuário ligue o equipamento, conecte o celular ao Wi-Fi local e acesse a interface sem terminal.

```text
Power ON
Wi-Fi: MORFOCAMPO
https://morfocampo.local:8011
```

## Premissas

- Raspberry Pi 5 ou similar.
- Raspberry Pi OS recente baseado em Debian.
- NetworkManager disponível para configurar hotspot com `nmcli`.
- Repositório Morfocampo já clonado no equipamento.
- Operação em rede de campo confiável.

## Instalação Inicial

Aviso: o instalador altera configuração de sistema, hostname, serviço `systemd` e tenta criar um hotspot Wi-Fi. Use em um Raspberry dedicado ao MorfoNode ou em uma imagem preparada para esse fim.

Execute a partir da raiz do repositório:

```bash
sudo deploy/install_morfonode.sh
```

Para preparação headless, rode o instalador uma vez por SSH ou durante a preparação da imagem do cartão SD. Depois disso, o Raspberry deve iniciar sozinho sem teclado, mouse ou monitor.

O instalador faz:

- instala dependências de sistema;
- cria diretórios persistentes em `/var/lib/morfocampo`;
- cria ambiente Python em `/opt/morfocampo-venv`;
- instala dependências web;
- compila o binário C++;
- gera certificado local autoassinado;
- instala serviço `systemd`;
- configura hostname `morfocampo`;
- cria hotspot Wi-Fi persistente `MORFOCAMPO` via NetworkManager;
- configura autenticação local da API quando `MORFOCAMPO_AUTH_TOKEN` é informado;
- instala `faster-whisper` e baixa o modelo de transcrição;
- salva um resumo em `/var/lib/morfocampo/morfonode-info.txt`;
- instala o comando `morfocampo-backup`;
- instala o comando `morfocampo-update` e um timer de verificação segura;
- habilita o serviço na inicialização.

Variáveis úteis:

| Variável | Padrão | Uso |
|---|---:|---|
| `MORFOCAMPO_WIFI_SSID` | `MORFOCAMPO` | Nome do Wi-Fi criado pelo Raspberry |
| `MORFOCAMPO_WIFI_PASSWORD` | `morfocampo2026` | Senha WPA do hotspot |
| `MORFOCAMPO_WIFI_IFACE` | auto | Interface Wi-Fi, ex: `wlan0` |
| `MORFOCAMPO_AUTH_TOKEN` | vazio | Token local opcional da API; vazio desativa a exigência de token |
| `MORFOCAMPO_HOSTNAME` | `morfocampo` | Hostname publicado como `morfocampo.local` |
| `MORFOCAMPO_PORT` | `8011` | Porta HTTPS |
| `MORFOCAMPO_WHISPER_MODEL` | `small` | Modelo de transcrição offline |
| `MORFOCAMPO_HF_TOKEN` | vazio | Token opcional do Hugging Face usado só para baixar o modelo Whisper |
| `MORFOCAMPO_QR_URL` | `https://morfocampo.local:8011` | Endereço codificado no QR code persistente |
| `MORFOCAMPO_SKIP_WHISPER_DOWNLOAD` | `0` | Use `1` para não baixar o modelo na instalação |
| `MORFOCAMPO_UPDATE_ENABLED` | `0` | Use `1` para permitir atualização automática pelo timer |
| `MORFOCAMPO_UPDATE_REPO` | GitHub do projeto | Repositório usado pelo atualizador |
| `MORFOCAMPO_UPDATE_REQUIRE_CI` | `1` | Exige GitHub Actions aprovado para a tag candidata |
| `MORFOCAMPO_UPDATE_RUN_TESTS` | `1` | Roda testes e checagens de sintaxe antes de instalar |

Exemplo com senha do hotspot e token do Hugging Face para baixar o modelo:

```bash
sudo MORFOCAMPO_WIFI_PASSWORD='senha-com-8-ou-mais-caracteres' \
     MORFOCAMPO_HF_TOKEN='hf_token_novo' \
     deploy/install_morfonode.sh
```

Para proteger também as rotas `/api`, defina um token local separado:

```bash
sudo MORFOCAMPO_WIFI_PASSWORD='senha-com-8-ou-mais-caracteres' \
     MORFOCAMPO_AUTH_TOKEN='token-local-longo' \
     MORFOCAMPO_HF_TOKEN='hf_token_novo' \
     deploy/install_morfonode.sh
```

Se a interface Wi-Fi não for detectada automaticamente:

```bash
sudo MORFOCAMPO_WIFI_IFACE=wlan0 deploy/install_morfonode.sh
```

Quando `MORFOCAMPO_AUTH_TOKEN` está ativo, o navegador pede o token no primeiro acesso às rotas protegidas e o salva no `localStorage` do aparelho. O `MORFOCAMPO_HF_TOKEN` não é usado pelo app web e não deve ser confundido com o token local da API.

## QR Code De Acesso

O MorfoNode não depende de tela. Durante a instalação, o instalador gera um QR code persistente em:

```text
/var/lib/morfocampo/morfonode-access-qr.svg
```

Por padrão, ele aponta para:

```text
https://morfocampo.local:8011
```

Use esse arquivo para imprimir uma etiqueta e colar no Raspberry ou na caixa de campo. Se precisar apontar para outro endereço fixo, defina `MORFOCAMPO_QR_URL` ao instalar:

```bash
sudo MORFOCAMPO_QR_URL='https://morfocampo.local:8011' deploy/install_morfonode.sh
```

## Serviço

```bash
sudo systemctl status morfocampo
sudo systemctl restart morfocampo
sudo journalctl -u morfocampo -f
```

## Acesso

No celular:

1. conecte ao Wi-Fi `MORFOCAMPO`;
2. abra `https://morfocampo.local:8011`;
3. aceite o aviso do certificado local autoassinado.

`localhost` não deve ser usado no celular, porque aponta para o próprio celular. Se o nome local não resolver, use o IP do Raspberry informado pelo sistema:

```bash
hostname -I
```

## Arquivos Persistentes

- Banco SQLite: `/var/lib/morfocampo/campo.db`
- Áudios: `/var/lib/morfocampo/audio_files/`
- Certificados locais: `/var/lib/morfocampo/certs/`
- Resumo de acesso: `/var/lib/morfocampo/morfonode-info.txt`
- QR code de acesso: `/var/lib/morfocampo/morfonode-access-qr.svg`
- Log de instalação: `/var/lib/morfocampo/install.log`
- Log de atualização: `/var/lib/morfocampo/update.log`
- Versão instalada: `/var/lib/morfocampo/installed-version.txt`
- Backups de código para rollback: `/var/lib/morfocampo/code-backups/`

Esses arquivos devem entrar na rotina de backup/exportação do equipamento.

## Privacidade E LGPD

O MorfoNode pode armazenar dados pessoais operacionais, especialmente nome ou identificação do observador, áudios, transcrições, registros de coleta e backups. O equipamento não usa cookies de rastreamento, mas o navegador do celular pode guardar token local, nome do observador e reconhecimento do aviso de privacidade em `localStorage`.

Antes de usar em campanha real:

1. defina quem é a instituição/controlador responsável pelos dados;
2. informe a equipe de campo sobre identificação, áudio e transcrição;
3. defina retenção, backup, descarte e acesso aos arquivos persistentes;
4. proteja fisicamente o Raspberry Pi e os backups exportados;
5. revise `PRIVACY_LGPD.md` na raiz do repositório.

## Backup

Para criar um pacote local com banco, áudios, certificados e resumo de acesso:

```bash
sudo morfocampo-backup
```

O arquivo é salvo por padrão em:

```text
/var/lib/morfocampo/backups/
```

Também é possível executar o script diretamente a partir do repositório:

```bash
sudo deploy/backup_morfonode.sh
```

## Atualização Segura

O MorfoNode foi desenhado para operar offline. Por isso, a atualização automática fica instalada, mas desabilitada por padrão. O timer pode rodar sem risco: enquanto `MORFOCAMPO_UPDATE_ENABLED=0`, ele apenas registra no log que não deve atualizar.

Para atualizar manualmente:

```bash
sudo morfocampo-update
```

Para permitir verificação automática diária, edite `/etc/morfocampo/morfonode.env`:

```bash
MORFOCAMPO_UPDATE_ENABLED=1
```

Depois recarregue o timer:

```bash
sudo systemctl daemon-reload
sudo systemctl restart morfocampo-update.timer
```

O fluxo de proteção é:

1. verifica se há internet real antes de tentar qualquer operação;
2. usa somente tags `v*` do repositório configurado, não uma branch em movimento;
3. consulta o GitHub Actions e exige ao menos um workflow concluído com sucesso para o commit da tag;
4. constrói a versão candidata fora de `/opt/morfocampo`;
5. roda CTest e checagem de sintaxe Python quando `MORFOCAMPO_UPDATE_RUN_TESTS=1`;
6. atualiza dependências Python antes da troca do código;
7. executa `morfocampo-backup` antes de instalar;
8. guarda um backup do código anterior;
9. para o serviço principal somente na etapa final;
10. reinicia e valida se `morfocampo.service` ficou ativo;
11. em falha durante a troca ou inicialização, restaura o código anterior e tenta subir o serviço antigo.

Comandos úteis:

```bash
sudo systemctl status morfocampo-update.timer
sudo systemctl start morfocampo-update.service
sudo journalctl -u morfocampo-update -n 100
sudo tail -f /var/lib/morfocampo/update.log
cat /var/lib/morfocampo/installed-version.txt
```

Se o GitHub limitar chamadas anônimas ou o repositório for privado, defina um token com escopo mínimo em `/etc/morfocampo/morfonode.env`:

```bash
MORFOCAMPO_GITHUB_TOKEN=ghp_token_com_escopo_minimo
```

## Segurança Operacional

Este modo ainda pressupõe rede local confiável. A API usa token local simples, limites de upload e sanitização básica, mas uma release embarcada pública ainda deve passar por validação em Raspberry Pi real, revisão de operação e revisão institucional de privacidade/LGPD.
