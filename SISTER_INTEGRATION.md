# Integracao com o SisTer

Este repositorio e um sistema autonomo integrado ao SisTer. Antes de alterar
portas, containers, volumes, hosts locais, contratos ou formatos de intercambio,
consulte a fonte central:

```text
$SISTER_HOME/config/local_resources.json
$SISTER_HOME/docs/governance/INTEGRATED_PROJECTS.md
```

Se `SISTER_HOME` nao estiver definido, no layout do laboratorio a raiz esperada
e `../SisTer`. Se a governanca central nao estiver disponivel, nao reserve um
novo recurso local nem publique uma mudanca de integracao.

Identificador deste projeto no registro: `morfocampo`.

## Canais com o SisTer-Nexo (IS-MORFOCAMPO-NEXO-001)

A especificação formal de requisitos e conformidade arquitetural com o SisTer-Nexo é governada por [`docs/IS-MORFOCAMPO-NEXO-001.md`](docs/IS-MORFOCAMPO-NEXO-001.md).

- **Contrato de Intercâmbio**: `camposync.package/2.0.0`
- **Operação**: Local-first e offline-first no MorfoNode (Raspberry Pi 5)
- **API institucional do Nexo**:
  - `GET /api/v1/integrations/morfocampo/contexts` (cache local de contextos autorizados)
  - `POST /api/v1/integrations/morfocampo/packages` (sincronização via outbox imutável com recibo `camposync.receipt/1.0.0`)

Configuração de runtime do MorfoNode:

```text
MORFOCAMPO_NEXO_URL=https://host-do-nexo:8000
MORFOCAMPO_NEXO_TOKEN_FILE=/caminho/protegido/token
MORFOCAMPO_NEXO_CA_FILE=/caminho/protegido/ca.crt
```
*(Variáveis legadas `MORFOCAMPO_SISTER_CAMPO_*` são mantidas como fallback de compatibilidade).*

HTTP sem TLS é aceito somente em loopback. Segredos não são declarados no
registro central nem versionados.

