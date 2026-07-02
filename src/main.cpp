#include "morfocampo/Csv.hpp"
#include "morfocampo/Normalizer.hpp"
#include "morfocampo/Report.hpp"
#include "morfocampo/TranscriptParser.hpp"
#include "morfocampo/Validator.hpp"
#include "morfocampo/VoiceCommandParser.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void printHelp() {
    std::cout
        << "morfocampo - organizacao e validacao de morfometria de arvores\n\n"
        << "Uso:\n"
        << "  morfocampo init --dir examples\n"
        << "  morfocampo init-campaign --dir campo_C01 --project MORFO_CAMPO_2026 --campaign C01 "
              "--area \"Butiazal Sao Miguel\" --plots P01,P02 --rows 50\n"
        << "  morfocampo parse-voice --input examples/fala_estruturada.txt --out out/dados_por_voz.csv\n"
        << "  morfocampo session --project MORFO_2026 --campaign C01 --plot P01 --observer Pedro "
              "--date 2026-07-01 [--max-cap 600] [--max-dap 200] [--max-height 30] [--max-crown 20]\n"
        << "  morfocampo validate --input dados.csv --out out "
              "[--max-cap 600] [--max-dap 200] [--max-height 30] [--max-crown 20]\n"
        << "  morfocampo parse-transcript --input transcricoes.txt --out saida.csv\n"
        << "  morfocampo help\n\n"
        << "Na sessao interativa, prefixe a frase com 'corrigir' para substituir\n"
        << "o registro existente com o mesmo tree_id na sessao atual.\n";
}

std::string optionValue(const std::vector<std::string>& args, const std::string& name) {
    for (std::size_t i = 0; i + 1 < args.size(); ++i) {
        if (args[i] == name) {
            return args[i + 1];
        }
    }
    return {};
}

void writeTextFile(const std::filesystem::path& path, const std::string& text) {
    if (path.has_parent_path()) {
        std::filesystem::create_directories(path.parent_path());
    }
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("nao foi possivel escrever arquivo: " + path.string());
    }
    out << text;
}

std::vector<std::string> splitList(const std::string& text) {
    std::vector<std::string> values;
    std::stringstream stream(text);
    std::string value;
    while (std::getline(stream, value, ',')) {
        if (!value.empty()) {
            values.push_back(value);
        }
    }
    return values;
}

int parsePositiveInt(const std::string& text, int fallback) {
    if (text.empty()) {
        return fallback;
    }
    const int value = std::stoi(text);
    if (value <= 0) {
        throw std::runtime_error("--rows deve ser maior que zero");
    }
    return value;
}

double parseOptionalDouble(const std::vector<std::string>& args,
                           const std::string& name,
                           double fallback = std::numeric_limits<double>::infinity()) {
    const auto text = optionValue(args, name);
    if (text.empty()) {
        return fallback;
    }
    const double v = std::stod(text);
    if (v <= 0.0) {
        throw std::runtime_error(name + " deve ser maior que zero");
    }
    return v;
}

int runInit(const std::vector<std::string>& args) {
    const std::filesystem::path dir = optionValue(args, "--dir").empty()
        ? std::filesystem::path("examples")
        : std::filesystem::path(optionValue(args, "--dir"));
    std::filesystem::create_directories(dir);

    morfocampo::csv::writeTemplateCsv(dir / "template_arvores.csv");
    morfocampo::csv::writeVoiceExampleFile(dir / "fala_estruturada.txt");
    writeTextFile(dir / "transcricoes_exemplo.txt",
        "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; transecto T01; arvore A-023; especie Butia odorata; CAP 42,5 cm; altura total 4,8 m; altura da copa 2,1 m; copa norte-sul 3,4 m; copa leste-oeste 2,9 m; condicao viva; observador Pedro; data 2026-07-01; latitude -30,0341; longitude -51,2177\n"
        "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P01; transecto T01; arvore A-024; especie Butia odorata; DAP 13.2 cm; altura total 4.2 m; altura da copa 1.7 m; copa norte-sul 3.1 m; copa leste-oeste 2.6 m; condicao rebrote; observador Ana; data 2026-07-01\n"
        "projeto PRJ-BUTIA; campanha 2026-01; area Restinga norte; parcela P02; transecto T02; arvore A-025; CAP 38,1 cm; altura total 3,9 m; condicao desconhecida; observador Carla; data 2026-07-02; comentario livre ignorado\n");
    writeTextFile(dir / "README_EXEMPLOS.md",
        "# Exemplos morfocampo\n\n"
        "- `template_arvores.csv`: CSV minimo para preenchimento e validacao.\n"
        "- `fala_estruturada.txt`: frases curtas simulando fala transcrita.\n"
        "- `transcricoes_exemplo.txt`: transcricoes controladas, uma arvore por linha.\n\n"
        "Comandos:\n\n"
        "```sh\n"
        "morfocampo validate --input examples/template_arvores.csv --out out\n"
        "morfocampo parse-voice --input examples/fala_estruturada.txt --out out/dados_por_voz.csv\n"
        "morfocampo parse-transcript --input examples/transcricoes_exemplo.txt --out out/transcricao_convertida.csv\n"
        "```\n");

    std::cout << "Arquivos de exemplo gerados em " << dir << '\n';
    return 0;
}

