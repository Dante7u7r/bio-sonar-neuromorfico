import numpy as np
import scipy.signal
import sounddevice as sd
import socket
import struct
import time
import sys

# ==============================================================================
# CONFIGURACION DEL MOTOR BIO-SONAR (48 kHz / 10 Hz Pulse Rate)
# ==============================================================================
FS = 48000                  # 48 kHz
SPEED_OF_SOUND = 343.0      # m/s
F_START = 8000.0            # 8 kHz
F_END = 18000.0             # 18 kHz
CHIRP_DURATION = 0.015      # 15 ms
PULSE_INTERVAL = 0.100      # 100 ms (10 pulsos por segundo)
UDP_PORT = 9099             # Puerto local UDP para el motor C++
UDP_IP = "127.0.0.1"

# 128 canales de distancia: de 0 cm a 256 cm (2 cm por canal)
N_DISTANCE_CHANNELS = 128
MAX_RANGE_M = 2.56          # 2.56 metros

def generate_chirp(fs, duration, f0, f1):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    chirp = scipy.signal.chirp(t, f0=f0, t1=duration, f1=f1, method='linear')
    window = np.hanning(len(chirp))
    chirp = chirp * window
    chirp = chirp * 0.70 / np.max(np.abs(chirp))
    return chirp.astype(np.float32)

def main():
    print("=" * 70, flush=True)
    print("  [BIO-SONAR] ACOUSTIC BACKEND (Python -> C++ SNN Bridge)", flush=True)
    print(f"  Streaming UDP -> {UDP_IP}:{UDP_PORT} | Tasa: 10 Hz", flush=True)
    print("=" * 70, flush=True)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    chirp = generate_chirp(FS, CHIRP_DURATION, F_START, F_END)
    chirp_len = len(chirp)
    
    total_samples = int(FS * PULSE_INTERVAL)
    tx_buffer = np.zeros(total_samples, dtype=np.float32)
    tx_buffer[:chirp_len] = chirp
    
    sos = scipy.signal.butter(4, [F_START * 0.9, min(F_END * 1.1, FS/2 - 500)], btype='bandpass', fs=FS, output='sos')
    
    prev_distance_m = 0.0
    pulse_seq = 0
    
    print("[*] Enlace de audio activo. Transmitiendo ecos...", flush=True)
    
    try:
        while True:
            t0_loop = time.time()
            pulse_seq += 1
            
            # Emitir y grabar
            rx_data = sd.playrec(tx_buffer, samplerate=FS, channels=1, dtype='float32', blocking=True)
            rx_signal = rx_data.flatten()
            
            # Filtro y correlación cruzada (Matched Filter)
            rx_filtered = scipy.signal.sosfilt(sos, rx_signal)
            correlation = scipy.signal.correlate(rx_filtered, chirp, mode='full')
            analytic_envelope = np.abs(scipy.signal.hilbert(correlation))
            
            # Encontrar t0 (camino directo)
            t0_idx = np.argmax(analytic_envelope[:int(FS * 0.025)])
            
            # Muestrear los 128 canales de distancia a lo largo de los 2.56 metros
            # Distancia de ida y vuelta: tiempo = (distancia * 2) / SPEED_OF_SOUND
            distance_channels = np.zeros(N_DISTANCE_CHANNELS, dtype=np.float32)
            
            for ch in range(N_DISTANCE_CHANNELS):
                d_m = (ch + 1) * (MAX_RANGE_M / N_DISTANCE_CHANNELS)
                t_delay_sec = (d_m * 2.0) / SPEED_OF_SOUND
                samp_idx = t0_idx + int(t_delay_sec * FS)
                if samp_idx < len(analytic_envelope):
                    # Promediar una pequeña ventana alrededor del bin
                    w_rad = max(1, int(FS * 0.0005))
                    w_start = max(0, samp_idx - w_rad)
                    w_end = min(len(analytic_envelope), samp_idx + w_rad)
                    val = np.mean(analytic_envelope[w_start:w_end])
                    distance_channels[ch] = float(val)
            
            # Normalizar canales de distancia
            noise_floor = np.median(distance_channels)
            max_val = np.max(distance_channels) + 1e-6
            norm_channels = np.clip((distance_channels - noise_floor) / (max_val - noise_floor + 1e-6), 0.0, 1.0)
            
            # Detectar pico principal de distancia
            peaks, props = scipy.signal.find_peaks(norm_channels[8:], height=0.35, distance=4) # evitar los primeros 16 cm (zona ciega)
            
            detected_dist_m = 0.0
            if len(peaks) > 0:
                best_peak = peaks[np.argmax(props['peak_heights'])] + 8
                detected_dist_m = (best_peak + 1) * (MAX_RANGE_M / N_DISTANCE_CHANNELS)
            
            # Calcular velocidad Doppler aproximada (dD/dt)
            velocity_mps = 0.0
            if detected_dist_m > 0.0 and prev_distance_m > 0.0:
                velocity_mps = (detected_dist_m - prev_distance_m) / PULSE_INTERVAL
            if detected_dist_m > 0.0:
                prev_distance_m = detected_dist_m
            
            snr_db = float(10.0 * np.log10((max_val + 1e-6) / (noise_floor + 1e-6)))
            
            # Empaquetar datos para UDP:
            # Header: uint32 seq, float detected_dist_m, float velocity_mps, float snr_db (16 bytes)
            # Body: 128 floats (512 bytes)
            header = struct.pack('<Ifff', pulse_seq, float(detected_dist_m), float(velocity_mps), float(snr_db))
            body = norm_channels.astype('<f4').tobytes()
            
            sock.sendto(header + body, (UDP_IP, UDP_PORT))
            
            if pulse_seq % 10 == 0:
                dist_str = f"{detected_dist_m*100:.1f} cm" if detected_dist_m > 0 else "Sin eco"
                print(f"[Bio-Sonar] Seq #{pulse_seq:>5} | Distancia: {dist_str:<10} | Vel: {velocity_mps:>5.2f} m/s | SNR: {snr_db:>4.1f} dB", flush=True)
                
    except KeyboardInterrupt:
        print("\n[+] Backend de Bio-Sonar detenido.", flush=True)

if __name__ == "__main__":
    main()
