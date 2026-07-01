# Exemplos morfocampo

- `template_arvores.csv`: CSV minimo para preenchimento e validacao.
- `fala_estruturada.txt`: frases curtas simulando fala transcrita.
- `transcricoes_exemplo.txt`: transcricoes controladas, uma arvore por linha.

Comandos:

```sh
morfocampo validate --input examples/template_arvores.csv --out out
morfocampo parse-voice --input examples/fala_estruturada.txt --out out/dados_por_voz.csv
morfocampo parse-transcript --input examples/transcricoes_exemplo.txt --out out/transcricao_convertida.csv
```
