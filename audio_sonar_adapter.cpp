#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

#include "audio_sonar_adapter.hpp"
#include <sstream>
#include <iostream>
#include <cstring>
#include <algorithm>
#include <cmath>

#pragma pack(push, 1)
struct SonarPacketHeader {
    uint32_t seq;
    float distance_m;
    float velocity_mps;
    float snr_db;
};
#pragma pack(pop)

AudioSonarAdapter::AudioSonarAdapter(int udp_port)
    : udp_port_(udp_port),
      sock_(INVALID_SOCKET),
      connected_(false),
      latest_seq_(0),
      latest_distance_m_(0.0f),
      latest_velocity_mps_(0.0f),
      latest_snr_db_(0.0f),
      latest_channels_(128, 0.0f),
      reward_(0.0),
      frames_received_(0) {}

AudioSonarAdapter::~AudioSonarAdapter() {
    disconnect();
}

bool AudioSonarAdapter::init_socket() {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock_ == INVALID_SOCKET) {
        std::cerr << "[AudioSonarAdapter] Error al crear socket UDP.\n";
        return false;
    }

    // Configurar socket como no bloqueante
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(sock_, FIONBIO, &mode);
#else
    int flags = fcntl(sock_, F_GETFL, 0);
    fcntl(sock_, F_SETFL, flags | O_NONBLOCK);
#endif

    // Reusar direccion
    int opt = 1;
    setsockopt(sock_, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<u_short>(udp_port_));
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sock_, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        std::cerr << "[AudioSonarAdapter] Error al enlazar socket UDP en puerto " << udp_port_ << ".\n";
        close_socket();
        return false;
    }

    return true;
}

void AudioSonarAdapter::close_socket() {
    if (sock_ != INVALID_SOCKET) {
        closesocket(sock_);
        sock_ = INVALID_SOCKET;
    }
}

bool AudioSonarAdapter::connect() {
    if (init_socket()) {
        connected_ = true;
        std::cout << "[AudioSonarAdapter] Receptor Bio-Sonar UDP escuchando en 127.0.0.1:" << udp_port_ << "\n";
        return true;
    }
    return false;
}

void AudioSonarAdapter::disconnect() {
    connected_ = false;
    close_socket();
}

bool AudioSonarAdapter::is_connected() const {
    return connected_;
}

bool AudioSonarAdapter::read_sensory_frame(SensoryFrame& frame, double dt_sec, double time_ms) {
    (void)dt_sec;
    (void)time_ms;

    if (!connected_ || sock_ == INVALID_SOCKET) return false;

    // Buffer: 16 bytes header + 128 * 4 bytes (512 bytes) = 528 bytes
    uint8_t buffer[1024];
    sockaddr_in sender{};
    int sender_len = sizeof(sender);
    
    bool got_new_packet = false;
    
    // Drenar el socket para procesar el paquete más reciente
    while (true) {
        int bytes = recvfrom(sock_, (char*)buffer, sizeof(buffer), 0, (sockaddr*)&sender, (socklen_t*)&sender_len);
        if (bytes >= (int)(sizeof(SonarPacketHeader) + 128 * sizeof(float))) {
            SonarPacketHeader* hdr = (SonarPacketHeader*)buffer;
            float* channel_data = (float*)(buffer + sizeof(SonarPacketHeader));
            
            std::lock_guard<std::mutex> lock(data_mutex_);
            latest_seq_ = hdr->seq;
            latest_distance_m_ = hdr->distance_m;
            latest_velocity_mps_ = hdr->velocity_mps;
            latest_snr_db_ = hdr->snr_db;
            
            for (int i = 0; i < 128; ++i) {
                latest_channels_[i] = channel_data[i];
            }
            
            frames_received_++;
            got_new_packet = true;
            
            // Recompensa neuromodulatoria (Dopamina) si detecta un eco claro (>0 cm y <2.5 m)
            if (latest_distance_m_ > 0.15f && latest_distance_m_ < 2.00f) {
                reward_ = 0.15; // Reforzar mapeo espacial STDP
            }
        } else {
            break; // No hay más paquetes pendientes
        }
    }

    std::lock_guard<std::mutex> lock(data_mutex_);
    
    frame.channels.resize(128);
    frame.spectrum_amps.resize(64);
    frame.spatial_gradients.resize(63);

    // 1. Inyectar los 128 canales de distancia acústica como corriente sináptica a la SNN
    for (int i = 0; i < 128; ++i) {
        double val = latest_channels_[i];
        // Corriente proporcional a la reflectividad acústica en ese bin de distancia
        frame.channels[i] = 4.0 + 24.0 * val;
    }

    // 2. Llenar los 64 canales de espectro (comprimir 128 a 64 promediando pares)
    for (int i = 0; i < 64; ++i) {
        frame.spectrum_amps[i] = static_cast<float>((latest_channels_[i*2] + latest_channels_[i*2+1]) * 0.5f);
    }

    // 3. Gradientes espaciales de distancia (derivada de la envolvente de eco)
    for (int i = 0; i < 63; ++i) {
        double grad = latest_channels_[i + 1] - latest_channels_[i];
        frame.spatial_gradients[i] = static_cast<float>(grad);
    }

    // 4. Velocidad Doppler y calidad
    frame.motion_velocity = latest_velocity_mps_;
    double snr_ratio = latest_snr_db_ / 30.0;
    frame.signal_quality = (snr_ratio < 0.1) ? 0.1 : ((snr_ratio > 1.0) ? 1.0 : snr_ratio);
    frame.source_name = "AUDIO_BIO_SONAR";
    frame.source_type = SensorSourceType::ACOUSTIC_RADAR;
    
    if (latest_distance_m_ > 0.0f) {
        std::ostringstream oss;
        oss << "OBSTACULO @" << static_cast<int>(latest_distance_m_ * 100.0f) << "cm";
        frame.status_label = oss.str();
    } else {
        frame.status_label = "BUSCANDO_ECO";
    }

    frame.primary_samples_count = static_cast<int>(frames_received_);
    frame.secondary_samples_count = static_cast<int>(frames_received_);

    return true;
}

void AudioSonarAdapter::send_motor_feedback(const std::vector<double>& motor_firing_rates, double time_ms) {
    (void)motor_firing_rates;
    (void)time_ms;
}

std::string AudioSonarAdapter::get_telemetry_json() const {
    std::lock_guard<std::mutex> lock(data_mutex_);
    std::ostringstream oss;
    oss << "{\"audio_sonar\":{"
        << "\"distance_cm\":" << (latest_distance_m_ * 100.0f) << ","
        << "\"velocity_mps\":" << latest_velocity_mps_ << ","
        << "\"snr_db\":" << latest_snr_db_ << ","
        << "\"seq\":" << latest_seq_ << ","
        << "\"frames_received\":" << frames_received_
        << "}}";
    return oss.str();
}

double AudioSonarAdapter::get_reward() {
    double r = reward_;
    reward_ = 0.0;
    return r;
}

bool AudioSonarAdapter::is_calibrating() const {
    return false;
}
