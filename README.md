# Morfocampo 🌳

O `morfocampo` é um ecossistema completo para a coleta, processamento, transcrição por voz e validação de dados morfométricos e silvipastoris (protocolo IRDER) em campo. 

Criado com uma arquitetura híbrida de alto desempenho, o sistema combina um **núcleo determinístico em C++** com uma **aplicação web mobile-first** (Python/FastAPI + SQLite), permitindo coletas ágeis por comando de voz direto no celular, mesmo sem acesso à internet.

---

## 🚀 Arquitetura e Componentes

1. **Núcleo C++20 (`src/`, `include/`)**
   O coração do sistema. Responsável por interpretar a fala estruturada (Regex avançado e normalização utf-8), processar e validar arquivos CSV, e emitir relatórios Markdown. É um binário isolado, testável e sem dependências externas complexas, garantindo auditoria e velocidade.

2. **Interface Web / App Mobile (`web/`)**
   Uma SPA (Single Page Application) em Vanilla JS, HTML e CSS injetada por um servidor Python (FastAPI).
   * **Gravador de áudio nativo:** O usuário grava a voz em campo direto no navegador do celular.
   * **Transcrição Offline:** O servidor utiliza o modelo `faster-whisper` localmente para converter o áudio em texto (sem precisar de internet em campo).
   * **Persistência Segura:** Banco de dados SQLite (`web/campo.db`) em tempo real.
   * **Painel Admin:** Visão global de campanhas, observadores, e controle de exportações.

3. **Integração IRDER**
   O morfocampo não lida apenas com dendrometria básica. Ele possui suporte total e nativo aos descritores do **Protocolo IRDER** (silvipastoril): *Altura do Fuste (HF), Altura de Inserção da Copa (HIC), Densicopa, Forma do Fuste, Posição Sociológica, e Características 1/2*.

---

## 📖 Tutorial de Uso Completo

### 1. Inicializando o Servidor Web

Para iniciar o sistema na sua máquina e deixá-lo pronto para acesso no celular, basta usar o script de automação na raiz do projeto:

```bash
./run.sh
```

O script cuidará de:
1. Compilar o binário C++ (caso existam atualizações de código).
2. Verificar dependências Python (`fastapi`, `faster-whisper`, etc.).
3. Subir o servidor Uvicorn na porta **8011** (HTTPS).

**Acesso no Celular:**
Conecte o celular na mesma rede Wi-Fi do notebook (ou use ancoragem USB). O terminal exibirá um endereço seguro (HTTPS) parecido com: `https://192.168.0.10:8011`.
Abra esse link no navegador do celular. (*Nota: Aceite o aviso de segurança do navegador para "Prosseguir em modo inseguro", isso é necessário para o navegador liberar acesso ao microfone*).

### 2. Fluxo em Campo (Coleta por Voz)

O `morfocampo` foi desenhado para agilizar o trabalho do observador que está com fita métrica e prancheta na mão.

1. Acesse o aplicativo e clique em **+ Campanha** para registrar a área de estudo.
2. Na tela da Sessão, insira seu **Nome** (Observador) e a **Parcela**.
3. Na aba **Coletar**, clique no botão central de Microfone (🎙) e dite as medidas da árvore pausadamente.

**Protocolo de Fala (Exemplo Completo):**
> *"arvore A-023 espécie Butia odorata latitude -30,5 longitude -54,2 CAP 42,5 altura total 4,8 altura da copa 2,2 copa ns 3,5 copa lo 3,1 condição viva HF 2,5 HIC 1,5 densicopa 4 forma TL posição dossel característica PF característica 2 seca"*

*Dicas para o comando de voz:*
* Use números normais e vírgulas: diga "quarenta e dois vírgula cinco", não fale unidades por extenso.
* O comando `corrigir` altera um registro pré-existente (ex: `"corrigir arvore A-023 CAP 43,0"`).
* Os descritores de copa tradicionais (`altura da copa`, `copa ns`, `copa lo`) convivem em harmonia com os descritores do IRDER. Todos são opcionais e só aparecem se forem ditados.

### 3. Integração e Importação de Planilhas Legadas

Se você tem planilhas antigas do protocolo IRDER (exportadas em CSV pelo LibreOffice), o morfocampo pode ingeri-las nativamente:

1. Acesse o botão **⚙ Admin** ao lado da sua campanha.
2. Clique no botão verde **🌳 IRDER**.
3. O modal exibirá os campos esperados (separador `;` ou `,`). Faça o upload do arquivo e o sistema migrará os dados instantaneamente para o SQLite.

### 4. Validação e Exportação

Ao final do dia de trabalho:
1. Vá na aba **✓ Validar**.
2. Clique em **▶ Validar campanha**.
3. O núcleo C++ varrerá todos os registros cruzando informações de todos os observadores para checar valores discrepantes, árvores não identificadas, e DAPs fora da faixa aceitável.
4. Clique em **⬇ Exportar** para baixar um pacote `.zip` contendo os CSVs consolidados e o Relatório em Markdown, ideais para importar no QGIS ou R.

---

## 🛠 Comandos de Terminal (Core C++ / CLI)

O morfocampo ainda pode ser usado de forma "pura", diretamente pelo terminal, sem o servidor Web. O binário ficará em `build/morfocampo`.

**Normalizar e Validar um arquivo CSV avulso:**
```bash
./build/morfocampo validate --input sua_planilha.csv --out pasta_saida --max-cap 600
```

**Interpretar arquivo de transcrições em lote (lote txt de vozes):**
```bash
./build/morfocampo parse-voice --input audio_transcrito.txt --out resultado_interpretado.csv
```

**Importar protocolo IRDER em lote pelo terminal:**
```bash
./build/morfocampo import-irder --input planilha_irder.csv --out resultado_importado.csv
```

---

## 🔧 Estrutura de Diretórios

* `src/` e `include/`: Código-fonte C++20 puro. Classes de negócio, Validador, Parser de Voz e gerador de Relatório.
* `web/`: Aplicação Python FastAPI (`server.py`), Banco SQLite (`db.py`), Bridge C++ (`morfocampo_bridge.py`), e frontend em HTML/JS (`static/`).
* `build/`: Local do binário C++ após execução do `run.sh`.
* `tests/`: Bateria de testes unitários do núcleo C++.

## 💡 Filosofia de Uso

O aplicativo digital **complementa e acelera o registro, mas não substitui a necessidade do papel como backup de segurança ou as marcações no terreno**. Seu maior benefício é o *Double-Entry* instantâneo: você coleta falando, o celular registra visualmente e o banco normaliza e exporta, minimizando semanas de digitação em laboratório.
