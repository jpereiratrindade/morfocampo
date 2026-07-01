#include "morfocampo/Csv.hpp"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>

namespace morfocampo::csv {
namespace {

std::string formatNumber(const std::optional<double>& value) {
    if (!value.has_value()) {
        return {};
    }
    std::ostringstream out;
    out << std::fixed << std::setprecision(6) << *value;
    std::string text = out.str();
    while (text.size() > 1 && text.back() == '0') {
        text.pop_back();
    }
    if (!text.empty() && text.back() == '.') {
        text.pop_back();
    }
    return text;
}

std::string sourceName(MeasurementSource source) {
    switch (source) {
        case MeasurementSource::Observed:
            return "observed";
        case MeasurementSource::Derived:
            return "derived";
        case MeasurementSource::Missing:
            return "missing";
    }
    return "missing";
}

std::string csvEscape(const std::string& value) {
    if (value.find_first_of(",\"\n\r") == std::string::npos) {
        return value;
    }
    std::string escaped = "\"";
    for (char c : value) {
        if (c == '"') {
            escaped += "\"\"";
        } else {
            escaped.push_back(c);
        }
    }
    escaped.push_back('"');
    return escaped;
}

std::string jsonEscape(const std::string& value) {
    std::string out;
    for (unsigned char c : value) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    out += "\\u00";
                    const char* hex = "0123456789abcdef";
                    out.push_back(hex[(c >> 4) & 0x0f]);
                    out.push_back(hex[c & 0x0f]);
                } else {
                    out.push_back(static_cast<char>(c));
                }
        }
    }
    return out;
}

void writeCsvRow(std::ostream& out, const std::vector<std::string>& values) {
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i > 0) {
            out << ',';
        }
        out << csvEscape(values[i]);
    }
    out << '\n';
}

std::vector<std::string> recordToRow(const TreeRecord& record) {
    return {
        record.project_id,
        record.campaign_id,
        record.area,
        record.plot,
        record.transect,
        record.tree_id,
        record.species,
        formatNumber(record.cap_cm),
        formatNumber(record.dap_cm),
        formatNumber(record.total_height_m),
        formatNumber(record.crown_height_m),
        formatNumber(record.crown_diameter_ns_m),
        formatNumber(record.crown_diameter_ew_m),
        record.condition,
        record.observer,
        record.date,
        formatNumber(record.latitude),
        formatNumber(record.longitude),
        record.notes,
        record.source,
        record.confidence_flag,
        record.raw_input
    };
}

TreeRecord rowToRecord(const std::vector<std::string>& headers,
                       const std::vector<std::string>& row,
                       std::size_t source_line) {
    std::map<std::string, std::string> values;
    for (std::size_t i = 0; i < headers.size() && i < row.size(); ++i) {
        values[headers[i]] = row[i];
    }

    TreeRecord record;
    record.source_line = source_line;
    record.project_id = values["project_id"];
    record.campaign_id = values["campaign_id"];
    record.area = values["area"];
    record.plot = values["plot"];
    record.transect = values["transect"];
    record.tree_id = values["tree_id"];
    record.species = values["species"];
    record.cap_cm_text = values["cap_cm"];
    record.dap_cm_text = values["dap_cm"];
    record.total_height_m_text = values["total_height_m"];
    record.crown_height_m_text = values["crown_height_m"];
    record.crown_diameter_ns_m_text = values["crown_diameter_ns_m"];
    record.crown_diameter_ew_m_text = values["crown_diameter_ew_m"];
    record.condition = values["condition"];
    record.observer = values["observer"];
    record.date = values["date"];
    record.latitude_text = values["latitude"];
    record.longitude_text = values["longitude"];
    record.notes = values["notes"];
    record.source = values["source"].empty() ? "csv" : values["source"];
    record.confidence_flag = values["confidence_flag"].empty() ? "ok" : values["confidence_flag"];
    record.raw_input = values["raw_input"];
    return record;
}

void ensureOutput(const std::filesystem::path& output) {
    if (output.has_parent_path()) {
        std::filesystem::create_directories(output.parent_path());
    }
}

} // namespace

std::vector<std::string> defaultTreeHeaders() {
    return {
        "project_id",
        "campaign_id",
        "area",
        "plot",
        "transect",
        "tree_id",
        "species",
        "cap_cm",
        "dap_cm",
        "total_height_m",
        "crown_height_m",
        "crown_diameter_ns_m",
        "crown_diameter_ew_m",
        "condition",
        "observer",
        "date",
        "latitude",
        "longitude",
        "notes",
        "source",
        "confidence_flag",
        "raw_input"
    };
}

std::vector<std::string> parseCsvLine(const std::string& line) {
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
            } else if (c == ',') {
                fields.push_back(current);
                current.clear();
            } else {
                current.push_back(c);
            }
        }
    }
    fields.push_back(current);
    return fields;
}

ProcessingResult readTrees(const std::filesystem::path& input) {
    std::ifstream in(input);
    if (!in) {
        throw std::runtime_error("nao foi possivel abrir CSV: " + input.string());
    }

    ProcessingResult result;
    std::string line;
    std::size_t line_number = 0;
    std::vector<std::string> headers;

    while (std::getline(in, line)) {
        ++line_number;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line_number == 1) {
            headers = parseCsvLine(line);
            const auto expected = defaultTreeHeaders();
            for (const auto& name : expected) {
                if (std::find(headers.begin(), headers.end(), name) == headers.end()) {
                    result.issues.push_back({Severity::Warning, 1, name, "coluna esperada ausente no CSV"});
                }
            }
            continue;
        }
        if (line.empty()) {
            continue;
        }
        result.records.push_back(rowToRecord(headers, parseCsvLine(line), line_number));
    }

    return result;
}

