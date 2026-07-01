#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <filesystem>
#include <vector>

namespace morfocampo::report {

void writeValidationReport(const std::filesystem::path& output,
                           const std::vector<TreeRecord>& records,
                           const std::vector<ValidationIssue>& issues);

} // namespace morfocampo::report
