cmake_minimum_required(VERSION 3.20)

project(morfocampo VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(morfocampo_core
    src/Csv.cpp
    src/Normalizer.cpp
    src/Validator.cpp
    src/TranscriptParser.cpp
    src/VoiceCommandParser.cpp
    src/Report.cpp
)

target_include_directories(morfocampo_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(morfocampo_core PRIVATE
    -Wall -Wextra -Wpedantic
)

add_executable(morfocampo src/main.cpp)
target_link_libraries(morfocampo PRIVATE morfocampo_core)
target_compile_options(morfocampo PRIVATE -Wall -Wextra -Wpedantic)

enable_testing()

add_executable(test_normalizer tests/test_normalizer.cpp)
target_link_libraries(test_normalizer PRIVATE morfocampo_core)
add_test(NAME test_normalizer COMMAND test_normalizer)

add_executable(test_validator tests/test_validator.cpp)
target_link_libraries(test_validator PRIVATE morfocampo_core)
add_test(NAME test_validator COMMAND test_validator)

add_executable(test_transcript_parser tests/test_transcript_parser.cpp)
target_link_libraries(test_transcript_parser PRIVATE morfocampo_core)
add_test(NAME test_transcript_parser COMMAND test_transcript_parser)

add_executable(test_voice_command_parser tests/test_voice_command_parser.cpp)
target_link_libraries(test_voice_command_parser PRIVATE morfocampo_core)
add_test(NAME test_voice_command_parser COMMAND test_voice_command_parser)

add_test(
    NAME test_cli_init_campaign
    COMMAND morfocampo init-campaign
        --dir ${CMAKE_CURRENT_BINARY_DIR}/test_campaign
        --project MORFO_CAMPO_2026
        --campaign C01
        --area "Butiazal Sao Miguel"
        --plots P01,P02
        --observers Pedro,Ana
        --rows 2
)

add_test(
    NAME test_cli_validate_campaign_sheet
    COMMAND morfocampo validate
        --input ${CMAKE_CURRENT_BINARY_DIR}/test_campaign/coleta_arvores.csv
        --out ${CMAKE_CURRENT_BINARY_DIR}/test_campaign/validacao
)
set_tests_properties(test_cli_validate_campaign_sheet PROPERTIES DEPENDS test_cli_init_campaign)
