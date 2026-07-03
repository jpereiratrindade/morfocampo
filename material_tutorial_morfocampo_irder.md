# Material tutorial — Morfocampo e Protocolo IRDER

**Objetivo deste arquivo:** servir como base para dois produtos de comunicação da equipe:

1. um **vídeo tutorial técnico**, voltado para demonstrar o uso do sistema em campo e na importação de planilhas;
2. uma **apresentação curta**, voltada para explicar a lógica do sistema, o mapeamento dos dados IRDER e os próximos passos de desenvolvimento.

---

## 1. Ideia central do material

O **Morfocampo** é uma ferramenta para reduzir retrabalho, erros de digitação e perda de informação em levantamentos morfométricos e silvipastoris.

A mensagem principal deve ser:

> O sistema não substitui o protocolo de campo. Ele traduz o protocolo para um fluxo digital, mantendo a lógica técnica da coleta e facilitando validação, exportação e análise posterior.

Em outras palavras: o protocolo IRDER continua sendo a referência. O Morfocampo apenas evita que a equipe tenha que “domar a planilha no laço” depois do campo.

---

## 2. Público-alvo

Este material deve conversar com três públicos ao mesmo tempo:

| Público | O que precisa entender |
|---|---|
| Equipe de campo | Como coletar, revisar e exportar os dados |
| Equipe técnica/desenvolvimento | Como os campos da planilha IRDER entram no sistema |
| Coordenação/pesquisa | Por que o sistema melhora rastreabilidade, qualidade e padronização dos dados |

---

## 3. Problema que o sistema resolve

### Situação atual

A coleta do arboreto IRDER utiliza planilhas com campos próprios do protocolo silvipastoril, como:

- data;
- linha;
- espécie;
- GPS ou identificador da árvore;
- CAP;
- altura total;
- altura do fuste;
- altura de inserção da copa;
- densidade da copa;
- forma do fuste;
- posição sociológica;
- características qualitativas da árvore.

Esses dados são ricos, mas quando ficam apenas em planilhas, surgem alguns problemas:

- risco de erro de digitação;
- dificuldade de padronizar nomes de espécies e códigos;
- retrabalho ao consolidar dados;
- perda de significado quando campos técnicos são jogados em observações gerais;
- dificuldade de validar valores discrepantes rapidamente;
- demora para levar os dados para R, QGIS, relatórios ou banco de dados.

### Proposta

O Morfocampo organiza esse fluxo em três caminhos complementares:

1. **coleta digital por voz ou formulário**;
2. **importação de planilhas legadas do protocolo IRDER**;
3. **validação e exportação padronizada dos dados**.

---

## 4. Explicação simples para a equipe

Cada linha da planilha representa uma árvore.

No sistema, cada árvore vira um registro, chamado tecnicamente de `TreeRecord`.

A questão principal não é apenas abrir a planilha. O ponto mais importante é fazer o **mapeamento correto das colunas**.

A planilha IRDER tem campos próprios, enquanto o modelo interno do sistema possui campos padronizados. Por isso, precisamos traduzir cada coluna sem perder o sentido técnico.

### Mapeamento inicial dos campos

| Planilha IRDER | Campo no sistema | Observação |
|---|---|---|
| `data` | `date` | data da coleta |
| `Linha` | `plot`, `transect` ou campo próprio | confirmar se representa linha de plantio, parcela ou faixa |
| `Especie` | `species` | espécie/código da espécie |
| `GPS` | `tree_id` | aparentemente é o identificador da árvore |
| `CAP` | `cap_cm` | circunferência à altura do peito, em cm |
| `HT` | `total_height_m` | altura total, em metros |
| `HF` | `stem_height_m` ou campo IRDER específico | altura do fuste |
| `HIC` | `crown_insertion_height_m` | altura de inserção da copa |
| `Densicopa` | `crown_density` | densidade da copa |
| `Forma Fuste` | `stem_form` | forma do fuste |
| `Posição sociológica` | `sociological_position` | posição da árvore no estrato |
| `Característica` | `feature_1` | código qualitativo |
| `Característica2` | `feature_2` | segundo código qualitativo |

### Ponto de atenção