int runInitCampaign(const std::vector<std::string>& args) {
    const auto dir_arg = optionValue(args, "--dir");
    const auto project = optionValue(args, "--project");
    const auto campaign = optionValue(args, "--campaign");
    const auto area = optionValue(args, "--area");
    const auto plots_arg = optionValue(args, "--plots");
    const auto observers_arg = optionValue(args, "--observers");
    const auto rows_arg = optionValue(args, "--rows");

    if (dir_arg.empty() || project.empty() || campaign.empty() || area.empty() || plots_arg.empty()) {
        throw std::runtime_error("init-campaign requer --dir, --project, --campaign, --area e --plots");
    }

    const std::filesystem::path dir(dir_arg);
    const auto plots = splitList(plots_arg);
    const auto observers = observers_arg.empty() ? std::vector<std::string>{} : splitList(observers_arg);
    const int rows_per_plot = parsePositiveInt(rows_arg, 50);
    if (plots.empty()) {
        throw std::runtime_error("--plots deve conter pelo menos uma parcela");
    }

    std::filesystem::create_directories(dir / "listas");

    std::vector<morfocampo::TreeRecord> records;
    records.reserve(plots.size() * static_cast<std::size_t>(rows_per_plot));
    for (const auto& plot : plots) {
        for (int i = 1; i <= rows_per_plot; ++i) {
            morfocampo::TreeRecord record;
            record.project_id = project;
            record.campaign_id = campaign;
            record.area = area;
            record.plot = plot;
            std::ostringstream tree_id;
            tree_id << 'A' << '-' << std::setfill('0') << std::setw(3) << i;
            record.tree_id = tree_id.str();
            records.push_back(std::move(record));
        }
    }

    morfocampo::csv::writeTreesCsv(dir / "coleta_arvores.csv", records);

    writeTextFile(dir / "listas" / "condicoes.csv",
        "condition\n"
        "viva\n"
        "morta\n"
        "rebrote\n"
        "dano\n"
        "desconhecida\n");

    std::string plots_csv = "plot\n";
    for (const auto& plot : plots) {
        plots_csv += plot + "\n";
    }
    writeTextFile(dir / "listas" / "parcelas.csv", plots_csv);

    std::string observers_csv = "observer\n";
    for (const auto& observer : observers) {
        observers_csv += observer + "\n";
    }
    writeTextFile(dir / "listas" / "observadores.csv", observers_csv);

    writeTextFile(dir / "protocolo_campo.md",
        "# Protocolo de campo\n\n"
        "- Projeto: `" + project + "`\n"
        "- Campanha: `" + campaign + "`\n"
        "- Area: `" + area + "`\n"
        "- Planilha principal: `coleta_arvores.csv`\n"
        "- Listas de apoio: `listas/`\n\n"
        "## Rotina sugerida\n\n"
        "1. Abra `coleta_arvores.csv` em uma planilha digital no celular, tablet ou notebook.\n"
        "2. Preencha uma linha por arvore medida.\n"
        "3. Use as listas em `listas/` para padronizar parcelas, observadores e condicoes.\n"
        "4. Ao fim do periodo de coleta, rode:\n\n"
        "```sh\n"
        "morfocampo validate --input " + (dir / "coleta_arvores.csv").string() + " --out " + (dir / "validacao").string() + "\n"
        "```\n\n"
        "## Campos obrigatorios\n\n"
        "- `project_id`\n"
        "- `campaign_id`\n"
        "- `plot`\n"
        "- `tree_id`\n"
        "- `observer`\n"
        "- `date`\n"
        "- pelo menos um entre `cap_cm` e `dap_cm`\n");

    writeTextFile(dir / "README_PLANILHA.md",
        "# Planilha digital da campanha\n\n"
        "`coleta_arvores.csv` e uma planilha simples compativel com LibreOffice, Excel, Google Sheets, OnlyOffice e editores CSV em celular/tablet.\n\n"
        "Ela nao tem macros nem validacao embutida. A validacao oficial continua sendo feita pelo `morfocampo validate`, para manter o fluxo reproduzivel e auditavel.\n\n"
        "Importe as listas de `listas/` como apoio para menus suspensos quando o aplicativo de planilha permitir.\n");

    std::cout << "Pacote de campanha gerado em " << dir << '\n';
    std::cout << "Planilha digital: " << (dir / "coleta_arvores.csv") << '\n';
    return 0;
}

