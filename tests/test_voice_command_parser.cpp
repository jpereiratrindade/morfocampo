#include "morfocampo/Normalizer.hpp"
#include "morfocampo/VoiceCommandParser.hpp"

#include <cassert>
#include <cmath>

int main() {
    morfocampo::voice::SessionDefaults defaults;
    defaults.project_id = "MORFO_2026";
    defaults.campaign_id = "C01";
    defaults.plot = "P01";
    defaults.observer = "Pedro";
    defaults.date = "2026-07-01";

    const std::string raw = "projeto MORFO_2026 campanha C01 parcela P01 observador Pedro data 2026-07-01 arvore A-023 CAP 42,5 altura total 4,8 condicao viva";
    const auto parsed = morfocampo::voice::parseVoiceLine(raw, 1, defaults);
    assert(parsed.records.size() == 1);
    assert(parsed.records.front().raw_input == raw);
    assert(parsed.records.front().source == "voice_text");
    assert(parsed.records.front().project_id == "MORFO_2026");
    assert(parsed.records.front().campaign_id == "C01");
    assert(parsed.records.front().plot == "P01");
    assert(parsed.records.front().observer == "Pedro");
    assert(parsed.records.front().date == "2026-07-01");
    assert(parsed.records.front().tree_id == "A-023");
    assert(parsed.records.front().cap_cm_text == "42,5");
    assert(parsed.records.front().total_height_m_text == "4,8");
    assert(parsed.records.front().condition == "viva");

    const auto normalized = morfocampo::normalizer::normalizeRecords(parsed.records);
    assert(normalized.records.front().dap_cm.has_value());
    assert(std::abs(*normalized.records.front().dap_cm - 13.52817) < 0.0001);

    const auto dap = morfocampo::voice::parseVoiceLine("nova arvore A-025 diametro 13,4 dano", 2, defaults);
    assert(dap.records.front().dap_cm_text == "13,4");
    assert(dap.records.front().condition == "dano");

    const auto incomplete = morfocampo::voice::parseVoiceLine("altura total 5,1 condicao viva", 3, defaults);
    assert(incomplete.records.front().confidence_flag == "erro");
    assert(!incomplete.issues.empty());
}
