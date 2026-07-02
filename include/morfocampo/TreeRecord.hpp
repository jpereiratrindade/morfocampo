#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace morfocampo {

enum class MeasurementSource {
    Missing,
    Observed,
    Derived
};

enum class Severity {
    Error,
    Warning
};

struct ValidationIssue {
    Severity severity{Severity::Error};
    std::size_t line{0};
    std::string field;
    std::string message;
};

struct TreeRecord {
    std::size_t source_line{0};

    std::string project_id;
    std::string campaign_id;
    std::string area;
    std::string plot;
    std::string transect;
    std::string tree_id;
    std::string species;
    std::string condition;
    std::string observer;
    std::string date;
    std::string notes;
    std::string source{"csv"};
    std::string confidence_flag{"ok"};
    std::string raw_input;

    std::string cap_cm_text;
    std::string dap_cm_text;
    std::string total_height_m_text;
    std::string crown_height_m_text;
    std::string crown_diameter_ns_m_text;
    std::string crown_diameter_ew_m_text;
    std::string latitude_text;
    std::string longitude_text;

    std::optional<double> cap_cm;
    std::optional<double> dap_cm;
    std::optional<double> total_height_m;
    std::optional<double> crown_height_m;
    std::optional<double> crown_diameter_ns_m;
    std::optional<double> crown_diameter_ew_m;
    std::optional<double> latitude;
    std::optional<double> longitude;

    MeasurementSource cap_source{MeasurementSource::Missing};
    MeasurementSource dap_source{MeasurementSource::Missing};
};

struct ProcessingResult {
    std::vector<TreeRecord> records;
    std::vector<ValidationIssue> issues;
    bool is_correction{false};
};

} // namespace morfocampo