int runValidate(const std::vector<std::string>& args) {
    const auto input = optionValue(args, "--input");
    const auto out_dir = optionValue(args, "--out");
    if (input.empty() || out_dir.empty()) {
        throw std::runtime_error("validate requer --input e --out");
    }

    morfocampo::validator::RangeConfig range;
    range.max_cap_cm    = parseOptionalDouble(args, "--max-cap");
    range.max_dap_cm    = parseOptionalDouble(args, "--max-dap");
    range.max_height_m  = parseOptionalDouble(args, "--max-height");
    range.max_crown_m   = parseOptionalDouble(args, "--max-crown");

    auto read = morfocampo::csv::readTrees(input);
    auto normalized = morfocampo::normalizer::normalizeRecords(read.records);
    auto validation = morfocampo::validator::validateRecords(normalized.records, range);

    std::vector<morfocampo::ValidationIssue> issues;
    issues.insert(issues.end(), read.issues.begin(), read.issues.end());
    issues.insert(issues.end(), normalized.issues.begin(), normalized.issues.end());
    issues.insert(issues.end(), validation.begin(), validation.end());

    const std::filesystem::path out_path(out_dir);
    std::filesystem::create_directories(out_path);
    morfocampo::csv::writeTreesCsv(out_path / "arvores_normalizadas.csv", normalized.records);
    morfocampo::csv::writeTreesJsonl(out_path / "arvores_normalizadas.jsonl", normalized.records);
    morfocampo::report::writeValidationReport(out_path / "relatorio_validacao.md", normalized.records, issues);

    std::cout << "Validacao concluida em " << out_path << '\n';
    return 0;
}

int runParseTranscript(const std::vector<std::string>& args) {
    const auto input = optionValue(args, "--input");
    const auto output = optionValue(args, "--out");
    if (input.empty() || output.empty()) {
        throw std::runtime_error("parse-transcript requer --input e --out");
    }

    auto parsed = morfocampo::transcript::parseTranscriptFile(input);
    auto normalized = morfocampo::normalizer::normalizeRecords(parsed.records);

    std::vector<morfocampo::ValidationIssue> issues;
    issues.insert(issues.end(), parsed.issues.begin(), parsed.issues.end());
    issues.insert(issues.end(), normalized.issues.begin(), normalized.issues.end());

    morfocampo::csv::writeTreesCsv(output, normalized.records);
    for (const auto& issue : issues) {
        std::cerr << "Aviso linha " << issue.line << " [" << issue.field << "]: " << issue.message << '\n';
    }
    std::cout << "Transcricao convertida em " << output << '\n';
    return 0;
}

int runParseVoice(const std::vector<std::string>& args) {
    const auto input = optionValue(args, "--input");
    const auto output = optionValue(args, "--out");
    if (input.empty() || output.empty()) {
        throw std::runtime_error("parse-voice requer --input e --out");
    }

    auto parsed = morfocampo::voice::parseVoiceFile(input);
    auto normalized = morfocampo::normalizer::normalizeRecords(parsed.records);
    morfocampo::csv::writeTreesCsv(output, normalized.records);
    for (const auto& issue : parsed.issues) {
        std::cerr << "Aviso linha " << issue.line << " [" << issue.field << "]: " << issue.message << '\n';
    }
    std::cout << "Fala estruturada convertida em " << output << '\n';
    return 0;
}

void printInterpreted(const morfocampo::TreeRecord& record) {
    std::cout << "Registro interpretado:\n";
    std::cout << "tree_id: " << record.tree_id << '\n';
    if (record.cap_cm.has_value()) {
        std::cout << "cap_cm: " << *record.cap_cm << '\n';
    }
    if (record.dap_cm.has_value()) {
        std::cout << "dap_cm: " << *record.dap_cm;
        if (record.dap_source == morfocampo::MeasurementSource::Derived) {
            std::cout << " calculado";
        }
        std::cout << '\n';
    }
    if (record.total_height_m.has_value()) {
        std::cout << "total_height_m: " << *record.total_height_m << '\n';
    }
    std::cout << "condition: " << record.condition << '\n';
    std::cout << "confidence_flag: " << record.confidence_flag << '\n';
}

