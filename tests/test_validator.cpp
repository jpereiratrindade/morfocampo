#include "morfocampo/Normalizer.hpp"
#include "morfocampo/Validator.hpp"

#include <cassert>

int main() {
    morfocampo::TreeRecord first;
    first.source_line = 2;
    first.project_id = "PRJ";
    first.campaign_id = "C1";
    first.plot = "P1";
    first.tree_id = "A-001";
    first.species = "";
    first.cap_cm_text = "10";
    first.condition = "viva";
    first.observer = "Pedro";
    first.date = "2026-07-01";

    morfocampo::TreeRecord duplicate = first;
    duplicate.source_line = 3;
    duplicate.dap_cm_text = "4";

    morfocampo::TreeRecord invalid;
    invalid.source_line = 4;
    invalid.project_id = "PRJ";
    invalid.campaign_id = "C1";
    invalid.plot = "P1";
    invalid.tree_id = "A-002";
    invalid.observer = "Ana";
    invalid.date = "01/07/2026";
    invalid.condition = "boa";
    invalid.latitude_text = "-91";

    const auto normalized = morfocampo::normalizer::normalizeRecords({first, duplicate, invalid});
    const auto issues = morfocampo::validator::validateRecords(normalized.records);

    bool saw_species_warning = false;
    bool saw_duplicate = false;
    bool saw_date_error = false;
    bool saw_missing_measurement = false;
    bool saw_latitude_error = false;

    for (const auto& issue : issues) {
        saw_species_warning = saw_species_warning ||
            (issue.severity == morfocampo::Severity::Warning && issue.field == "species");
        saw_duplicate = saw_duplicate || issue.field == "duplicate_key";
        saw_date_error = saw_date_error || issue.field == "date";
        saw_missing_measurement = saw_missing_measurement || issue.field == "cap_cm,dap_cm";
        saw_latitude_error = saw_latitude_error || issue.field == "latitude";
    }

    assert(saw_species_warning);
    assert(saw_duplicate);
    assert(saw_date_error);
    assert(saw_missing_measurement);
    assert(saw_latitude_error);
}
