#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <filesystem>
#include <string>

namespace morfocampo::transcript {

ProcessingResult parseTranscriptFile(const std::filesystem::path& input);
ProcessingResult parseTranscriptLine(const std::string& line, std::size_t line_number);

} // namespace morfocampo::transcript
