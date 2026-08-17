#ifndef AUDIO_SONAR_ADAPTER_HPP
#define AUDIO_SONAR_ADAPTER_HPP

#include "sensor_adapter.hpp"
#include <vector>
#include <string>
#include <memory>
#include <mutex>
#include <cstdint>

// Adaptador de Bio-Sonar Acústico (Ecolocalización Biomimética)
class AudioSonarAdapter : public ISensorAdapter {
public:
    AudioSonarAdapter(int udp_port = 9099);
    ~AudioSonarAdapter() override;

    bool connect() override;
    void disconnect() override;
    bool is_connected() const override;

    bool read_sensory_frame(SensoryFrame& frame, double dt_sec, double time_ms) override;
    void send_motor_feedback(const std::vector<double>& motor_firing_rates, double time_ms) override;

    std::string get_telemetry_json() const override;
    std::string get_source_name() const override { return "AUDIO_BIO_SONAR"; }
    SensorSourceType get_source_type() const override { return SensorSourceType::ACOUSTIC_RADAR; }

    double get_reward() override;
    bool is_calibrating() const override;

    double get_detected_distance_cm() const { return latest_distance_m_ * 100.0; }
    double get_velocity_mps() const { return latest_velocity_mps_; }
    double get_snr_db() const { return latest_snr_db_; }

private:
    int udp_port_;
    uintptr_t sock_;
    bool connected_;
    
    uint32_t latest_seq_;
    float latest_distance_m_;
    float latest_velocity_mps_;
    float latest_snr_db_;
    std::vector<float> latest_channels_;
    
    double reward_;
    uint64_t frames_received_;
    mutable std::mutex data_mutex_;
    
    bool init_socket();
    void close_socket();
};

#endif // AUDIO_SONAR_ADAPTER_HPP
