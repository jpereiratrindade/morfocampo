#include "morfocampo/Normalizer.hpp"

#include <algorithm>
#include <cctype>
#include <charconv>
#include <cmath>
#include <numbers>
#include <sstream>

namespace morfocampo::normalizer {
namespace {

ValidationIssue numberError(std::size_t line, const std::string& field, const std::string& value) {
    return {Severity::Error, line, field, "numero invalido: '" + value + "'"};
}

void parseNumberField(const TreeRecord& input,
                      std::vector<ValidationIssue>& issues,
                      const std::string& field,
                      const std::string& text,
                      std::optional<double>& target) {
    const auto parsed = parseOptionalDecimal(text);
    if (!parsed.ok) {
        issues.push_back(numberError(input.source_line, field, text));
        return;
    }
    target = parsed.value;
}

} // namespace

std::string trim(std::string value) {
    const auto first = std::find_if_not(value.begin(), value.end(), [](unsigned char c) {
        return std::isspace(c) != 0;
    });
    const auto last = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char c) {
        return std::isspace(c) != 0;
    }).base();
    if (first >= last) {
        return {};
    }
    return std::string(first, last);
}

std::string normalizeSpaces(std::string value) {
    value = trim(std::move(value));
    std::string result;
    bool previous_space = false;
    for (unsigned char c : value) {
        if (std::isspace(c) != 0) {
            if (!previous_space) {
                result.push_back(' ');
            }
            previous_space = true;
            continue;
        }
        result.push_back(static_cast<char>(c));
        previous_space = false;
    }
    return result;
}

std::string lowercaseAscii(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

NumberParseResult parseOptionalDecimal(const std::string& text) {
    std::string value = trim(text);
    if (value.empty()) {
        return {};
    }

    value.erase(std::remove_if(value.begin(), value.end(), [](unsigned char c) {
        return std::isspace(c) != 0;
    }), value.end());

    const bool has_comma = value.find(',') != std::string::npos;
    const bool has_dot = value.find('.') != std::string::npos;
    if (has_comma && has_dot) {
        return {.value = std::nullopt, .had_text = true, .ok = false};
    }
    std::replace(value.begin(), value.end(), ',', '.');

    double parsed = 0.0;
    const char* begin = value.data();
    const char* end = value.data() + value.size();
    const auto result = std::from_chars(begin, end, parsed);
    if (result.ec != std::errc{} || result.ptr != end || !std::isfinite(parsed)) {
        return {.value = std::nullopt, .had_text = true, .ok = false};
    }
    return {.value = parsed, .had_text = true, .ok = true};
}

TreeRecord normalizeTextFields(TreeRecord record) {
    record.project_id = trim(std::move(record.project_id));
    record.campaign_id = trim(std::move(record.campaign_id));
    record.area = trim(std::move(record.area));
    record.plot = trim(std::move(record.plot));
    record.transect = trim(std::move(record.transect));
    record.tree_id = trim(std::move(record.tree_id));
    record.species = normalizeSpaces(std::move(record.species));
    record.condition = lowercaseAscii(trim(std::move(record.condition)));
    record.observer = normalizeSpaces(std::move(record.observer));
    record.date = trim(std::move(record.date));
    record.notes = normalizeSpaces(std::move(record.notes));
    record.source = trim(std::move(record.source));
    record.confidence_flag = trim(std::move(record.confidence_flag));
    record.raw_input = trim(std::move(record.raw_input));

    record.cap_cm_text = trim(std::move(record.cap_cm_text));
    record.dap_cm_text = trim(std::move(record.dap_cm_text));
    record.total_height_m_text = trim(std::move(record.total_height_m_text));
    record.crown_height_m_text = trim(std::move(record.crown_height_m_text));
    record.crown_diameter_ns_m_text = trim(std::move(record.crown_diameter_ns_m_text));
    record.crown_diameter_ew_m_text = trim(std::move(record.crown_diameter_ew_m_text));
    record.latitude_text = trim(std::move(record.latitude_text));
    record.longitude_text = trim(std::move(record.longitude_text));
    return record;
}

ProcessingResult normalizeRecords(const std::vector<TreeRecord>& records) {
    ProcessingResult result;
    result.records.reserve(records.size());

    for (const auto& input : records) {
        TreeRecord output = normalizeTextFields(input);

        parseNumberField(input, result.issues, "cap_cm", output.cap_cm_text, output.cap_cm);
        parseNumberField(input, result.issues, "dap_cm", output.dap_cm_text, output.dap_cm);
        parseNumberField(input, result.issues, "total_height_m", output.total_height_m_text, output.total_height_m);
        parseNumberField(input, result.issues, "crown_height_m", output.crown_height_m_text, output.crown_height_m);
        parseNumberField(input, result.issues, "crown_diameter_ns_m", output.crown_diameter_ns_m_text, output.crown_diameter_ns_m);
        parseNumberField(input, result.issues, "crown_diameter_ew_m", output.crown_diameter_ew_m_text, output.crown_diameter_ew_m);
        parseNumberField(input, result.issues, "latitude", output.latitude_text, output.latitude);
        parseNumberField(input, result.issues, "longitude", output.longitude_text, output.longitude);

        if (output.cap_cm.has_value()) {
            output.cap_source = MeasurementSource::Observed;
        }
        if (output.dap_cm.has_value()) {
            output.dap_source = MeasurementSource::Observed;
        }
        if (output.cap_cm.has_value() && !output.dap_cm.has_value()) {
            output.dap_cm = *output.cap_cm / std::numbers::pi;
            output.dap_source = MeasurementSource::Derived;
        }
        if (output.dap_cm.has_value() && !output.cap_cm.has_value()) {
            output.cap_cm = *output.dap_cm * std::numbers::pi;
            output.cap_source = MeasurementSource::Derived;
        }

        result.records.push_back(std::move(output));
    }

    return result;
}

} // namespace morfocampo::normalizer
