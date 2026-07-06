# Roadmap Morfocampo

Este roadmap separa o estado atual do projeto da direção de produto. A meta é evoluir o Morfocampo de uma ferramenta local de coleta para uma plataforma offline de aquisição de dados ecológicos.

## Visão

O Morfocampo deve funcionar como infraestrutura de campo:

- núcleo determinístico em C++20;
- interface web local acessada pelo celular;
- armazenamento SQLite;
- operação sem internet;
- exportação auditável;
- implantação embarcada em Raspberry Pi como MorfoNode.

A primeira camada de coleta cobre dados morfométricos e silvipastoris. A arquitetura deve continuar aberta para outros protocolos ambientais, como inventário florestal, solos, pastagens, biodiversidade, fauna e monitoramento participativo.

## Fase 1: Núcleo Reproduzível

Estado desejado:

- build CMake documentado;
- testes CTest passando;
- exemplos pequenos e versionados;
- arquivos gerados fora do Git;
- README voltado a desenvolvimento.

Status atual: em andamento, com build e testes funcionais.

## Fase 2: Web Local Segura

Antes de tratar a web como release robusta, implementar:

- autenticação local simples por token;
- limites de tamanho para uploads de áudio e CSV;
- validação de extensão e tipo de arquivo;
- sanitização de nomes de arquivo recebidos por upload;
- escape seguro de HTML ao renderizar relatórios;
- mensagens de erro auditáveis sem expor caminhos internos desnecessários;
- documentação explícita de operação em rede confiável.
- aviso de privacidade na interface e documentação LGPD operacional;
- política institucional definida para retenção, descarte e atendimento a titulares quando houver dados pessoais.

Status atual: hardening básico iniciado com token local opcional, limites de upload, sanitização de nomes de arquivo, escape no renderizador de relatórios, aviso de privacidade e documentação LGPD operacional.

## Fase 3: MorfoNode

Transformar o Raspberry Pi em um appliance de campo:

```text
Power ON
30 s
Wi-Fi: MORFOCAMPO
https://morfocampo.local
```

Requisitos:

- serviço `systemd` para iniciar automaticamente;
- hostname `morfocampo.local` via mDNS/Avahi;
- hotspot Wi-Fi próprio;
- HTTPS local;
- banco e áudios em diretório persistente;
- logs via `journalctl`;
- firewall com portas mínimas abertas;
- instalação documentada e repetível.
- rotina de backup, retenção e descarte de banco, áudios e exportações.

Artefatos iniciais ficam em `deploy/`.

Status atual: instalador MorfoNode com checagens básicas, hotspot persistente via NetworkManager, serviço `systemd`, token local, log de instalação, resumo de acesso em `/var/lib/morfocampo/morfonode-info.txt`, backup manual via `morfocampo-backup` e documentação de privacidade operacional.

## Fase 4: Atualização Operacional

Objetivo:

```bash
morfocampo update
```

Fluxo esperado:

1. verificar internet;
2. selecionar tag `v*`;
3. confirmar CI aprovado no GitHub Actions;
4. construir em staging;
5. rodar testes de sanidade;
6. fazer backup de dados e código;
7. parar serviço;
8. atualizar código;
9. reiniciar serviço;
10. restaurar versão anterior em falha de troca ou inicialização;
11. registrar versão instalada.

Status atual: atualizador inicial implementado como `morfocampo-update`, com timer `systemd` instalado e desabilitado por política via `MORFOCAMPO_UPDATE_ENABLED=0` até o operador optar por atualização automática.

## Fase 5: Sincronização

Evoluir de appliance isolado para edge node:

```text
MorfoNode 1  \
MorfoNode 2   -> sincronização eventual -> MorfoCloud ou servidor institucional
MorfoNode N  /
```

Princípios:

- cada node deve operar sozinho sem internet;
- sincronização deve ser explícita e auditável;
- conflitos devem preservar dados originais;
- exportação local deve continuar existindo mesmo com nuvem.

## Critério Para Primeira Release Embarcada

Antes da primeira tag voltada a Raspberry Pi:

1. build e testes passando;
2. hardening mínimo da API web concluído;
3. instalação MorfoNode testada em Raspberry Pi real;
4. acesso por `https://morfocampo.local`;
5. hotspot próprio validado;
6. backup/exportação documentados;
7. recuperação básica documentada para falha de cartão SD ou banco.
8. checklist LGPD revisado pela instituição responsável pela campanha.
