# Morfocampo v0.2.4

Release patch para melhorar as opções de exportação na interface web.

## Destaques

- Adiciona exportação direta em CSV pela interface web.
- Adiciona exportação SQL da campanha para backup técnico/reprodutibilidade.
- Mantém o pacote ZIP de exportação e passa a incluir CSV, relatório e dump SQL.
- Documenta os endpoints `export.csv` e `export.sql`.

## Validação

- Build C++ com CMake.
- Testes CTest passando: 6/6.
- Checagem de sintaxe Python.
- Checagem de sintaxe dos scripts de deploy.
