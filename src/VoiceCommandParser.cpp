#include "morfocampo/VoiceCommandParser.hpp"

#include "morfocampo/Normalizer.hpp"

#include <fstream>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace morfocampo::voice {
namespace {

std::string lower(std::string text) {
    return normalizer::lowercaseAscii(std::move(text));
}

std::string cleanCommandPrefix(std::string text) {
    text = std::regex_replace(text, std::regex(R"(\b(?:nova|novo|salvar)\b)", std::regex::icase), " ");
    return normalizer::normalizeSpaces(std::move(text));
}

bool capture(const std::string& text, const std::regex& pattern, std::string& value) {
    std::smatch match;
    if (!std::regex_search(text, match, pattern) || match.size() < 2) {
        return false;
    }
    value = normalizer::trim(match[1].str());
    return true;
}

std::string trailingText(const std::string& value) {
    auto text = normalizer::trim(value);
    while (!text.empty() && (text.back() == ';' || text.back() == ',' || text.back() == '.')) {
        text.pop_back();
    }
    return normalizer::trim(text);
}

void applyDefaults(TreeRecord& record, const SessionDefaults& defaults) {
    record.project_id = defaults.project_id;
    record.campaign_id = defaults.campaign_id;
    record.area = defaults.area;
    record.plot = defaults.plot;
    record.transect = defaults.transect;
    record.observer = defaults.observer;
    record.date = defaults.date;
}

void updateConfidence(TreeRecord& record, std::size_t warning_count) {
    if (record.tree_id.empty() || (record.cap_cm_text.empty() && record.dap_cm_text.empty())) {
        record.confidence_flag = "erro";
        return;
    }
    if (warning_count > 0) {
        record.confidence_flag = "revisar";
        return;
    }
    if (record.species.empty()) {
        record.confidence_flag = "incompleto";
        return;
    }
    record.confidence_flag = "ok";
}

} // namespace

