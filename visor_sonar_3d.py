import sys
import time
import numpy as np
import scipy.signal as signal
import sounddevice as sd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from collections import deque

# ==============================================================================
# VISOR 3D DE ECO-LOCALIZACIÓN ACÚSTICA EN TIEMPO REAL (BIO-SONAR)
# ==============================================================================

SAMPLE_RATE = 48000
CHIRP_DURATION = 0.015    # 15 ms
CHIRP_F_START = 8000      # 8 kHz
CHIRP_F_END = 18000       # 18 kHz
SPEED_OF_SOUND = 343.0    # m/s
MAX_DISTANCE_M = 3.0      # Rango máximo 3 metros (300 cm)
BUFFER_FRAMES = int(SAMPLE_RATE * (CHIRP_DURATION + 2.0 * MAX_DISTANCE_M / SPEED_OF_SOUND + 0.02))

# Generar señal chirp y filtro casado analítico
t_chirp = np.linspace(0, CHIRP_DURATION, int(SAMPLE_RATE * CHIRP_DURATION), endpoint=False)
window = signal.windows.tukey(len(t_chirp), alpha=0.15)
chirp_signal = signal.chirp(t_chirp, f0=CHIRP_F_START, t1=CHIRP_DURATION, f1=CHIRP_F_END, method='linear') * window
chirp_signal = chirp_signal.astype(np.float32)

# Referencia analítica de Hilbert para envolvente instantánea
ref_chirp = signal.hilbert(chirp_signal[::-1])

# Buffer circular para histórico de ecos 3D
MAX_HISTORY = 40
history_points = deque(maxlen=MAX_HISTORY)  # [(x, y, z, intensity, age)]

