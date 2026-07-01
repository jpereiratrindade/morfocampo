#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <filesystem>
#include <string>
#include <vector>

namespace morfocampo::csv {

std::vector<std::string> defaultTreeHeaders();

ProcessingResult readTrees(const std::filesystem::path& input);

void writeTreesCsv(const std::filesystem::path& output,
                   const std::vector<TreeRecord>& records);

void writeTreesJsonl(const std::filesystem::path& output,
                     const std::vector<TreeRecord>& records);

void writeTemplateCsv(const std::filesystem::path& output);

void writeVoiceExampleFile(const std::filesystem::path& output);

std::vector<std::string> parseCsvLine(const std::string& line);

} // namespace morfocampo::csv
