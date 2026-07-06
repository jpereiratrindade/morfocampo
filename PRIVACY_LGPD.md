# Privacidade, LGPD e armazenamento local

Este documento descreve os cuidados de privacidade do Morfocampo em uso local de campo. Ele não substitui análise jurídica da instituição responsável pela coleta.

## Escopo

O Morfocampo é uma ferramenta local de coleta, validação e exportação de dados de campo. Em uso padrão, os dados ficam no equipamento que executa o servidor, como notebook ou MorfoNode/Raspberry Pi, e nos arquivos exportados pelo operador.

## Dados tratados

O sistema pode registrar:

- nome ou identificação do observador;
- parcela, campanha, área, data e registros de coleta;
- texto transcrito ou digitado em `raw_input`;
- arquivos de áudio gravados durante a coleta;
- metadados técnicos de operação, como data/hora de gravação e nomes de arquivos.

Evite registrar dados pessoais desnecessários em observações livres, transcrições ou nomes de campanha.

## Finalidade

Os dados são tratados para:

- documentar a autoria operacional dos registros;
- permitir auditoria, correção e validação da coleta;
- preservar evidência documental por áudio quando habilitada;
- exportar resultados para análise técnica posterior.

## Cookies e armazenamento no navegador

O Morfocampo não usa cookies HTTP para rastreamento, publicidade ou analytics.

O frontend usa `localStorage` do navegador para:

- guardar o token local de acesso, quando `MORFOCAMPO_AUTH_TOKEN` está ativo;
- guardar o nome do observador para pré-preenchimento;
- registrar que o aviso de privacidade foi reconhecido naquele aparelho.

Esses dados ficam no próprio navegador usado em campo e podem ser apagados limpando os dados do site no navegador.

## Armazenamento no servidor local

O servidor local grava:

- banco SQLite, conforme o caminho definido por `--db`;
- áudios em `--audio-dir`;
- arquivos exportados quando o operador realiza exportação ou backup.

Em MorfoNode, os caminhos padrão ficam sob `/var/lib/morfocampo/`.

## Retenção e descarte

A política de retenção deve ser definida pela instituição ou responsável pela campanha. Como prática mínima:

- mantenha os dados apenas pelo tempo necessário à validação e auditoria;
- exporte e arquive os dados em local institucional definido;
- remova bancos, áudios e backups de aparelhos compartilhados após a consolidação;
- proteja backups e arquivos exportados com controles equivalentes aos dados originais.

## Segurança operacional

Recomendações:

- habilite `MORFOCAMPO_AUTH_TOKEN` em redes compartilhadas;
- use HTTPS local quando possível;
- limite o acesso físico ao MorfoNode/notebook;
- evite expor o servidor fora da rede local de campo;
- revise permissões dos diretórios de banco, áudio e backup;
- não reutilize tokens entre campanhas sensíveis.

## Responsabilidades

O operador ou instituição controladora deve informar a equipe de campo sobre a coleta de nome/identificação, áudio e transcrição, além de definir base legal, retenção, descarte e procedimentos de atendimento a titulares quando aplicável.
