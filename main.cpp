#include "cerebro.hpp"
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
#include <algorithm>

std::atomic<bool> sim_running(true);

void signal_handler(int signum) {
    if (signum == SIGINT) {
        std::cout << "\n[WARN] Interrupcion detectada. Deteniendo Bio-Sonar...\n";
        sim_running = false;
    }
}

int main(int argc, char* argv[]) {
    std::signal(SIGINT, signal_handler);

    int max_steps = -1;
    bool use_audio_sonar = true;
    int sonar_port = 9099;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--steps" && i + 1 < argc) {
            max_steps = std::atoi(argv[++i]);
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
    std::cout << "  🦇 MOTOR NEUROMORFICO BIO-SONAR ACUSTICO EN TIEMPO REAL (C++17)\n";
    std::cout << "  Ecolocalizacion y Mapeo Espacial Bio-Inspirado (SNN + Physarum)\n";
    std::cout << "  Modo: " << (use_audio_sonar ? ("AUDIO BIO-SONAR UDP:" + std::to_string(sonar_port)) : "GENERADOR SINTETICO BENCHMARK") << "\n";
    std::cout << "  Red SNN: " << N_SENSORY << " Sensoriales (0-2.5m) | " << N_HIDDEN << " Ocultas | " 
              << N_MOTOR << " Motoras | " << N_PFC << " PFC (Total: " << N_TOTAL << " LIF Neurons)\n";
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
    AudioSonarAdapter* sonar_raw_ptr = nullptr;

    if (use_audio_sonar) {
        auto sonar = std::make_unique<AudioSonarAdapter>(sonar_port);
        sonar_raw_ptr = sonar.get();
        if (sonar->connect()) {
            std::cout << "[OK] Adaptador Bio-Sonar Acustico escuchando en 127.0.0.1:" << sonar_port << "\n";
            sensor_adapter = std::move(sonar);
        } else {
            std::cerr << "[WARN] Fallo enlace Bio-Sonar. Cambiando a generador sintetico...\n";
            sonar_raw_ptr = nullptr;
            auto syn = std::make_unique<SyntheticSignalAdapter>(10, 30.0);
            syn->connect();
            sensor_adapter = std::move(syn);
        }
    } else {
        auto syn = std::make_unique<SyntheticSignalAdapter>(10, 30.0);
        syn->connect();
        sensor_adapter = std::move(syn);
    }

    // 2. Inicializar el nucleo cerebral con el adaptador de sensores
    auto cerebro = std::make_unique<BrainUnico>(std::move(sensor_adapter));

    // Cargar estado previo si existe
    std::ifstream check_file(state_path, std::ios::binary);
    if (check_file.good()) {
        check_file.close();
        if (cerebro->load_state(state_path)) {
            std::cout << "[OK] Estado previo cargado desde " << state_path << "\n";
        }
    }

    std::cout << "\n[*] Bucle del Bio-Sonar activo. Presiona Ctrl+C para salir.\n";
    std::cout << "----------------------------------------------------------------------------------------------------\n";
    std::cout << " Tiempo  | Estado SNN | Distancia Eco | Radar Acustico (0cm -> 200cm)           | Spikes | Dopamina\n";
    std::cout << "----------------------------------------------------------------------------------------------------\n";

    int step_counter = 0;
    while (sim_running) {
        cerebro->step();
        step_counter++;

        if (step_counter % 10 == 0) {
            double t_sec = cerebro->time_ms / 1000.0;
            double dist_cm = 0.0;
            if (sonar_raw_ptr) {
                dist_cm = sonar_raw_ptr->get_detected_distance_cm();
            }

            // Barra visual de radar en consola (0 cm a 200 cm)
            int bar_len = 30;
            int bar_pos = (dist_cm > 0.0) ? std::min(bar_len - 1, static_cast<int>((dist_cm / 200.0) * bar_len)) : -1;
            
            std::string radar_bar = "[";
            for (int b = 0; b < bar_len; ++b) {
                if (b == bar_pos) radar_bar += "*";
                else radar_bar += "-";
            }
            radar_bar += "]";

            std::string dist_str = (dist_cm > 0.0) ? (std::to_string(static_cast<int>(dist_cm)) + " cm") : "Buscando...";

            std::cout << " " << std::setw(6) << std::fixed << std::setprecision(1) << t_sec << "s"
                      << " | " << std::setw(10) << cerebro->brain_state
                      << " | " << std::setw(13) << dist_str
                      << " | " << std::setw(40) << std::left << radar_bar << std::right
                      << " | " << std::setw(6) << cerebro->spikes_in_current_batch
                      << " | " << std::setw(8) << std::setprecision(2) << cerebro->neuromod.dopamine
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
    std::cout << "[+] Bio-Sonar finalizado ordenadamente.\n";
    return 0;
}
