#include "morfocampo/Validator.hpp"

#include <regex>
#include <set>
#include <string>
#include <unordered_map>

namespace morfocampo::validator {
namespace {

void requireField(std::vector<ValidationIssue>& issues,
                  const TreeRecord& record,
                  const std::string& field,
                  const std::string& value) {
    if (value.empty()) {
        issues.push_back({Severity::Error, record.source_line, field, "campo obrigatorio ausente"});
    }
}

void requirePositive(std::vector<ValidationIssue>& issues,
                     const TreeRecord& record,
                     const std::string& field,
                     const std::optional<double>& value) {
    if (value.has_value() && *value <= 0.0) {
        issues.push_back({Severity::Error, record.source_line, field, "deve ser maior que zero"});
    }
}

void requireNonNegative(std::vector<ValidationIssue>& issues,
                        const TreeRecord& record,
                        const std::string& field,
                        const std::optional<double>& value) {
    if (value.has_value() && *value < 0.0) {
        issues.push_back({Severity::Error, record.source_line, field, "deve ser maior ou igual a zero"});
    }
}

std::string duplicateKey(const TreeRecord& record) {
    return record.project_id + "|" + record.campaign_id + "|" + record.plot + "|" + record.tree_id;
}

} // namespace

std::vector<ValidationIssue> validateRecords(const std::vector<TreeRecord>& records) {
    std::vector<ValidationIssue> issues;
    const std::regex iso_date(R"(^\d{4}-\d{2}-\d{2}$)");
    const std::set<std::string> allowed_conditions{
        "viva", "morta", "rebrote", "dano", "desconhecida"
    };
    std::unordered_map<std::string, std::size_t> first_seen;

    for (const auto& record : records) {
        requireField(issues, record, "project_id", record.project_id);
        requireField(issues, record, "campaign_id", record.campaign_id);
        requireField(issues, record, "plot", record.plot);
        requireField(issues, record, "tree_id", record.tree_id);
        requireField(issues, record, "observer", record.observer);
        requireField(issues, record, "date", record.date);

        if (!record.date.empty() && !std::regex_match(record.date, iso_date)) {
            issues.push_back({Severity::Error, record.source_line, "date", "deve estar no formato ISO YYYY-MM-DD"});
        }
        if (!record.cap_cm.has_value() && !record.dap_cm.has_value()) {
            issues.push_back({Severity::Error, record.source_line, "cap_cm,dap_cm", "informe pelo menos CAP ou DAP"});
        }

        requirePositive(issues, record, "cap_cm", record.cap_cm);
        requirePositive(issues, record, "dap_cm", record.dap_cm);
        requirePositive(issues, record, "total_height_m", record.total_height_m);
        requireNonNegative(issues, record, "crown_height_m", record.crown_height_m);
        requireNonNegative(issues, record, "crown_diameter_ns_m", record.crown_diameter_ns_m);
        requireNonNegative(issues, record, "crown_diameter_ew_m", record.crown_diameter_ew_m);

        if (record.latitude.has_value() && (*record.latitude < -90.0 || *record.latitude > 90.0)) {
            issues.push_back({Severity::Error, record.source_line, "latitude", "deve estar entre -90 e 90"});
        }
        if (record.longitude.has_value() && (*record.longitude < -180.0 || *record.longitude > 180.0)) {
            issues.push_back({Severity::Error, record.source_line, "longitude", "deve estar entre -180 e 180"});
        }
        if (!record.condition.empty() && !allowed_conditions.contains(record.condition)) {
            issues.push_back({Severity::Error, record.source_line, "condition", "condicao fora da lista controlada"});
        }
        if (record.species.empty()) {
            issues.push_back({Severity::Warning, record.source_line, "species", "especie vazia"});
        }

        if (!record.project_id.empty() && !record.campaign_id.empty() &&
            !record.plot.empty() && !record.tree_id.empty()) {
            const auto key = duplicateKey(record);
            const auto [it, inserted] = first_seen.emplace(key, record.source_line);
            if (!inserted) {
                issues.push_back({
                    Severity::Error,
                    record.source_line,
                    "duplicate_key",
                    "arvore duplicada; primeira ocorrencia na linha " + std::to_string(it->second) +
                        "; chave " + key
                });
            }
        }
    }

    return issues;
}

} // namespace morfocampo::validator