Não é recomendável colocar tudo em `notes` ou `condition`, porque isso empobrece o banco de dados.

Campos como densidade de copa, forma do fuste e posição sociológica têm valor analítico. Eles precisam ser preservados como variáveis próprias.

---

## 5. Estrutura sugerida para o vídeo tutorial

**Duração sugerida:** 8 a 12 minutos  
**Formato:** gravação de tela + narração + trechos curtos de campo  
**Tom:** técnico, direto e demonstrativo

---

### Roteiro do vídeo

| Tempo | Bloco | Conteúdo | Imagem sugerida |
|---|---|---|---|
| 0:00–0:40 | Abertura | Apresentar o problema: planilhas ricas, mas difíceis de consolidar | imagem da planilha IRDER |
| 0:40–1:30 | O que é o Morfocampo | Explicar que o sistema coleta, importa, valida e exporta dados | tela inicial do sistema |
| 1:30–2:30 | Lógica dos dados | Mostrar que cada linha da planilha é uma árvore/registro | zoom em uma linha da planilha |
| 2:30–4:00 | Mapeamento IRDER | Explicar os campos principais: CAP, HT, HF, HIC, densicopa etc. | tabela de mapeamento |
| 4:00–5:30 | Coleta por voz | Demonstrar um exemplo de comando de voz | celular gravando |
| 5:30–6:40 | Importação de planilha | Mostrar exportação CSV e importação pelo painel Admin | LibreOffice + tela Admin |
| 6:40–8:00 | Validação | Mostrar checagem de inconsistências e revisão | aba Validar |
| 8:00–9:30 | Exportação | Mostrar saída CSV/Markdown para análise | botão Exportar + arquivos |
| 9:30–10:30 | Boas práticas | Papel como backup, conferência em campo, padronização de códigos | equipe em campo |
| 10:30–12:00 | Encerramento | Reforçar próximos passos e uso piloto | tela final com resumo |

---

## 6. Texto-base de narração para o vídeo

### Abertura

> Neste vídeo vamos apresentar o Morfocampo, uma ferramenta criada para apoiar a coleta, importação, validação e exportação de dados morfométricos e silvipastoris, com foco no protocolo IRDER.

> A ideia não é substituir o protocolo de campo, nem dispensar o cuidado técnico da equipe. A ideia é reduzir retrabalho, evitar erros de digitação e preservar melhor o significado das variáveis coletadas.

### Problema

> Hoje, os dados do arboreto são registrados em uma planilha com várias colunas importantes: data, linha, espécie, identificador da árvore, CAP, altura total, altura do fuste, altura de inserção da copa, densidade de copa, forma do fuste, posição sociológica e características qualitativas.

> Essa planilha é tecnicamente rica. O problema é que, quando chega a hora de consolidar, validar ou importar esses dados para outras ferramentas, o trabalho pode ficar lento e sujeito a erros.

### Lógica do sistema

> No Morfocampo, cada linha da planilha é tratada como o registro de uma árvore. Internamente, esse registro é organizado como um TreeRecord.

> Para isso funcionar bem, precisamos mapear corretamente cada coluna da planilha para o campo correspondente no sistema. CAP entra como cap_cm. HT entra como altura total. HF deve ser tratada como altura do fuste. HIC como altura de inserção da copa. Densicopa como densidade da copa. Forma do Fuste e Posição Sociológica devem ser mantidas como variáveis próprias, porque têm significado ecológico e silvipastoril.

### Coleta por voz

> Além de importar planilhas existentes, o sistema também permite coleta por voz. O observador pode ditar as informações da árvore diretamente no celular, e o sistema transforma a fala em registro estruturado.

> Um exemplo de comando seria: árvore A-023, espécie Butia odorata, CAP 42,5, altura total 4,8, HF 2,5, HIC 1,5, densicopa 4, forma TL, posição 3, característica PF.

> Depois da transcrição, o registro pode ser conferido visualmente antes de ser validado.

### Importação de planilhas

> Para dados já coletados, o caminho é exportar a planilha do LibreOffice como CSV e importar no painel administrativo do Morfocampo.

