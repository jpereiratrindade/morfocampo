# Morfocampo v0.2.0

Esta release marca a transição do projeto para uma base mais clara de desenvolvimento e para a visão MorfoNode em Raspberry Pi.

## Destaques

- README reorganizado com foco em build, testes, CLI, web local e fluxo de release.
- `.gitignore` revisado para manter artefatos locais fora do repositório.
- Roadmap de produto e engenharia adicionado em `ROADMAP.md`.
- Base inicial de implantação MorfoNode adicionada em `deploy/`.
- Serviço `systemd` inicial para execução automática do servidor local.
- Instalador inicial para Raspberry Pi com dependências, build, ambiente Python, certificados locais, Avahi e hotspot Wi-Fi.
- Configuração operacional exemplo para banco, áudio, HTTPS e porta do serviço.

## MorfoNode

O modo MorfoNode aponta para o uso do Raspberry Pi como equipamento local de coleta:

```text
Wi-Fi: MORFOCAMPO
https://morfocampo.local:8011
```

Esta base ainda deve ser validada em Raspberry Pi real antes de ser tratada como instalação embarcada estável.

## Validação

- Build C++ com CMake em modo Release.
- Testes CTest passando: 6/6.
- Validação de sintaxe do instalador `deploy/install_morfonode.sh`.

## Próximos Passos

- Hardening da API web com autenticação local, limites de upload e sanitização.
- Teste do instalador em Raspberry Pi real.
- Ajuste fino do hotspot Wi-Fi e resolução `morfocampo.local`.
- Rotina de backup/exportação operacional para banco SQLite e áudios.
