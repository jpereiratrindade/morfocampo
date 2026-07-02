#include "morfocampo/Report.hpp"

#include <algorithm>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>

namespace morfocampo::report {

void writeValidationReport(const std::filesystem::path& output,
                           const std::vector<TreeRecord>& records,
                           const std::vector<ValidationIssue>& issues) {
    if (output.has_parent_path()) {
        std::filesystem::create_directories(output.parent_path());
    }
    std::ofstream out(output);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever relatorio: " + output.string());
    }

    std::size_t warning_count = 0;
    std::size_t error_count = 0;
    std::set<std::size_t> records_with_error;
    std::map<std::size_t, std::vector<ValidationIssue>> errors_by_line;
    std::vector<ValidationIssue> duplicates;
    std::size_t review_count = 0;

    for (const auto& record : records) {
        if (record.confidence_flag == "revisar" ||
            record.confidence_flag == "incompleto" ||
            record.confidence_flag == "erro") {
            ++review_count;
        }
    }

    for (const auto& issue : issues) {
        if (issue.severity == Severity::Warning) {
            ++warning_count;
        } else {
            ++error_count;
            records_with_error.insert(issue.line);
            errors_by_line[issue.line].push_back(issue);
            if (issue.field == "duplicate_key") {
                duplicates.push_back(issue);
            }
        }
    }

    const auto valid_count = records.size() >= records_with_error.size()
        ? records.size() - records_with_error.size()
        : 0;

    out << "# Relatorio de validacao\n\n";
    out << "## Resumo\n\n";
    out << "- Total de registros: " << records.size() << '\n';
    out << "- Registros validos: " << valid_count << '\n';
    out << "- Registros com erro: " << records_with_error.size() << '\n';
    out << "- Registros para revisar (confidence_flag): " << review_count << '\n';
    out << "- Erros: " << error_count << '\n';
    out << "- Avisos: " << warning_count << "\n\n";

    // --- Seção acionável: registros que precisam de atenção imediata ---
    out << "## Registros para revisar\n\n";
    bool has_review = false;
    for (const auto& record : records) {
        const auto& flag = record.confidence_flag;
        if (flag == "revisar" || flag == "incompleto" || flag == "erro") {
            has_review = true;
            out << "- **" << (record.tree_id.empty() ? "(sem id)" : record.tree_id)
                << "** [" << flag << "]";
            if (!record.raw_input.empty()) {
                out << " — `" << record.raw_input << '`';
            }
            out << '\n';
        }
    }
    if (!has_review) {
        out << "Nenhum registro com flag de revisao.\n";
    }
    out << '\n';

    out << "## Erros por linha\n\n";
    if (errors_by_line.empty()) {
        out << "Nenhum erro encontrado.\n\n";
    } else {
        for (const auto& [line, line_issues] : errors_by_line) {
            out << "### Linha " << line << "\n\n";
            auto record_it = std::find_if(records.begin(), records.end(), [line](const TreeRecord& record) {
                return record.source_line == line;
            });
            if (record_it != records.end() && !record_it->raw_input.empty()) {
                out << "Frase original: `" << record_it->raw_input << "`\n\n";
            }
            for (const auto& issue : line_issues) {
                out << "- `" << issue.field << "`: " << issue.message << '\n';
            }
            out << '\n';
        }
    }

    out << "## Duplicidades encontradas\n\n";
    if (duplicates.empty()) {
        out << "Nenhuma duplicidade encontrada.\n\n";
    } else {
        for (const auto& issue : duplicates) {
            out << "- Linha " << issue.line << ": " << issue.message << '\n';
        }
        out << '\n';
    }

    out << "## Avisos\n\n";
    bool has_warning = false;
    for (const auto& issue : issues) {
        if (issue.severity == Severity::Warning) {
            has_warning = true;
            out << "- Linha " << issue.line << ", `" << issue.field << "`: " << issue.message << '\n';
            auto record_it = std::find_if(records.begin(), records.end(), [&issue](const TreeRecord& record) {
                return record.source_line == issue.line;
            });
            if (record_it != records.end() && !record_it->raw_input.empty()) {
                out << "  - Frase original: `" << record_it->raw_input << "`\n";
            }
        }
    }
    if (!has_warning) {
        out << "Nenhum aviso encontrado.\n";
    }
}

} // namespace morfocampo::report
