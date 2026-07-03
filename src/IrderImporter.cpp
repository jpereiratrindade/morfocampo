/**
 * IrderImporter.cpp — implementação do importador de planilhas IRDER.
 *
 * Mapeamento de colunas:
 *   data                 → date
 *   Linha                → plot
 *   Especie              → species
 *   GPS                  → tree_id
 *   CAP                  → cap_cm_text
 *   HT                   → total_height_m_text
 *   HF                   → stem_height_m_text
 *   HIC                  → crown_insertion_m_text
 *   Densicopa            → crown_density_text
 *   Forma Fuste          → stem_form
 *   Posição sociológica  → sociological_position
 *   Característica       → trait_1
 *   Característica2      → trait_2
 */

#include "morfocampo/IrderImporter.hpp"
#include "morfocampo/Normalizer.hpp"

#include <algorithm>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace morfocampo::irder {
namespace {

// ---------------------------------------------------------------------------
// Utilitários internos
// ---------------------------------------------------------------------------

std::string trimStr(const std::string& s) {
    const auto first = s.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last  = s.find_last_not_of(" \t\r\n");
    return s.substr(first, last - first + 1);
}

/**
 * Detecta o separador do CSV a partir da primeira linha (cabeçalho).
 * Prioriza ';' pois o LibreOffice BR exporta com ponto-e-vírgula por padrão.
 */
char detectSeparator(const std::string& header_line) {
    const auto count_semi  = std::count(header_line.begin(), header_line.end(), ';');
    const auto count_comma = std::count(header_line.begin(), header_line.end(), ',');
    return (count_semi >= count_comma) ? ';' : ',';
}

/**
 * Parser de linha CSV respeitando campos entre aspas.
 * Funciona com ';' ou ',' como separador.
 */
std::vector<std::string> parseLine(const std::string& line, char sep) {
    std::vector<std::string> fields;
    std::string current;
    bool quoted = false;

    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (quoted) {
            if (c == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                current.push_back('"');
                ++i;
            } else if (c == '"') {
                quoted = false;
            } else {
                current.push_back(c);
            }
        } else {
            if (c == '"') {
                quoted = true;
            } else if (c == sep) {
                fields.push_back(trimStr(current));
                current.clear();
            } else {
                current.push_back(c);
            }
        }
    }
    fields.push_back(trimStr(current));
    return fields;
}

/**
 * Normaliza o nome da coluna para facilitar lookup case-insensitive
 * e remover espaços extras e acentos problemáticos de terminal.
 * Retorna a string em lowercase sem espaços extras (trim).
 */