ProcessingResult parseVoiceLine(const std::string& line,
                                std::size_t line_number,
                                const SessionDefaults& defaults) {
    ProcessingResult result;
    TreeRecord record;
    applyDefaults(record, defaults);
    record.source_line = line_number;
    record.source = "voice_text";
    record.raw_input = line;

    const std::string text = cleanCommandPrefix(line);
    const auto flags = std::regex::ECMAScript | std::regex::icase;
    std::string value;
    std::size_t warning_count = 0;

    // Detectar intenção de correção ANTES de limpar o prefixo
    if (std::regex_search(line, std::regex(R"(\bcorrigir\b)", std::regex::icase))) {
        result.is_correction = true;
    }

    if (capture(text, std::regex(R"((?:arvore|árvore)\s+([^;]+?)(?=\s+(?:projeto|campanha|parcela|transecto|especie|espécie|cap|dap|circunfer|diametro|diâmetro|altura|copa|condi|observador|observa|data|lat|lon)\b|;|$))", flags), value)) {
        record.tree_id = trailingText(value);
        // Remove espaços internos substituindo por hífen (ex: "A 023" -> "A-023")
        record.tree_id = std::regex_replace(record.tree_id, std::regex(R"(\s+)"), "-");
    }
    if (capture(text, std::regex(R"(projeto\s+([A-Za-z0-9_.-]+))", flags), value)) {
        record.project_id = trailingText(value);
    }
    if (capture(text, std::regex(R"(campanha\s+([A-Za-z0-9_.-]+))", flags), value)) {
        record.campaign_id = trailingText(value);
    }
    if (capture(text, std::regex(R"(parcela\s+([A-Za-z0-9_.-]+))", flags), value)) {
        record.plot = trailingText(value);
    }
    if (capture(text, std::regex(R"(transecto\s+([A-Za-z0-9_.-]+))", flags), value)) {
        record.transect = trailingText(value);
    }
    if (capture(text, std::regex(R"(area\s+([^;]+?)(?=\s+(?:projeto|campanha|parcela|transecto|arvore|árvore|especie|espécie|cap|dap|circunfer|diametro|diâmetro|altura|copa|condi|observador|observa|data|lat|lon)\b|;|$))", flags), value)) {
        record.area = trailingText(value);
    }
    if (capture(text, std::regex(R"((?:especie|espécie)\s+([^;]+?)(?=\s+(?:cap|dap|circunfer|diametro|diâmetro|altura|copa|condi|observa|data|lat|lon)\b|;|$))", flags), value)) {
        record.species = trailingText(value);
    }
    if (capture(text, std::regex(R"((?:cap|circunfer[eê]ncia(?:\s+[aà]\s+altura\s+do\s+peito)?)\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.cap_cm_text = value;
    }
    if (capture(text, std::regex(R"((?:dap|di[aâ]metro(?:\s+[aà]\s+altura\s+do\s+peito)?)\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.dap_cm_text = value;
    }
    if (capture(text, std::regex(R"((?:altura\s+total|altura)\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.total_height_m_text = value;
    }
    if (capture(text, std::regex(R"(altura\s+da\s+copa\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.crown_height_m_text = value;
    }
    if (capture(text, std::regex(R"(copa\s+(?:norte-sul|ns)\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.crown_diameter_ns_m_text = value;
    }
    if (capture(text, std::regex(R"(copa\s+(?:leste-oeste|leste\s+oeste|ew|lo)\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.crown_diameter_ew_m_text = value;
    }
    if (capture(text, std::regex(R"((?:condicao|condição)\s+(viva|morta|rebrote|dano|desconhecida))", flags), value)) {
        record.condition = value;
    } else if (std::regex_search(lower(text), std::regex(R"(\b(viva|morta|rebrote|dano|desconhecida)\b)"))) {
        std::smatch match;
        const auto lowered = lower(text);
        std::regex_search(lowered, match, std::regex(R"(\b(viva|morta|rebrote|dano|desconhecida)\b)"));
        record.condition = match[1].str();
    }
    if (capture(text, std::regex(R"(observador\s+([^;]+?)(?=\s+(?:data|arvore|árvore|especie|espécie|cap|dap|circunfer|diametro|diâmetro|altura|copa|condi|observa|lat|lon)\b|;|$))", flags), value)) {
        record.observer = trailingText(value);
    }
    if (capture(text, std::regex(R"(data\s+([0-9]{4}-[0-9]{2}-[0-9]{2}))", flags), value)) {
        record.date = value;
    }
    if (capture(text, std::regex(R"(observa[cç][aã]o\s+([^;]+))", flags), value)) {
        record.notes = trailingText(value);
    }
    if (capture(text, std::regex(R"(lat(?:itude)?\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.latitude_text = value;
    }
    if (capture(text, std::regex(R"(lon(?:gitude)?\s+([+-]?[0-9]+(?:[,.][0-9]+)?))", flags), value)) {
        record.longitude_text = value;
    }

    if (record.tree_id.empty()) {
        result.issues.push_back({Severity::Error, line_number, "tree_id", "fala sem identificacao de arvore"});
    }
    if (record.cap_cm_text.empty() && record.dap_cm_text.empty()) {
        result.issues.push_back({Severity::Error, line_number, "cap_cm,dap_cm", "fala sem CAP ou DAP"});
    }
    if (record.species.empty()) {
        // Não incrementa warning_count para não forçar status "revisar", apenas deixa "incompleto"
        result.issues.push_back({Severity::Warning, line_number, "species", "especie ausente na fala"});
    }

    updateConfidence(record, warning_count);
    result.records.push_back(std::move(record));
    return result;
}

ProcessingResult parseVoiceFile(const std::filesystem::path& input,
                                const SessionDefaults& defaults) {
    std::ifstream in(input);
    if (!in) {
        throw std::runtime_error("nao foi possivel abrir arquivo de fala estruturada: " + input.string());
    }

    ProcessingResult result;
    std::string line;
    std::size_t line_number = 0;
    while (std::getline(in, line)) {
        ++line_number;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (normalizer::trim(line).empty()) {
            continue;
        }
        auto parsed = parseVoiceLine(line, line_number, defaults);
        result.records.insert(result.records.end(), parsed.records.begin(), parsed.records.end());
        result.issues.insert(result.issues.end(), parsed.issues.begin(), parsed.issues.end());
    }
    return result;
}

} // namespace morfocampo::voice
