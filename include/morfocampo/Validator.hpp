#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <limits>
#include <vector>

namespace morfocampo::validator {

struct RangeConfig {
    double max_cap_cm{std::numeric_limits<double>::infinity()};
    double max_dap_cm{std::numeric_limits<double>::infinity()};
    double max_height_m{std::numeric_limits<double>::infinity()};
    double max_crown_m{std::numeric_limits<double>::infinity()};
};

std::vector<ValidationIssue> validateRecords(const std::vector<TreeRecord>& records,
                                              const RangeConfig& range = {});

} // namespace morfocampo::validator
