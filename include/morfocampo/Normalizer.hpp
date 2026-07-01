#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <optional>
#include <string>

namespace morfocampo::normalizer {

struct NumberParseResult {
    std::optional<double> value;
    bool had_text{false};
    bool ok{true};
};

std::string trim(std::string value);
std::string normalizeSpaces(std::string value);
std::string lowercaseAscii(std::string value);
NumberParseResult parseOptionalDecimal(const std::string& text);
ProcessingResult normalizeRecords(const std::vector<TreeRecord>& records);
TreeRecord normalizeTextFields(TreeRecord record);

} // namespace morfocampo::normalizer
