# Morfocampo v0.2.1

Release de manutenção para preparar uso do MorfoNode em Raspberry Pi com operação offline, QR code de acesso e separação entre token local da aplicação e token do Hugging Face.

## Destaques

- Adiciona licença GNU GPL v3.0 somente.
- Remove referências públicas ao protocolo inicial usado como ponto de partida.
- Adiciona documentação operacional de privacidade, LGPD, retenção e descarte.
- Adiciona aviso de privacidade na interface web.
- Adiciona QR code de acesso no `run.sh` para desenvolvimento.
- Adiciona QR code persistente do MorfoNode em `/var/lib/morfocampo/morfonode-access-qr.svg`.
- Adiciona comando neutro `import-silvipastoril`, mantendo `import-irder` como compatibilidade.
- Separa `MORFOCAMPO_AUTH_TOKEN` de `MORFOCAMPO_HF_TOKEN`.

## MorfoNode

O instalador passa a gerar um QR code de acesso para uso headless:

```text
/var/lib/morfocampo/morfonode-access-qr.svg
```

Por padrão, o QR code aponta para:

```text
https://morfocampo.local:8011
```

O token local do app fica desativado por padrão. Para proteger rotas `/api`, defina explicitamente:

```bash
MORFOCAMPO_AUTH_TOKEN='token-local'
```

Para autenticar download do modelo Whisper no Hugging Face, use:

```bash
MORFOCAMPO_HF_TOKEN='hf_token'
```

## Validação

- Build C++ com CMake.
- Testes CTest passando: 6/6.
- Checagem de sintaxe Python.
- Checagem de sintaxe dos scripts de deploy.

## Atualização

No MorfoNode com internet e CI aprovado para a tag:

```bash
sudo morfocampo-update
```