def main():
    print("=" * 75)
    print("  [BIO-SONAR] VISOR 3D DE ECO-LOCALIZACION ACUSTICA EN TIEMPO REAL")
    print("  Prueba estatica: Coloca tu mano o un objeto frente al microfono.")
    print("=" * 75)

    # Configurar Matplotlib en modo interactivo
    plt.ion()
    fig = plt.figure(figsize=(10, 8), facecolor='#111118')
    ax = fig.add_subplot(111, projection='3d', facecolor='#111118')

    # Configuración de ejes 3D
    ax.set_xlim([-200, 200])
    ax.set_ylim([0, 250])
    ax.set_zlim([-150, 150])
    ax.set_xlabel("Lateral X (cm)", color='#aaaaaa', labelpad=10)
    ax.set_ylabel("Distancia Frontal Y (cm)", color='#aaaaaa', labelpad=10)
    ax.set_zlabel("Altura Z (cm)", color='#aaaaaa', labelpad=10)
    ax.tick_params(colors='#888888')
    
    # Líneas de rejilla y paneles oscuros
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#333344')
    ax.yaxis.pane.set_edgecolor('#333344')
    ax.zaxis.pane.set_edgecolor('#333344')
    ax.grid(True, linestyle=':', color='#333344', alpha=0.6)

    # Título en pantalla
    title_text = fig.suptitle("BIO-SONAR 3D: DETECCIÓN DE ECOS FÍSICOS", color='#00ffcc', fontsize=14, fontweight='bold', y=0.95)
    info_text = fig.text(0.5, 0.03, "Iniciando captura de audio...", color='#ffffff', ha='center', fontsize=11, family='monospace')

    # Posición del sensor (Micrófono / Altavoz) en (0, 0, 0)
    sensor_scatter = ax.scatter([0], [0], [0], color='#00ffcc', s=120, marker='^', label='Micrófono / Sensor')

    # Arcos de radar fijos de referencia (50cm, 100cm, 150cm, 200cm)
    theta_rad = np.linspace(-np.pi/3, np.pi/3, 50)
    for r_ref in [50, 100, 150, 200]:
        x_arc = r_ref * np.sin(theta_rad)
        y_arc = r_ref * np.cos(theta_rad)
        z_arc = np.zeros_like(x_arc)
        ax.plot(x_arc, y_arc, z_arc, color='#223344', linestyle='--', alpha=0.5)
        ax.text(x_arc[-1] + 5, y_arc[-1], 0, f"{r_ref}cm", color='#446688', fontsize=8)

    # Dispersión dinámica de puntos 3D de eco
    echo_scatter = ax.scatter([], [], [], c=[], cmap='plasma', s=40, alpha=0.8, vmin=0.0, vmax=1.0)

    # Vista inicial 3D elevada
    ax.view_init(elev=25, azim=-60)
    plt.tight_layout()
    plt.show(block=False)

    print("[*] Sensor acústico listo. Abriendo ventana 3D...")
    print("[*] Acerca o aleja tu mano frente al micrófono para ver los puntos 3D moverse en vivo.\n")

    pulse_seq = 0

    while plt.fignum_exists(fig.number):
        try:
            # 1. Emisión y Grabación simultánea del pulso acústico
            rec_audio = sd.playrec(chirp_signal, samplerate=SAMPLE_RATE, channels=1, dtype='float32', blocking=True)
            rec_audio = rec_audio.flatten()

            # 2. Filtro Casado con señal de referencia
            corr = signal.fftconvolve(rec_audio, ref_chirp, mode='full')
            envelope = np.abs(corr[len(ref_chirp) - 1: len(ref_chirp) - 1 + BUFFER_FRAMES])

            # 3. Conversión de tiempo a distancia física
            time_axis = np.arange(len(envelope)) / SAMPLE_RATE
            dist_axis_cm = (time_axis * SPEED_OF_SOUND / 2.0) * 100.0

            # 4. Encontrar el eco directo (bocina a micrófono) y enmascarar zona ciega (primeros 15 cm)
            idx_direct = np.argmax(envelope[:int(SAMPLE_RATE * 0.008)])
            dist_calibrated = dist_axis_cm - dist_axis_cm[idx_direct]
            
            valid_mask = (dist_calibrated >= 15.0) & (dist_calibrated <= 250.0)
            valid_dist = dist_calibrated[valid_mask]
            valid_env = envelope[valid_mask]

            if len(valid_env) == 0:
                continue

            # Normalizar envolvente
            noise_floor = np.median(valid_env)
            norm_env = (valid_env - noise_floor)
            norm_env = np.maximum(0, norm_env)
            max_val = np.max(norm_env) if np.max(norm_env) > 1e-6 else 1.0
            norm_env /= max_val

            # 5. Detección de Picos de Eco Físicos
            peaks, props = signal.find_peaks(norm_env, height=0.18, distance=int(SAMPLE_RATE * 0.05 / (SPEED_OF_SOUND / 2.0)))

            current_points = []
            detected_dist_str = "Buscando ecos..."

            if len(peaks) > 0:
                peak_dists = valid_dist[peaks]
                peak_amps = norm_env[peaks]

                # Ordenar por cercanía
                sorted_indices = np.argsort(peak_dists)
                primary_dist = peak_dists[sorted_indices[0]]
                primary_amp = peak_amps[sorted_indices[0]]

                detected_dist_str = f"Eco Principal: {primary_dist:.1f} cm | Ecos Secundarios: {len(peaks)-1}"

                # Mapear picos a un arco tridimensional de reflexión
                for p_idx in sorted_indices:
                    r_cm = peak_dists[p_idx]
                    amp = peak_amps[p_idx]
                    
                    # Generar un clúster de puntos en el arco frontal a esa distancia exacta r
                    n_subpoints = max(5, int(amp * 15))
                    angles = np.linspace(-0.35, 0.35, n_subpoints)
                    z_angles = np.linspace(-0.2, 0.2, n_subpoints)

                    for a_x, a_z in zip(angles, z_angles):
                        x = r_cm * np.sin(a_x)
                        y = r_cm * np.cos(a_x) * np.cos(a_z)
                        z = r_cm * np.sin(a_z)
                        current_points.append((x, y, z, float(amp), 1.0))

            # Agregar nuevos puntos al histórico con factor de desvanecimiento
            history_points.append(current_points)

            # 6. Recopilar todos los puntos del histórico para renderizado 3D
            all_x, all_y, all_z, all_colors, all_sizes = [], [], [], [], []
            
            for frame_idx, frame_pts in enumerate(history_points):
                fade = (frame_idx + 1) / len(history_points)  # Más viejo = más transparente/pequeño
                for (px, py, pz, p_amp, _) in frame_pts:
                    all_x.append(px)
                    all_y.append(py)
                    all_z.append(pz)
                    all_colors.append(p_amp * fade)
                    all_sizes.append(15 + 45 * p_amp * fade)

            # 7. Actualizar el gráfico 3D
            if len(all_x) > 0:
                echo_scatter._offsets3d = (all_x, all_y, all_z)
                echo_scatter.set_array(np.array(all_colors))
                echo_scatter.set_sizes(np.array(all_sizes))
            else:
                echo_scatter._offsets3d = ([], [], [])

            info_text.set_text(f"Seq #{pulse_seq:04d} | {detected_dist_str} | Tasa: ~6 Hz")
            
            fig.canvas.draw_idle()
            fig.canvas.flush_events()

            pulse_seq += 1
            time.sleep(0.04)

        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            time.sleep(0.1)

    print("\n[+] Visor 3D cerrado.")

if __name__ == "__main__":
    main()
