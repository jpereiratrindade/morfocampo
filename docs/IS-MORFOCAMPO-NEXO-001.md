---
document_type: implementation_spec
document_id: IS-MORFOCAMPO-NEXO-001
title: "MorfoCampo — requisitos de implementação para integração com Nexo"
version: 0.1.0
status: proposed
maturity: implementation_candidate
created_at: 2026-09-02
last_reviewed_at: 2026-09-02
institutional_context: Embrapa
system: morfocampo
runtime_target: Raspberry Pi 5
integrates_with: sister-nexo
parent_architecture:
  document_id: AP-MORFOCAMPO-NEXO-001
  version: 0.1.0
source_snapshots:
  morfocampo:
    git_head: ae483805b5ad465f12dcd96d163695e6c6a4af6f
    git_describe: v0.2.4-dirty
  sister_nexo:
    git_head: 0822c6776c05cc1829fefee91fffd40994e335ae
    git_describe: v0.2.1-37-g0822c67
scope:
  - identidade persistente do MorfoNode
  - consumo de contexto institucional do Nexo
  - operação offline-first
  - CampoSync 2.0.0
  - outbox e retry
  - eficiência de CPU, memória e I/O no RPi5
out_of_scope:
  - criação de projeto no Nexo
  - criação de atividade de pesquisa/D&I no Nexo
  - acesso direto ao PostgreSQL do Nexo
  - substituição do SQLite local
  - processamento analítico pesado
supersedes: null
superseded_by: null
next_version_hint: "0.1.1 para refinamentos compatíveis; 0.2.0 para mudança substantiva; 1.0.0 após aceitação"
---

# MorfoCampo — integração com Nexo

## 1. Objetivo

Adaptar o MorfoCampo para operar como sistema de aquisição de campo vinculado ao contexto institucional fornecido pelo Nexo, preservando:

- operação local-first;
- funcionamento offline;
- autoridade sobre o dado primário;
- independência do banco do Nexo;
- uso eficiente de CPU, memória e I/O no Raspberry Pi 5.

O MorfoCampo não cria projeto ou atividade institucional. Ele consome um contexto autorizado pelo Nexo e produz campanhas vinculadas a esse contexto.

---

## 2. Responsabilidades do MorfoCampo

O MorfoCampo deverá ser autoridade sobre:

- aquisição de campo;
- observação primária;
- validação local;
- arquivos originais;
- campanha;
- persistência local;
- geração do pacote CampoSync;
- fila local de sincronização.

O MorfoCampo não deverá:

- criar `project_id` livremente no modo integrado;
- criar `research_activity_id`;
- registrar sozinho um MorfoNode como autoridade institucional;
- acessar diretamente o PostgreSQL do Nexo;
- depender de conexão durante a coleta;
- reconstruir desnecessariamente pacotes já materializados em cada retry.

---

## 3. Implementação requerida

### MC-NEXO-01 — Identidade local do MorfoNode

Persistir localmente:

```text
morfonode_id
hardware_serial
credential_id/fingerprint
credential material protegido
registration_state
```

Regras:

- o `morfonode_id` vem do processo de registro no Nexo;
- o serial físico identifica o hardware;
- a credencial autentica o nó;
- hostname, IP, MAC e `machine-id` são apenas informações auxiliares;
- reinstalação deve permitir reestabelecer a identidade do mesmo hardware de forma controlada;
- credencial revogada não deve ser reutilizada silenciosamente.

### MC-NEXO-02 — Cache de Collection Context

Consumir:

```text
GET /api/v1/integrations/morfocampo/contexts
```

e armazenar localmente os contextos autorizados.

Cada contexto deve conter pelo menos:

```text
context_id
project_id
research_activity_id
operational_activity_id?
morfonode_id
status
valid_from
valid_until?
revision
```

O operador deve selecionar um contexto provisionado; não digitar livremente projeto/atividade no modo integrado.

### MC-NEXO-03 — Campanha vinculada ao contexto

Toda campanha integrada deverá persistir desde sua criação:

```text
campaign_id
context_id
project_id
research_activity_id
operational_activity_id?
morfonode_id
context_revision
```

Essa vinculação não deve depender de informação adicionada somente no momento da exportação.

Campanhas locais fora de integração podem existir apenas se forem explicitamente diferenciadas das campanhas institucionalmente vinculadas.

### MC-NEXO-04 — CampoSync 2.0.0

Evoluir o pacote para incluir obrigatoriamente:

```text
package_id
campaign_id
context
producer
created_at
files
checksum
```

com:

```text
context.context_id
context.project_id
context.research_activity_id
context.operational_activity_id?

producer.system_id = morfocampo
producer.system_version
producer.morfonode_id
producer.credential_id
```

Neutralizar nomenclatura específica de intermediário, incluindo referências `SISTER_CAMPO_*` e rotas `sync/sister-campo`.

CampoSync deve ser contrato de integração, não nome de um sistema receptor.

