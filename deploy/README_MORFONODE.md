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

O instalador faz:

- instala dependências de sistema;
- cria diretórios persistentes em `/var/lib/morfocampo`;
- cria ambiente Python em `/opt/morfocampo-venv`;
- instala dependências web;
- compila o binário C++;
- gera certificado local autoassinado;
- instala serviço `systemd`;
- configura hostname `morfocampo`;
- tenta criar hotspot Wi-Fi `MORFOCAMPO` com senha local;
- gera um token local para proteger as rotas `/api`;
- habilita o serviço na inicialização.

A senha padrão do hotspot é `morfocampo2026`. Para definir outra senha na instalação:

```bash
sudo MORFOCAMPO_WIFI_PASSWORD='senha-com-8-ou-mais-caracteres' deploy/install_morfonode.sh
```

O instalador imprime o token local ao final. Para definir um token próprio:

```bash
sudo MORFOCAMPO_AUTH_TOKEN='token-longo-local' deploy/install_morfonode.sh
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

Se o nome local não resolver, use o IP do Raspberry informado pelo sistema:

```bash
hostname -I
```

## Arquivos Persistentes

- Banco SQLite: `/var/lib/morfocampo/campo.db`
- Áudios: `/var/lib/morfocampo/audio_files/`
- Certificados locais: `/var/lib/morfocampo/certs/`

Esses arquivos devem entrar na rotina de backup/exportação do equipamento.

## Segurança Operacional

Este modo ainda pressupõe rede local confiável. A API usa token local simples, limites de upload e sanitização básica, mas uma release embarcada pública ainda deve passar por validação em Raspberry Pi real e revisão de operação.
