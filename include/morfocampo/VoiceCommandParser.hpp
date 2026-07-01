#pragma once

#include "morfocampo/TreeRecord.hpp"

#include <filesystem>
#include <string>

namespace morfocampo::voice {

struct SessionDefaults {
    std::string project_id;
    std::string campaign_id;
    std::string area;
    std::string plot;
    std::string transect;
    std::string observer;
    std::string date;
};

ProcessingResult parseVoiceFile(const std::filesystem::path& input,
                                const SessionDefaults& defaults = {});
ProcessingResult parseVoiceLine(const std::string& line,
                                std::size_t line_number,
                                const SessionDefaults& defaults = {});

} // namespace morfocampo::voice
