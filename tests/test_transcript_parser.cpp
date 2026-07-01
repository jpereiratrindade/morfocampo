#include "morfocampo/Normalizer.hpp"
#include "morfocampo/TranscriptParser.hpp"

#include <cassert>
#include <cmath>

int main() {
    const auto parsed = morfocampo::transcript::parseTranscriptLine(
        "projeto PRJ-BUTIA; campanha 2026-01; parcela P01; árvore A-023; espécie Butia odorata; CAP 42,5 cm; altura total 4,8 m; altura da copa 2,1 m; copa norte-sul 3,4 m; copa leste-oeste 2,9 m; condição viva; observador Pedro; data 2026-07-01; campo desconhecido valor",
        7
    );

    assert(parsed.records.size() == 1);
    assert(parsed.issues.empty());
    assert(parsed.records.front().tree_id == "A-023");
    assert(parsed.records.front().species == "Butia odorata");
    assert(parsed.records.front().cap_cm_text == "42,5");
    assert(parsed.records.front().condition == "viva");

    const auto normalized = morfocampo::normalizer::normalizeRecords(parsed.records);
    assert(normalized.issues.empty());
    assert(normalized.records.front().cap_cm.has_value());
    assert(std::abs(*normalized.records.front().cap_cm - 42.5) < 0.000001);
    assert(normalized.records.front().dap_cm.has_value());
}
