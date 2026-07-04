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

O protocolo IRDER é a primeira camada de coleta. A arquitetura deve continuar aberta para outros protocolos ambientais, como inventário florestal, solos, pastagens, biodiversidade, fauna e monitoramento participativo.

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

Artefatos iniciais ficam em `deploy/`.

## Fase 4: Atualização Operacional

Objetivo:

```bash
morfocampo update
```

Fluxo esperado:

1. parar serviço;
2. atualizar código;
3. recompilar;
4. aplicar migrações;
5. rodar testes de sanidade;
6. reiniciar serviço;
7. registrar versão instalada.

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