std::string normalizeColName(std::string name) {
    name = trimStr(name);
    std::transform(name.begin(), name.end(), name.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return name;
}

// Mapa de sinônimos: nome normalizado → nome canônico do campo IRDER
const std::map<std::string, std::string> COL_ALIASES = {
    // data
    {"data",                    "date"},
    // Linha
    {"linha",                   "plot"},
    // Especie / Espécie
    {"especie",                 "species"},
    {"espécie",                 "species"},
    // GPS
    {"gps",                     "tree_id"},
    // CAP
    {"cap",                     "cap_cm"},
    // HT
    {"ht",                      "total_height_m"},
    // HF
    {"hf",                      "stem_height_m"},
    // HIC
    {"hic",                     "crown_insertion_m"},
    // Densicopa
    {"densicopa",               "crown_density"},
    // Forma Fuste
    {"forma fuste",             "stem_form"},
    {"formafuste",              "stem_form"},
    // Posição sociológica
    {"posição sociológica",     "sociological_position"},
    {"posicao sociologica",     "sociological_position"},
    // Característica / Característica2
    {"característica",          "trait_1"},
    {"caracteristica",          "trait_1"},
    {"característica2",         "trait_2"},
    {"caracteristica2",         "trait_2"},
    // Campos nativos morfocampo (para reexportar corretamente)
    {"observer",                "observer"},
    {"observador",              "observer"},
    {"transecto",               "transect"},
    {"transect",                "transect"},
    {"notes",                   "notes"},
    {"observação",              "notes"},
    {"observacao",              "notes"},
    {"latitude",                "latitude"},
    {"longitude",               "longitude"},
    {"dap",                     "dap_cm"},
    {"dap_cm",                  "dap_cm"},
};

/**
 * Resolve um nome de coluna do IRDER para o nome canônico interno.
 * Se não houver sinônimo, retorna o próprio nome normalizado.
 */
std::string resolveColName(const std::string& raw) {
    const auto key = normalizeColName(raw);
    const auto it = COL_ALIASES.find(key);
    if (it != COL_ALIASES.end()) {
        return it->second;
    }
    return key;
}

// ---------------------------------------------------------------------------
// Conversão de linha CSV → TreeRecord
// ---------------------------------------------------------------------------

TreeRecord buildRecord(
    const std::vector<std::string>& canonical_headers,
    const std::vector<std::string>& row,
    std::size_t source_line,
    const std::string& project_id,
    const std::string& campaign_id,
    const std::string& area,
    const std::string& default_observer)
{
    std::map<std::string, std::string> values;
    for (std::size_t i = 0; i < canonical_headers.size() && i < row.size(); ++i) {
        values[canonical_headers[i]] = row[i];
    }

    TreeRecord rec;
    rec.source_line  = source_line;
    rec.project_id   = project_id;
    rec.campaign_id  = campaign_id;
    rec.area         = area;
    rec.source       = "irder_import";
    rec.confidence_flag = "ok";

    // Campos comuns
    rec.date          = values["date"];
    rec.plot          = values["plot"];
    rec.transect      = values["transect"];
    rec.species       = values["species"];
    rec.tree_id       = values["tree_id"];
    rec.observer      = values["observer"].empty() ? default_observer : values["observer"];
    rec.notes         = values["notes"];
    rec.latitude_text  = values["latitude"];
    rec.longitude_text = values["longitude"];

    // Campos de medição — armazenar como texto para o Normalizer converter
    rec.cap_cm_text             = values["cap_cm"];
    rec.dap_cm_text             = values["dap_cm"];
    rec.total_height_m_text     = values["total_height_m"];
    rec.crown_height_m_text     = values["crown_height_m"];
    rec.crown_diameter_ns_m_text = values["crown_diameter_ns_m"];
    rec.crown_diameter_ew_m_text = values["crown_diameter_ew_m"];

    // Campos específicos IRDER
    rec.stem_height_m_text     = values["stem_height_m"];
    rec.crown_insertion_m_text = values["crown_insertion_m"];
    rec.crown_density_text     = values["crown_density"];
    rec.stem_form              = values["stem_form"];
    rec.sociological_position  = values["sociological_position"];
    rec.trait_1                = values["trait_1"];
    rec.trait_2                = values["trait_2"];

    return rec;
}

} // namespace

// ---------------------------------------------------------------------------
// Função pública
// ---------------------------------------------------------------------------

ProcessingResult importIrder(
    const std::filesystem::path& input,
    const std::string& project_id,
    const std::string& campaign_id,
    const std::string& area,
    const std::string& observer)
{
    std::ifstream in(input);
    if (!in) {
        throw std::runtime_error("IrderImporter: nao foi possivel abrir arquivo: " + input.string());
    }

    ProcessingResult result;
    std::string line;
    std::size_t line_number = 0;
    char sep = ';';
    std::vector<std::string> canonical_headers;

    while (std::getline(in, line)) {
        ++line_number;
        // Remove \r do final (Windows line endings)
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) {
            continue;
        }

        if (line_number == 1) {
            // Detecta separador a partir do cabeçalho
            sep = detectSeparator(line);

            // Mapeia cada coluna para seu nome canônico
            const auto raw_headers = parseLine(line, sep);
            canonical_headers.reserve(raw_headers.size());
            for (const auto& h : raw_headers) {
                canonical_headers.push_back(resolveColName(h));
            }
            continue;
        }

        if (canonical_headers.empty()) {
            result.issues.push_back({Severity::Error, line_number, "header",
                "cabeçalho não encontrado antes da linha de dados"});
            break;
        }

        const auto row = parseLine(line, sep);
        result.records.push_back(
            buildRecord(canonical_headers, row, line_number,
                        project_id, campaign_id, area, observer)
        );
    }

    if (result.records.empty() && result.issues.empty()) {
        result.issues.push_back({Severity::Warning, 0, "arquivo",
            "nenhum registro encontrado no CSV IRDER"});
    }

    return result;
}

} // namespace morfocampo::irder
