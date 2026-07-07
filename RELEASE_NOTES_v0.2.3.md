# Morfocampo v0.2.3

Release patch para exibir automaticamente a versão instalada do sistema na interface web.

## Destaques

- Remove a versão fixa `0.2.0` do servidor web.
- Lê a versão instalada de `/var/lib/morfocampo/installed-version.txt` no MorfoNode.
- Usa `git describe --tags --always --dirty` em ambiente de desenvolvimento.
- Expõe `version`, `commit`, `installed_at` e `version_source` em `GET /api/status`.
- Mostra a versão no cabeçalho da tela inicial da interface web.
- Salva QR codes gerados manualmente em `~/Downloads/morfocampo-qrcodes` por padrão.
- Padroniza `tmp/` como diretório local ignorado para saídas de desenvolvimento.

## Validação

- Build C++ com CMake.
- Testes CTest passando: 6/6.
- Checagem de sintaxe Python.
- Checagem de sintaxe dos scripts de deploy.
