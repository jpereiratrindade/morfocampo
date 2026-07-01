#include "morfocampo/TranscriptParser.hpp"

#include "morfocampo/VoiceCommandParser.hpp"

namespace morfocampo::transcript {

ProcessingResult parseTranscriptLine(const std::string& line, std::size_t line_number) {
    return voice::parseVoiceLine(line, line_number);
}

ProcessingResult parseTranscriptFile(const std::filesystem::path& input) {
    return voice::parseVoiceFile(input);
}

} // namespace morfocampo::transcript
