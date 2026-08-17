import numpy as np
import scipy.signal
import sounddevice as sd
import matplotlib.pyplot as plt
import os

FS = 48000
CHIRP_DURATION = 0.015
F_START = 8000.0
F_END = 18000.0
RECORD_DURATION = 0.25
SPEED_OF_SOUND = 343.0

def generate_chirp(fs, duration, f0, f1):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    chirp = scipy.signal.chirp(t, f0=f0, t1=duration, f1=f1, method='linear')
    window = np.hanning(len(chirp))
    chirp = chirp * window
    chirp = chirp * 0.70 / np.max(np.abs(chirp))
    return chirp.astype(np.float32)

def capture_and_plot():
    chirp = generate_chirp(FS, CHIRP_DURATION, F_START, F_END)
    total_samples = int(FS * RECORD_DURATION)
    tx_buffer = np.zeros(total_samples, dtype=np.float32)
    tx_buffer[:len(chirp)] = chirp
    
    print("[*] Emitiendo chirp de calibracion y capturando eco...")
    rx_data = sd.playrec(tx_buffer, samplerate=FS, channels=1, dtype='float32', blocking=True)
    rx_signal = rx_data.flatten()
    
    sos = scipy.signal.butter(4, [F_START * 0.9, min(F_END * 1.1, FS/2 - 500)], btype='bandpass', fs=FS, output='sos')
    rx_filtered = scipy.signal.sosfilt(sos, rx_signal)
    correlation = scipy.signal.correlate(rx_filtered, chirp, mode='full')
    analytic_envelope = np.abs(scipy.signal.hilbert(correlation))
    
    t0_idx = np.argmax(analytic_envelope[:int(FS*0.03)])
    
    # Eje X en distancia (metros)
    time_axis = np.arange(len(analytic_envelope)) / FS
    time_from_t0 = time_axis - (t0_idx / FS)
    distance_axis = (time_from_t0 * SPEED_OF_SOUND) / 2.0
    
    # Filtrar solo distancias positivas de 0 a 3 metros
    mask = (distance_axis >= 0.0) & (distance_axis <= 3.0)
    dist_plot = distance_axis[mask] * 100.0 # en cm
    env_plot = analytic_envelope[mask]
    
    # Detectar picos
    noise_floor = np.median(env_plot)
    peaks, props = scipy.signal.find_peaks(env_plot, height=noise_floor*2.5, distance=int(FS*0.001))
    
    plt.figure(figsize=(10, 5), dpi=120)
    plt.plot(dist_plot, env_plot, color='#00ffcc', lw=1.8, label='Respuesta al Impulso Acústico (RIR)')
    plt.axhline(noise_floor * 2.5, color='#ff0055', ls='--', alpha=0.7, label='Umbral de Ruido de Fondo')
    
    for p in peaks:
        d_cm = dist_plot[p]
        h = env_plot[p]
        plt.plot(d_cm, h, 'ro', markersize=8)
        plt.annotate(f'Eco: {d_cm:.1f} cm', (d_cm, h), textcoords="offset points", xytext=(0,10),
                     ha='center', fontsize=9, color='white',
                     bbox=dict(boxstyle='round,pad=0.3', fc='#1a1a2e', ec='#00ffcc', lw=1))
        
    plt.title('🦇 Bio-Sonar Acústico: Perfil de Distancia y Ecos Físicos', fontsize=12, fontweight='bold', color='white')
    plt.xlabel('Distancia al Obstáculo / Pared (cm)', fontsize=10, color='white')
    plt.ylabel('Amplitud del Eco (Normalizada)', fontsize=10, color='white')
    plt.grid(True, color='#333355', ls=':', alpha=0.6)
    plt.xlim(0, 300)
    
    # Fondo oscuro elegante
    plt.gca().set_facecolor('#0f111a')
    plt.gcf().patch.set_facecolor('#0a0c13')
    plt.tick_params(colors='white')
    plt.legend(facecolor='#1a1a2e', edgecolor='#00ffcc', labelcolor='white')
    
    out_dir = r"C:\Users\maruc\.gemini\antigravity\brain\4567119c-e0d3-4059-b403-0d5cb547ca41"
    out_path = os.path.join(out_dir, "grafica_bio_sonar_prueba_real.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"[+] Gráfica guardada exitosamente en: {out_path}")

if __name__ == "__main__":
    capture_and_plot()