### MC-NEXO-05 — Materialização eficiente do pacote

A geração do pacote deverá:

- ler SQLite incrementalmente;
- evitar carregar a campanha completa em memória;
- escrever arquivos de saída progressivamente;
- calcular hashes incrementalmente;
- evitar cópias redundantes;
- manter uso previsível de memória;
- produzir artefato imutável após finalização.

Fluxo preferencial:

```text
SQLite
  ↓ leitura incremental
writer CampoSync
  ↓
hash incremental
  ↓
pacote final imutável
```

Evitar:

```text
SQLite
  ↓
dataset integral em RAM
  ↓
estrutura intermediária
  ↓
nova serialização
  ↓
nova cópia
  ↓
pacote
```

### MC-NEXO-06 — Outbox durável

Criar fila persistente:

```text
package_id
campaign_id
context_id
checksum
artifact_path
state
attempts
last_attempt_at
receipt_id?
```

Estados mínimos:

```text
pending
sending
acknowledged
failed
```

O artefato final deve ser reutilizado nos retries.

Um retry não deverá, por padrão:

- consultar novamente toda a campanha;
- recriar CSV;
- recalcular todo o pacote;
- gerar nova cópia integral do artefato.

### MC-NEXO-07 — Sincronização

Enviar:

```text
POST /api/v1/integrations/morfocampo/packages
```

Regras:

- transporte cifrado;
- autenticação de máquina separada da autenticação humana;
- envio tolerante a interrupção;
- retry controlado;
- recepção e persistência de `camposync.receipt/1.0.0`;
- pacote reconhecido como já recebido deve ser tratado como sucesso lógico.

### MC-NEXO-08 — Operação offline

A ausência do Nexo não pode impedir:

- abertura do MorfoCampo;
- seleção de contexto previamente armazenado e válido;
- criação de campanha;
- coleta;
- validação local;
- geração de pacote;
- enfileiramento para sincronização futura.

A conectividade é requisito da sincronização, não da coleta.

---

## 4. Eficiência computacional — prioridade do RPi5

No MorfoNode, eficiência faz parte da correção.

Todo código novo nos caminhos críticos deve priorizar, nesta ordem:

1. evitar trabalho desnecessário;
2. reduzir cópias de memória;
3. reduzir alocações;
4. evitar materialização integral de datasets;
5. reduzir serializações/conversões intermediárias;
6. reduzir I/O redundante;
7. reutilizar artefatos imutáveis;
8. somente depois considerar paralelismo adicional.

Não introduzir concorrência apenas para aumentar throughput se ela elevar de forma desnecessária:

- peak RSS;
- pressão de cache;
- contenção;
- I/O;
- consumo energético;
- complexidade do código.

Métricas mínimas para caminhos de geração e sincronização:

```text
peak RSS
CPU time
bytes lidos
bytes escritos
número de registros
tamanho do pacote
tempo de geração
tempo de envio
```

Os testes devem tornar regressões perceptíveis mesmo antes de existirem limites absolutos formais.

---

## 5. Invariantes de aceitação

O lado MorfoCampo somente estará pronto quando:

1. o MorfoNode utilizar identidade institucional persistente;
2. campanha integrada somente usar contexto provisionado;
3. projeto/atividade não forem digitados livremente no modo integrado;
4. identidade do contexto estiver persistida desde a criação da campanha;
5. coleta funcionar completamente offline;
6. CampoSync 2.0.0 incluir contexto e MorfoNode;
7. pacote final for imutável;
8. retry reutilizar o mesmo artefato sempre que seu conteúdo não mudou;
9. mesmo pacote puder ser reenviado sem duplicar efeito no Nexo;
10. revogação impedir sincronização, sem destruir dado local;
11. nenhum componente acessar diretamente o banco do Nexo;
12. geração e envio operarem com memória limitada e sem carregar a campanha completa em RAM.

---

## 6. Ordem de execução

```text
MC-NEXO-01  Identidade local
    ↓
MC-NEXO-02  Cache de contexto
    ↓
MC-NEXO-03  Campanha contextualizada
    ↓
MC-NEXO-04  CampoSync 2.0.0
    ↓
MC-NEXO-05  Empacotamento eficiente
    ↓
MC-NEXO-06  Outbox
    ↓
MC-NEXO-07  Sincronização + receipt
    ↓
MC-NEXO-08  Gate offline completo
```

Cada incremento deve vir acompanhado de teste funcional e, quando atuar sobre caminhos críticos, testemunho de CPU/memória/I/O.

---

## 7. Critério de conclusão

**DONE** significa que um MorfoNode registrado consegue receber e armazenar contexto do Nexo, operar uma campanha completamente offline, produzir CampoSync 2.0.0 com identidade e proveniência completas, sincronizar posteriormente de forma idempotente e repetir o envio sem reconstrução desnecessária do pacote, mantendo uso de CPU, memória e I/O compatível com o Raspberry Pi 5.
