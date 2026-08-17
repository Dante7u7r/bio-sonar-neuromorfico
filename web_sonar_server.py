import os
import sys
import time
import json
import threading
import numpy as np
import scipy.signal as signal
import sounddevice as sd
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# ==============================================================================
# SERVIDOR WEB DE BIO-SONAR ACÚSTICO EN TIEMPO REAL (Zero-Dependency Backend)
# ==============================================================================

PORT = 8080
SAMPLE_RATE = 48000
CHIRP_DURATION = 0.015    # 15 ms
CHIRP_F_START = 8000      # 8 kHz
CHIRP_F_END = 18000       # 18 kHz
SPEED_OF_SOUND = 343.0    # m/s
MAX_DISTANCE_M = 3.0
BUFFER_FRAMES = int(SAMPLE_RATE * (CHIRP_DURATION + 2.0 * MAX_DISTANCE_M / SPEED_OF_SOUND + 0.02))

# Generar señal chirp y filtro casado analítico
t_chirp = np.linspace(0, CHIRP_DURATION, int(SAMPLE_RATE * CHIRP_DURATION), endpoint=False)
window = signal.windows.tukey(len(t_chirp), alpha=0.15)
chirp_signal = signal.chirp(t_chirp, f0=CHIRP_F_START, t1=CHIRP_DURATION, f1=CHIRP_F_END, method='linear') * window
chirp_signal = chirp_signal.astype(np.float32)

ref_chirp = signal.hilbert(chirp_signal[::-1])

# Estado compartido de telemetría acústica
shared_sonar_lock = threading.Lock()
shared_sonar_data = {
    "seq": 0,
    "primary_distance_cm": 0.0,
    "velocity_mps": 0.0,
    "snr_db": 0.0,
    "peaks": [],
    "envelope": [0.0] * 128,
    "timestamp": time.time()
}

is_running = True

def audio_sonar_loop():
    global shared_sonar_data, is_running
    seq = 0
    prev_dist_m = 0.0
    prev_time = time.time()

    print("[*] Hilo de audio Bio-Sonar activo. Emitiendo pulsos a 48 kHz...", flush=True)

    while is_running:
        try:
            # 1. Emitir chirp y grabar eco físico
            rec_audio = sd.playrec(chirp_signal, samplerate=SAMPLE_RATE, channels=1, dtype='float32', blocking=True)
            rec_audio = rec_audio.flatten()

            now = time.time()
            dt = now - prev_time
            if dt <= 0: dt = 0.1

            # 2. Matched Filter
            corr = signal.fftconvolve(rec_audio, ref_chirp, mode='full')
            envelope = np.abs(corr[len(ref_chirp) - 1: len(ref_chirp) - 1 + BUFFER_FRAMES])

            # 3. Conversión de tiempo a distancia física
            time_axis = np.arange(len(envelope)) / SAMPLE_RATE
            dist_axis_cm = (time_axis * SPEED_OF_SOUND / 2.0) * 100.0

            # 4. Calibración y eliminación de diafonía directa (primeros 15 cm)
            idx_direct = np.argmax(envelope[:int(SAMPLE_RATE * 0.008)])
            dist_calibrated = dist_axis_cm - dist_axis_cm[idx_direct]

            valid_mask = (dist_calibrated >= 15.0) & (dist_calibrated <= 250.0)
            valid_dist = dist_calibrated[valid_mask]
            valid_env = envelope[valid_mask]

            if len(valid_env) == 0:
                continue

            # Normalizar
            noise_floor = np.median(valid_env)
            norm_env = np.maximum(0, valid_env - noise_floor)
            max_val = np.max(norm_env) if np.max(norm_env) > 1e-6 else 1.0
            norm_env /= max_val

            # 5. Detección de picos
            peaks_idx, _ = signal.find_peaks(norm_env, height=0.18, distance=int(SAMPLE_RATE * 0.04 / (SPEED_OF_SOUND / 2.0)))

            peaks_list = []
            primary_dist_cm = 0.0
            vel_mps = 0.0

            if len(peaks_idx) > 0:
                p_dists = valid_dist[peaks_idx]
                p_amps = norm_env[peaks_idx]

                sorted_indices = np.argsort(p_dists)
                primary_dist_cm = float(p_dists[sorted_indices[0]])

                for p_i in sorted_indices[:8]:
                    peaks_list.append({
                        "distance_cm": round(float(p_dists[p_i]), 1),
                        "amplitude": round(float(p_amps[p_i]), 3)
                    })

                # Velocidad Doppler
                if prev_dist_m > 0 and primary_dist_cm > 0:
                    curr_dist_m = primary_dist_cm / 100.0
                    vel_mps = float(np.clip((curr_dist_m - prev_dist_m) / dt, -5.0, 5.0))
                    prev_dist_m = curr_dist_m
                elif primary_dist_cm > 0:
                    prev_dist_m = primary_dist_cm / 100.0

            prev_time = now

            # SNR
            signal_power = np.mean(norm_env**2) + 1e-12
            noise_power = (noise_floor / (max_val + 1e-12))**2 + 1e-12
            snr_db = float(np.clip(10.0 * np.log10(signal_power / noise_power), 0.0, 45.0))

            # Resamplear envolvente a 128 puntos para la web
            resampled_env = signal.resample(norm_env, 128)
            resampled_env = np.clip(resampled_env, 0.0, 1.0).tolist()
            resampled_env = [round(float(v), 3) for v in resampled_env]

            # 6. Actualizar estado compartido
            with shared_sonar_lock:
                shared_sonar_data = {
                    "seq": seq,
                    "primary_distance_cm": round(primary_dist_cm, 1),
                    "velocity_mps": round(vel_mps, 2),
                    "snr_db": round(snr_db, 1),
                    "peaks": peaks_list,
                    "envelope": resampled_env,
                    "timestamp": now
                }

            seq += 1
            time.sleep(0.04)

        except Exception as e:
            print(f"[AUDIO ERROR] {e}", flush=True)
            time.sleep(0.1)

class SonarHttpHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        if self.path == "/api/sonar_frame":
            with shared_sonar_lock:
                payload = json.dumps(shared_sonar_data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
        else:
            super().do_GET()

    def log_message(self, format, *args):
        # Silenciar logs HTTP repetitivos para mantener la consola limpia
        pass

def main():
    global is_running
    print("=" * 75, flush=True)
    print("  [BIO-SONAR 3D] SERVIDOR WEB NATIVO EN TIEMPO REAL", flush=True)
    print(f"  Abre en tu navegador: http://localhost:{PORT}/", flush=True)
    print("=" * 75, flush=True)

    # Iniciar hilo de captura acústica
    audio_thread = threading.Thread(target=audio_sonar_loop, daemon=True)
    audio_thread.start()

    # Iniciar servidor HTTP
    server = ThreadingHTTPServer(("0.0.0.0", PORT), SonarHttpHandler)
    print(f"[+] Servidor Web activo en http://localhost:{PORT}/", flush=True)
    print("[*] Presiona Ctrl+C para detener el servidor.\n", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Apagando servidor Web...", flush=True)
        is_running = False
        server.shutdown()
        print("[+] Servidor detenido ordenadamente.", flush=True)

if __name__ == "__main__":
    main()