int runSession(const std::vector<std::string>& args) {
    morfocampo::voice::SessionDefaults defaults;
    defaults.project_id = optionValue(args, "--project");
    defaults.campaign_id = optionValue(args, "--campaign");
    defaults.area = optionValue(args, "--area");
    defaults.plot = optionValue(args, "--plot");
    defaults.transect = optionValue(args, "--transect");
    defaults.observer = optionValue(args, "--observer");
    defaults.date = optionValue(args, "--date");
    const auto output = optionValue(args, "--out").empty()
        ? std::string("session_voice.csv")
        : optionValue(args, "--out");
    if (defaults.project_id.empty() || defaults.campaign_id.empty() ||
        defaults.plot.empty() || defaults.observer.empty() || defaults.date.empty()) {
        throw std::runtime_error("session requer --project, --campaign, --plot, --observer e --date");
    }

    morfocampo::validator::RangeConfig range;
    range.max_cap_cm   = parseOptionalDouble(args, "--max-cap");
    range.max_dap_cm   = parseOptionalDouble(args, "--max-dap");
    range.max_height_m = parseOptionalDouble(args, "--max-height");
    range.max_crown_m  = parseOptionalDouble(args, "--max-crown");

    std::vector<morfocampo::TreeRecord> records;
    std::string line;
    std::cout << "Sessao morfocampo. Digite frases estruturadas; use 'sair' para encerrar.\n";
    std::cout << "Prefixe com 'corrigir' para substituir o ultimo registro com o mesmo tree_id.\n";
    while (std::cout << "> " && std::getline(std::cin, line)) {
        if (line == "sair" || line == "exit" || line == "quit") {
            break;
        }
        auto parsed = morfocampo::voice::parseVoiceLine(line, records.size() + 1, defaults);
        auto normalized = morfocampo::normalizer::normalizeRecords(parsed.records);
        const auto& record = normalized.records.front();
        printInterpreted(record);

        // Validação imediata com faixas configuradas
        auto issues = morfocampo::validator::validateRecords(normalized.records, range);
        for (const auto& issue : issues) {
            if (issue.severity == morfocampo::Severity::Warning) {
                std::cout << "  Aviso [" << issue.field << "]: " << issue.message << '\n';
            } else {
                std::cout << "  ERRO  [" << issue.field << "]: " << issue.message << '\n';
            }
        }

        std::cout << "Confirmar? [s/n] ";
        std::string answer;
        std::getline(std::cin, answer);
        if (!answer.empty() && (answer[0] == 's' || answer[0] == 'S')) {
            if (parsed.is_correction && !record.tree_id.empty()) {
                // Substituir registro anterior com mesmo tree_id
                auto it = std::find_if(records.begin(), records.end(),
                    [&record](const morfocampo::TreeRecord& r) {
                        return r.tree_id == record.tree_id;
                    });
                if (it != records.end()) {
                    *it = record;
                    std::cout << "Registro de " << record.tree_id << " corrigido.\n";
                } else {
                    records.push_back(record);
                    std::cout << "Arvore " << record.tree_id
                              << " nao encontrada na sessao; adicionada como novo registro.\n";
                }
            } else {
                records.push_back(record);
                std::cout << "Registro mantido.\n";
            }
        } else {
            std::cout << "Registro descartado.\n";
        }
    }
    morfocampo::csv::writeTreesCsv(output, records);
    std::cout << "Sessao salva em " << output << '\n';
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::vector<std::string> args(argv + 1, argv + argc);
        if (args.empty() || args[0] == "help" || args[0] == "--help" || args[0] == "-h") {
            printHelp();
            return 0;
        }
        if (args[0] == "init") {
            return runInit(args);
        }
        if (args[0] == "init-campaign") {
            return runInitCampaign(args);
        }
        if (args[0] == "validate") {
            return runValidate(args);
        }
        if (args[0] == "parse-voice") {
            return runParseVoice(args);
        }
        if (args[0] == "session") {
            return runSession(args);
        }
        if (args[0] == "parse-transcript") {
            return runParseTranscript(args);
        }

        printHelp();
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "Erro: " << error.what() << '\n';
        return 2;
    }
}