> O importador IRDER lê as colunas esperadas, converte os valores e grava os registros no banco SQLite.

> Assim, a equipe consegue aproveitar planilhas antigas sem precisar redigitar tudo.

### Validação e exportação

> Ao final da coleta, o sistema pode validar a campanha, buscando inconsistências, valores fora de faixa, campos ausentes ou registros que precisam de revisão.

> Depois, os dados podem ser exportados em CSV e em relatório Markdown, facilitando o uso posterior em R, QGIS, planilhas ou relatórios técnicos.

### Encerramento

> O ponto central é que o Morfocampo transforma a coleta em um fluxo mais rastreável. A informação nasce no campo, é conferida, validada e exportada de forma padronizada.

> O papel e as marcações de campo seguem importantes como backup e controle. O sistema entra para acelerar o processo e reduzir o retrabalho.

---

## 7. Checklist para gravação do vídeo

### Antes da gravação

- [ ] Separar uma planilha IRDER de exemplo.
- [ ] Exportar uma cópia em CSV.
- [ ] Rodar o sistema localmente com `./run.sh`.
- [ ] Confirmar que o celular acessa o endereço HTTPS do servidor.
- [ ] Testar o microfone no navegador.
- [ ] Preparar uma campanha fictícia para demonstração.
- [ ] Criar 3 a 5 registros de árvore para teste.
- [ ] Conferir se a importação CSV está funcionando.
- [ ] Conferir se a exportação gera CSV e relatório Markdown.

### Durante a gravação

- [ ] Mostrar a planilha original.
- [ ] Explicar rapidamente o significado das colunas.
- [ ] Mostrar a tela inicial do sistema.
- [ ] Demonstrar criação de campanha.
- [ ] Demonstrar coleta por voz.
- [ ] Demonstrar importação IRDER.
- [ ] Demonstrar validação.
- [ ] Demonstrar exportação.
- [ ] Fechar com próximos passos.

### Cuidados de linguagem

Evitar dizer:

- “O sistema resolve tudo sozinho.”
- “Não precisa mais de conferência.”
- “A voz elimina todos os erros.”
- “A planilha antiga está errada.”

Preferir dizer:

- “O sistema reduz retrabalho.”
- “A conferência continua necessária.”
- “A voz acelera a entrada dos dados.”
- “A planilha segue o protocolo de campo; o sistema precisa respeitar esse protocolo.”

---

## 8. Estrutura sugerida para apresentação

**Duração sugerida:** 10 a 15 minutos  
**Número de slides:** 10 a 12 slides  
**Objetivo:** apresentar a lógica do sistema e alinhar a equipe sobre uso, ajustes e próximos passos.

---

### Slide 1 — Título

**Morfocampo: coleta, importação e validação de dados IRDER**

Subtítulo:  
**Do registro em campo à base padronizada para análise**

---

### Slide 2 — O problema

Mensagem principal:

- a planilha IRDER é rica;
- mas a consolidação manual gera retrabalho;
- há risco de perda de significado técnico;
- precisamos padronizar sem empobrecer o protocolo.

Imagem sugerida: captura da planilha IRDER.

---

### Slide 3 — O que o Morfocampo faz

Mostrar os quatro blocos:

1. coleta por voz;
2. importação de planilhas;
3. validação de registros;
4. exportação para análise.

Frase de apoio:

> O sistema não substitui o protocolo; ele operacionaliza o protocolo em ambiente digital.

---

### Slide 4 — Arquitetura geral

Mostrar a arquitetura em três camadas:

| Camada | Função |
|---|---|
| C++20 | parser, validação, relatórios |
| FastAPI + SQLite | servidor web e persistência |
| Interface mobile | coleta, revisão e exportação |

Imagem sugerida: diagrama simples com setas.

---

### Slide 5 — Cada linha é uma árvore

Mensagem principal:

- uma linha da planilha corresponde a um registro individual;
- esse registro vira um `TreeRecord`;
- o banco precisa preservar os campos técnicos.

Imagem sugerida: destacar uma linha da planilha e mostrar seta para “Registro da árvore”.

---

### Slide 6 — Mapeamento dos campos IRDER

Usar tabela resumida:

