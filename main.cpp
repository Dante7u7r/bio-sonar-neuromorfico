#include "cerebro.hpp"
#include "server.hpp"
#include "sensor_adapter.hpp"
#include "synthetic_signal_adapter.hpp"
#include "audio_sonar_adapter.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include <atomic>
#include <fstream>
#include <cstdlib>
#include <iomanip>

std::atomic<bool> sim_running(true);
std::atomic<bool> exit_requested(false);

void signal_handler(int signum) {
    if (signum == SIGINT) {
        if (sim_running) {
            std::cout << "\n[WARN] Interrupcion detectada. Deteniendo bucle del Bio-Sonar...\n";
            sim_running = false;
        } else {
            std::cout << "\n[WARN] Interrupcion detectada de nuevo. Apagando servidor HTTP...\n";
            exit_requested = true;
        }
    }
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, signal_handler);

    int http_port = 8000;
    int max_steps = -1;
    bool disable_server = false;
    bool use_audio_sonar = true;
    int sonar_port = 9099;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--port" && i + 1 < argc) {
            http_port = std::atoi(argv[++i]);
        } else if (arg == "--steps" && i + 1 < argc) {
            max_steps = std::atoi(argv[++i]);
        } else if (arg == "--no-server") {
            disable_server = true;
        } else if (arg == "--sonar" || arg == "--audio") {
            use_audio_sonar = true;
            if (i + 1 < argc && argv[i+1][0] != '-') {
                sonar_port = std::atoi(argv[++i]);
            }
        } else if (arg == "--sim") {
            use_audio_sonar = false;
        }
    }

    std::cout << "========================================================================\n";
    std::cout << "  🦇 SISTEMA DE BIO-SONAR NEUROMORFICO ACUSTICO EN TIEMPO REAL (C++17)\n";
    std::cout << "  Ecolocalizacion y Mapeo Espacial 3D Bio-Inspirado (SNN + Physarum)\n";
    std::cout << "  Adaptador: " << (use_audio_sonar ? ("AUDIO BIO-SONAR UDP:" + std::to_string(sonar_port)) : "GENERADOR SINTETICO BENCHMARK") << "\n";
    std::cout << "  Topologia: Sensorial: " << N_SENSORY << ", Oculta: " << N_HIDDEN 
              << ", Motor: " << N_MOTOR << ", PFC: " << N_PFC << " (Total: " << N_TOTAL << " LIF Neurons)\n";
    std::cout << "========================================================================\n";

    // Crear carpeta logs si no existe
#ifdef _WIN32
    std::system("mkdir logs 2>nul");
#else
    std::system("mkdir -p logs");
#endif

    std::string state_path = "./logs/bio_sonar_state.bin";

    // 1. Instanciar el adaptador sensorial (Bio-Sonar o Sintético)
    std::unique_ptr<ISensorAdapter> sensor_adapter;
    if (use_audio_sonar) {
        auto sonar = std::make_unique<AudioSonarAdapter>(sonar_port);
        if (sonar->connect()) {
            std::cout << "[OK] Adaptador Bio-Sonar Acustico escuchando en puerto " << sonar_port << ".\n";
            sensor_adapter = std::move(sonar);
        } else {
            std::cerr << "[WARN] Fallo enlace Bio-Sonar. Cambiando a generador sintetico...\n";
            auto syn = std::make_unique<SyntheticSignalAdapter>(10, 30.0);
            syn->connect();
            sensor_adapter = std::move(syn);
        }
    } else {
        auto syn = std::make_unique<SyntheticSignalAdapter>(10, 30.0);
        syn->connect();
        sensor_adapter = std::move(syn);
    }

    // 2. Inicializar el nucleo cerebral
    auto cerebro = std::make_unique<BrainUnico>(std::move(sensor_adapter));

    // Cargar estado previo si existe
    std::ifstream check_file(state_path, std::ios::binary);
    if (check_file.good()) {
        check_file.close();
        if (cerebro->load_state(state_path)) {
            std::cout << "[OK] Estado previo cargado desde " << state_path << "\n";
        }
    }

    // 3. Iniciar servidor HTTP para visualizador Web
    if (!disable_server) {
        start_server(http_port);
        std::cout << "[OK] Visualizador Web activo en: http://localhost:" << http_port << "/demo.html\n";
    }

    std::cout << "\n[*] Bucle principal del Bio-Sonar en marcha. Presiona Ctrl+C para salir.\n\n";

    int step_counter = 0;
    while (sim_running) {
        cerebro->step();
        step_counter++;

        if (step_counter % 20 == 0) {
            double t_sec = cerebro->time_ms / 1000.0;
            std::string src = cerebro->sensor_adapter ? cerebro->sensor_adapter->get_source_name() : "NONE";
            std::string label = cerebro->sensor_adapter ? cerebro->current_sensory_frame.status_label : "N/A";
            
            std::cout << "[Paso " << step_counter << "] t=" << std::fixed << std::setprecision(1) << t_sec << "s"
                      << " | " << cerebro->brain_state
                      << " | Fuente: " << src
                      << " | " << label
                      << " | Spikes: " << cerebro->spikes_in_current_batch
                      << " | DA: " << std::setprecision(2) << cerebro->neuromod.dopamine
                      << " | Aforo: " << cerebro->fungal_quorum.get_estimated_occupants()
                      << "\n";
        }

        if (max_steps > 0 && step_counter >= max_steps) {
            break;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    std::cout << "\n[*] Guardando estado del Bio-Sonar...\n";
    cerebro->save_state(state_path);
    std::cout << "[OK] Estado guardado en " << state_path << "\n";

    if (!disable_server) {
        std::cout << "[*] Esperando a que el servidor HTTP concluya...\n";
        stop_server();
    }

    std::cout << "[+] Bio-Sonar finalizado ordenadamente.\n";
    return 0;
}
