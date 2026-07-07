# Morfocampo v0.2.2

Release patch para corrigir e completar o fluxo headless do MorfoNode em Raspberry Pi.

## Destaques

- Adiciona script reutilizável `deploy/generate_morfonode_qr.py`.
- Gera QR code PNG do site em `/var/lib/morfocampo/morfonode-site-qr.png`.
- Gera QR code PNG do Wi-Fi em `/var/lib/morfocampo/morfonode-wifi-qr.png`.
- Mantém `/var/lib/morfocampo/morfonode-access-qr.png` como cópia compatível do QR do site.
- Mantém `/var/lib/morfocampo/morfonode-access-qr.svg` para impressão vetorial.
- Corrige a senha padrão do hotspot para `labecomc`.
- Registra `MORFOCAMPO_WIFI_SSID` e `MORFOCAMPO_WIFI_PASSWORD` em `deploy/morfonode.env.example`.
- Documenta que Android/iOS podem exigir confirmação para conectar/salvar a rede Wi-Fi.

## MorfoNode

O instalador passa a gerar os arquivos:

```text
/var/lib/morfocampo/morfonode-access-qr.svg
/var/lib/morfocampo/morfonode-site-qr.png
/var/lib/morfocampo/morfonode-access-qr.png
/var/lib/morfocampo/morfonode-wifi-qr.png
```

Uso em campo:

1. escaneie `morfonode-wifi-qr.png`;
2. confirme a conexão à rede `MORFOCAMPO`;
3. escaneie `morfonode-site-qr.png` para abrir `https://morfocampo.local:8011`.

O QR do Wi-Fi não habilita o Wi-Fi sozinho; o sistema operacional do celular pode exigir confirmação do usuário.

## Validação

- Build C++ com CMake.
- Testes CTest passando: 6/6.
- Checagem de sintaxe Python.
- Checagem de sintaxe dos scripts de deploy.
- Geração local dos QR codes validada com `python3 deploy/generate_morfonode_qr.py`.

## Atualização

No MorfoNode com internet e CI aprovado para a tag:

```bash
sudo morfocampo-update
```
