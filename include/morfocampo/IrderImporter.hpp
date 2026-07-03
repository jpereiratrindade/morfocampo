#pragma once

/**
 * IrderImporter.hpp — importador de planilhas do protocolo IRDER.
 *
 * Lê um CSV exportado do LibreOffice (BR) com as colunas do arboreto IRDER
 * e converte cada linha em um TreeRecord do morfocampo.
 *
 * Colunas esperadas no CSV de entrada:
 *   data, Linha, Especie, GPS, CAP, HT, HF, HIC, Densicopa,
 *   Forma Fuste, Posição sociológica, Característica, Característica2
 *
 * O separador é detectado automaticamente (';' ou ',') a partir do cabeçalho.
 */

#include "morfocampo/TreeRecord.hpp"

#include <filesystem>
#include <string>

namespace morfocampo::irder {

/**
 * Importa um CSV no formato IRDER e retorna um ProcessingResult.
 *
 * @param input       Caminho do CSV exportado do LibreOffice.
 * @param project_id  Identificador do projeto (preenchido via CLI).
 * @param campaign_id Identificador da campanha (preenchido via CLI).
 * @param area        Área/localidade (preenchido via CLI).
 * @param observer    Observador padrão (opcional; usado se a coluna estiver ausente).
 */
ProcessingResult importIrder(
    const std::filesystem::path& input,
    const std::string& project_id,
    const std::string& campaign_id,
    const std::string& area,
    const std::string& observer = ""
);

} // namespace morfocampo::irder