void writeTreesCsv(const std::filesystem::path& output,
                   const std::vector<TreeRecord>& records) {
    ensureOutput(output);
    std::ofstream out(output);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever CSV: " + output.string());
    }
    writeCsvRow(out, defaultTreeHeaders());
    for (const auto& record : records) {
        writeCsvRow(out, recordToRow(record));
    }
}

void writeTreesJsonl(const std::filesystem::path& output,
                     const std::vector<TreeRecord>& records) {
    ensureOutput(output);
    std::ofstream out(output);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever JSONL: " + output.string());
    }

    for (const auto& record : records) {
        out << '{'
            << "\"project_id\":\"" << jsonEscape(record.project_id) << "\","
            << "\"campaign_id\":\"" << jsonEscape(record.campaign_id) << "\","
            << "\"area\":\"" << jsonEscape(record.area) << "\","
            << "\"plot\":\"" << jsonEscape(record.plot) << "\","
            << "\"transect\":\"" << jsonEscape(record.transect) << "\","
            << "\"tree_id\":\"" << jsonEscape(record.tree_id) << "\","
            << "\"species\":\"" << jsonEscape(record.species) << "\",";

        out << "\"cap_cm\":";
        if (record.cap_cm.has_value()) {
            out << formatNumber(record.cap_cm);
        } else {
            out << "null";
        }
        out << ",\"cap_source\":\"" << sourceName(record.cap_source) << "\",";

        out << "\"dap_cm\":";
        if (record.dap_cm.has_value()) {
            out << formatNumber(record.dap_cm);
        } else {
            out << "null";
        }
        out << ",\"dap_source\":\"" << sourceName(record.dap_source) << "\",";

        out << "\"total_height_m\":";
        if (record.total_height_m.has_value()) { out << formatNumber(record.total_height_m); } else { out << "null"; }
        out << ",\"crown_height_m\":";
        if (record.crown_height_m.has_value()) { out << formatNumber(record.crown_height_m); } else { out << "null"; }
        out << ",\"crown_diameter_ns_m\":";
        if (record.crown_diameter_ns_m.has_value()) { out << formatNumber(record.crown_diameter_ns_m); } else { out << "null"; }
        out << ",\"crown_diameter_ew_m\":";
        if (record.crown_diameter_ew_m.has_value()) { out << formatNumber(record.crown_diameter_ew_m); } else { out << "null"; }
        out << ",\"condition\":\"" << jsonEscape(record.condition) << "\","
            << "\"observer\":\"" << jsonEscape(record.observer) << "\","
            << "\"date\":\"" << jsonEscape(record.date) << "\",";
        out << "\"latitude\":";
        if (record.latitude.has_value()) { out << formatNumber(record.latitude); } else { out << "null"; }
        out << ",\"longitude\":";
        if (record.longitude.has_value()) { out << formatNumber(record.longitude); } else { out << "null"; }
        out << ",\"notes\":\"" << jsonEscape(record.notes) << "\","
            << "\"source\":\"" << jsonEscape(record.source) << "\","
            << "\"confidence_flag\":\"" << jsonEscape(record.confidence_flag) << "\","
            << "\"raw_input\":\"" << jsonEscape(record.raw_input) << "\""
            << "}\n";
    }
}

void writeTemplateCsv(const std::filesystem::path& output) {
    ensureOutput(output);
    std::ofstream out(output);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever template: " + output.string());
    }
    writeCsvRow(out, defaultTreeHeaders());
    writeCsvRow(out, {
        "PRJ-BUTIA",
        "2026-01",
        "Restinga norte",
        "P01",
        "T01",
        "A-001",
        "Butia odorata",
        "42,5",
        "",
        "4,8",
        "2,1",
        "3,4",
        "2,9",
        "viva",
        "Pedro",
        "2026-07-01",
        "-30.0341",
        "-51.2177",
        "CAP observado em campo",
        "csv",
        "ok",
        ""
    });
    writeCsvRow(out, {
        "PRJ-BUTIA",
        "2026-01",
        "Restinga norte",
        "P01",
        "T01",
        "A-002",
        "",
        "",
        "13.8",
        "5.1",
        "1.9",
        "3.0",
        "2.7",
        "desconhecida",
        "Ana",
        "2026-07-01",
        "-30,0342",
        "-51,2178",
        "DAP observado; especie a confirmar",
        "csv",
        "incompleto",
        ""
    });
}

void writeVoiceExampleFile(const std::filesystem::path& output) {
    ensureOutput(output);
    std::ofstream out(output);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever exemplo de fala: " + output.string());
    }
    out
        << "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; observador Pedro; data 2026-07-01; nova arvore A-023; especie Butia odorata; CAP 42,5; altura total 4,8; altura da copa 2,1; copa norte-sul 3,4; copa leste-oeste 2,9; condicao viva; salvar\n"
        << "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; observador Pedro; data 2026-07-01; arvore A-024; CAP 38,2; altura total 5,1; condicao viva; observacao tronco inclinado; salvar\n"
        << "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; observador Pedro; data 2026-07-01; corrigir arvore A-024; CAP 39,2; salvar\n"
        << "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; observador Ana; data 2026-07-01; nova arvore A-025; DAP 13,4; altura total 4,2; condicao dano; salvar\n";
}

} // namespace morfocampo::csv
