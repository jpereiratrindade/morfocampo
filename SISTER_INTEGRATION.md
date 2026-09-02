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

## Canais com o SisTer-Campo

- pacote offline: exportação `camposync.package/1.0.0`;
- API: envio explícito do mesmo ZIP, sem alterar o contrato.

Configuração opcional da API:

```text
MORFOCAMPO_SISTER_CAMPO_URL=https://host-do-sister-campo:8013
MORFOCAMPO_SISTER_CAMPO_TOKEN_FILE=/caminho/protegido/token
MORFOCAMPO_SISTER_CAMPO_CA_FILE=/caminho/protegido/ca.crt
```

HTTP sem TLS é aceito somente em loopback. Segredos não são declarados no
registro central nem versionados.
