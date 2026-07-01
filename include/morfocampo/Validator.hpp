#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <vector>

namespace morfocampo::validator {

std::vector<ValidationIssue> validateRecords(const std::vector<TreeRecord>& records);

} // namespace morfocampo::validator