| IRDER | Sistema |
|---|---|
| Espécie | species |
| GPS | tree_id |
| CAP | cap_cm |
| HT | total_height_m |
| HF | stem_height_m |
| HIC | crown_insertion_height_m |
| Densicopa | crown_density |
| Forma Fuste | stem_form |
| Posição sociológica | sociological_position |
| Características | feature_1 / feature_2 |

---

### Slide 7 — Coleta por voz

Mostrar exemplo:

> árvore A-023, espécie Butia odorata, CAP 42,5, altura total 4,8, HF 2,5, HIC 1,5, densicopa 4, forma TL, posição 3, característica PF.

Pontos a destacar:

- coleta rápida;
- conferência visual;
- possibilidade de correção;
- registro estruturado.

---

### Slide 8 — Importação de planilhas legadas

Mensagem principal:

- planilhas antigas podem ser reaproveitadas;
- exportar do LibreOffice como CSV;
- importar pelo painel Admin;
- o sistema converte para o banco SQLite.

Imagem sugerida: LibreOffice → CSV → Morfocampo → SQLite.

---

### Slide 9 — Validação

Mostrar exemplos de checagens:

- CAP muito alto ou muito baixo;
- altura total ausente;
- espécie sem código padronizado;
- árvore duplicada;
- campo obrigatório vazio;
- inconsistência entre variáveis.

Mensagem:

> A validação não substitui o olhar técnico, mas ajuda a encontrar rapidamente o que precisa ser revisado.

---

### Slide 10 — Exportação e uso posterior

Mostrar saídas possíveis:

- CSV consolidado;
- relatório Markdown;
- uso no R;
- uso no QGIS;
- integração com banco de dados;
- relatórios técnicos.

---

### Slide 11 — Boas práticas de campo

- manter papel ou ficha como backup;
- revisar os registros ainda no campo;
- padronizar códigos antes da campanha;
- registrar observações importantes;
- evitar criar novos códigos sem combinar com a equipe;
- validar antes de exportar.

---

### Slide 12 — Próximos passos

Sugestão de encaminhamentos:

1. confirmar o significado final de cada coluna IRDER;
2. fechar dicionário de dados;
3. testar importação com uma planilha real;
4. validar registros com a equipe de campo;
5. gravar vídeo tutorial;
6. realizar piloto em uma campanha curta;
7. ajustar o sistema a partir do uso real.

---

## 9. Dicionário preliminar de dados IRDER

Este dicionário deve ser revisado pela equipe antes de consolidar o importador.

| Campo | Significado provável | Tipo esperado | Observação |
|---|---|---|---|
| `data` | data da coleta | data | formato `dd/mm/aaaa` |
| `Linha` | linha de plantio/coleta | inteiro ou texto | confirmar conceito operacional |
| `Especie` | código ou nome da espécie | texto | padronizar lista de códigos |
| `GPS` | identificador da árvore | texto ou inteiro | confirmar se é ID da árvore ou ponto GPS |
| `CAP` | circunferência à altura do peito | número decimal | em centímetros |
| `HT` | altura total | número decimal | em metros |
| `HF` | altura do fuste | número decimal | em metros |
| `HIC` | altura de inserção da copa | número decimal | em metros |
| `Densicopa` | densidade de copa | inteiro/categoria | confirmar escala |
| `Forma Fuste` | forma do fuste | texto/código | exemplo: TL, RM, TC |
| `Posição sociológica` | posição no estrato | inteiro/categoria | confirmar escala |
| `Característica` | característica qualitativa 1 | texto/código | exemplo: B1, B2, PF |
| `Característica2` | característica qualitativa 2 | texto/código | exemplo: PF, SE, P3 |

---

## 10. Perguntas que a equipe precisa responder

Antes de fechar o importador IRDER, é importante confirmar:

1. `GPS` é identificador da árvore, ponto GPS, número da etiqueta ou outra coisa?
2. `Linha` representa linha de plantio, parcela, transecto ou outra unidade?
3. `HF` é sempre altura do fuste?
4. `HIC` é altura de inserção da copa?
5. Qual é a escala da `Densicopa`?
6. Quais são os códigos possíveis para `Forma Fuste`?
7. Quais são os códigos possíveis para `Posição sociológica`?
8. Quais são os códigos possíveis para `Característica` e `Característica2`?
9. Existem campos obrigatórios?
10. Quais valores devem acionar alerta de validação?

