#include "morfocampo/Normalizer.hpp"

#include <cassert>
#include <cmath>
#include <numbers>

int main() {
    morfocampo::TreeRecord record;
    record.source_line = 2;
    record.project_id = " PRJ ";
    record.species = "Butia   odorata";
    record.condition = " VIVA ";
    record.cap_cm_text = "42,5";
    record.total_height_m_text = " 4.8 ";

    const auto result = morfocampo::normalizer::normalizeRecords({record});
    assert(result.issues.empty());
    assert(result.records.size() == 1);

    const auto& normalized = result.records.front();
    assert(normalized.project_id == "PRJ");
    assert(normalized.species == "Butia odorata");
    assert(normalized.condition == "viva");
    assert(normalized.cap_cm.has_value());
    assert(std::abs(*normalized.cap_cm - 42.5) < 0.000001);
    assert(normalized.dap_cm.has_value());
    assert(std::abs(*normalized.dap_cm - (42.5 / std::numbers::pi)) < 0.000001);
    assert(normalized.cap_source == morfocampo::MeasurementSource::Observed);
    assert(normalized.dap_source == morfocampo::MeasurementSource::Derived);

    record.cap_cm_text = "42,5.1";
    const auto invalid = morfocampo::normalizer::normalizeRecords({record});
    assert(!invalid.issues.empty());
    assert(invalid.issues.front().field == "cap_cm");
}
