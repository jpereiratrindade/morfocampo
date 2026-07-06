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

    // Descritores silvipastoris / inventário florestal
    std::string stem_height_m_text;        // HF — altura do fuste
    std::string crown_insertion_m_text;    // HIC — altura de inserção da copa
    std::string crown_density_text;        // Densicopa — densidade de copa (ex.: 1-5)
    std::string stem_form;                 // Forma Fuste — categoria livre
    std::string sociological_position;     // Posição sociológica
    std::string trait_1;                   // Característica (coluna 1)
    std::string trait_2;                   // Característica2 (coluna 2)

    std::optional<double> cap_cm;
    std::optional<double> dap_cm;
    std::optional<double> total_height_m;
    std::optional<double> crown_height_m;
    std::optional<double> crown_diameter_ns_m;
    std::optional<double> crown_diameter_ew_m;
    std::optional<double> latitude;
    std::optional<double> longitude;

    // Descritores numéricos adicionais
    std::optional<double> stem_height_m;
    std::optional<double> crown_insertion_m;
    std::optional<int>    crown_density;

    MeasurementSource cap_source{MeasurementSource::Missing};
    MeasurementSource dap_source{MeasurementSource::Missing};
};

struct ProcessingResult {
    std::vector<TreeRecord> records;
    std::vector<ValidationIssue> issues;
    bool is_correction{false};
};

} // namespace morfocampo