---

## 11. Prompt para gerar uma apresentação no Gamma, Canva ou ferramenta similar

Use o texto abaixo como prompt-base:

```text
Crie uma apresentação técnica, clara e visual, com 10 a 12 slides, sobre o sistema Morfocampo aplicado ao protocolo IRDER.

Objetivo da apresentação:
explicar para uma equipe de campo, pesquisa e desenvolvimento como o Morfocampo organiza a coleta, importação, validação e exportação de dados morfométricos e silvipastoris.

Mensagem central:
o sistema não substitui o protocolo de campo; ele traduz o protocolo IRDER para um fluxo digital, reduzindo retrabalho, erros de digitação e perda de significado técnico.

Estrutura desejada:
1. Título: Morfocampo — coleta, importação e validação de dados IRDER.
2. Problema: planilhas ricas, mas difíceis de consolidar manualmente.
3. O que o sistema faz: coleta por voz, importação de planilhas, validação e exportação.
4. Arquitetura: núcleo C++20, servidor FastAPI/SQLite e interface mobile.
5. Lógica dos dados: cada linha da planilha é uma árvore/TreeRecord.
6. Mapeamento dos campos IRDER: data, linha, espécie, GPS, CAP, HT, HF, HIC, densicopa, forma do fuste, posição sociológica e características.
7. Coleta por voz: exemplo de comando e revisão do registro.
8. Importação de planilhas legadas: LibreOffice → CSV → Morfocampo → SQLite.
9. Validação dos dados: inconsistências, duplicidades e valores fora de faixa.
10. Exportação: CSV, relatório Markdown, uso em R, QGIS e relatórios técnicos.
11. Boas práticas: papel como backup, conferência em campo e padronização de códigos.
12. Próximos passos: dicionário de dados, teste com planilha real, piloto em campo e ajustes.

Estilo visual:
limpo, técnico, com poucos textos por slide, usando diagramas simples, tabelas resumidas e ícones de campo, árvore, banco de dados, microfone, planilha e validação.

Tom:
didático, objetivo, voltado para alinhamento de equipe.
```

---

## 12. Prompt para gerar roteiro de vídeo com IA

```text
Crie um roteiro de vídeo tutorial de 8 a 12 minutos sobre o Morfocampo, sistema de coleta, importação, validação e exportação de dados morfométricos e silvipastoris do protocolo IRDER.

O roteiro deve conter:
- abertura curta;
- explicação do problema das planilhas;
- demonstração da lógica de que cada linha representa uma árvore;
- explicação do mapeamento das colunas IRDER;
- demonstração da coleta por voz;
- demonstração da importação de planilha CSV;
- demonstração da validação;
- demonstração da exportação;
- encerramento com boas práticas e próximos passos.

Use linguagem técnica, mas acessível para equipe de campo e pesquisa.

Inclua uma tabela com:
tempo aproximado, cena, fala do narrador, imagem/tela sugerida e observações de gravação.
```

---

## 13. Encaminhamento recomendado para a equipe

Para a próxima reunião, a equipe pode trabalhar em cima de três entregas simples:

1. **Dicionário de dados IRDER validado**
   - significado de cada coluna;
   - tipo de dado;
   - escala ou unidade;
   - códigos permitidos;
   - regras de validação.

2. **Planilha exemplo**
   - uma planilha pequena, com 10 a 20 árvores;
   - contendo casos normais e casos com erro proposital;
   - útil para testar importação e validação.

3. **Roteiro de gravação**
   - quem narra;
   - quem demonstra;
   - quais telas serão gravadas;
   - qual planilha será usada;
   - onde será feita a cena de campo.

---

## 14. Frase de fechamento

> O Morfocampo deve ser apresentado como uma ponte entre o protocolo de campo e a análise dos dados. A qualidade continua nascendo no campo; o sistema apenas ajuda a carregar essa qualidade até o relatório final sem derrubar nada no caminho.
