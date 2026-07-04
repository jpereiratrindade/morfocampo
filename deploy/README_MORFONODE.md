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
- gera um token local para proteger as rotas `/api`;
- instala `faster-whisper` e baixa o modelo de transcrição;
- salva um resumo em `/var/lib/morfocampo/morfonode-info.txt`;
- instala o comando `morfocampo-backup`;
- habilita o serviço na inicialização.

Variáveis úteis:

| Variável | Padrão | Uso |
|---|---:|---|
| `MORFOCAMPO_WIFI_SSID` | `MORFOCAMPO` | Nome do Wi-Fi criado pelo Raspberry |
| `MORFOCAMPO_WIFI_PASSWORD` | `morfocampo2026` | Senha WPA do hotspot |
| `MORFOCAMPO_WIFI_IFACE` | auto | Interface Wi-Fi, ex: `wlan0` |
| `MORFOCAMPO_AUTH_TOKEN` | gerado | Token local da API |
| `MORFOCAMPO_HOSTNAME` | `morfocampo` | Hostname publicado como `morfocampo.local` |
| `MORFOCAMPO_PORT` | `8011` | Porta HTTPS |
| `MORFOCAMPO_WHISPER_MODEL` | `small` | Modelo de transcrição offline |
| `MORFOCAMPO_SKIP_WHISPER_DOWNLOAD` | `0` | Use `1` para não baixar o modelo na instalação |

Exemplo com senha e token definidos:

```bash
sudo MORFOCAMPO_WIFI_PASSWORD='senha-com-8-ou-mais-caracteres' \
     MORFOCAMPO_AUTH_TOKEN='token-longo-local' \
     deploy/install_morfonode.sh
```

Se a interface Wi-Fi não for detectada automaticamente:

```bash
sudo MORFOCAMPO_WIFI_IFACE=wlan0 deploy/install_morfonode.sh
```

Quando o token está ativo, o navegador pede o token no primeiro acesso às rotas protegidas e o salva no `localStorage` do aparelho.

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
- Log de instalação: `/var/lib/morfocampo/install.log`

Esses arquivos devem entrar na rotina de backup/exportação do equipamento.

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

## Segurança Operacional

Este modo ainda pressupõe rede local confiável. A API usa token local simples, limites de upload e sanitização básica, mas uma release embarcada pública ainda deve passar por validação em Raspberry Pi real e revisão de operação.
