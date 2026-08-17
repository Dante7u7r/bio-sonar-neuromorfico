import numpy as np
import scipy.signal
import sounddevice as sd
import time
import sys

# ==============================================================================
# PARAMETROS DE BIO-SONAR ACUSTICO (ECOLOCALIZACION BIOMIMETICA)
# ==============================================================================
FS = 48000                  # Tasa de muestreo (48 kHz estándar de alta definición)
SPEED_OF_SOUND = 343.0      # Velocidad del sonido en el aire a 20°C (m/s)

# Rango de frecuencias del Chirp (Modulación de Frecuencia Lineal - LFM)
F_START = 8000.0            # Frecuencia inicial (8 kHz)
F_END = 18000.0             # Frecuencia final (18 kHz)
CHIRP_DURATION = 0.015      # Duración del pulso: 15 milisegundos
RECORD_DURATION = 0.25      # Ventana de escucha: 250 ms (Alcance max teórico ~40 metros)
MIN_DISTANCE_M = 0.15       # Distancia mínima ciega (15 cm, zona del altavoz al micro)
MAX_DISTANCE_M = 4.00       # Distancia máxima de búsqueda (4 metros)

def generate_chirp(fs, duration, f0, f1):
    """Genera un pulso LFM con ventana de Hann para evitar clics del altavoz."""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    # Chirp de frecuencia lineal
    chirp = scipy.signal.chirp(t, f0=f0, t1=duration, f1=f1, method='linear')
    # Ventana de Hann para suavizar los bordes
    window = np.hanning(len(chirp))
    chirp = chirp * window
    # Normalizar amplitud al 70% para no distorsionar
    chirp = chirp * 0.70 / np.max(np.abs(chirp))
    return chirp.astype(np.float32)

def main():
    print("=" * 80)
    print("  🦇 BIO-SONAR NEUROMORFICO: ECOLOCALIZACION ACUSTICA EN TIEMPO REAL")
    print(f"  Banda: {F_START/1000:.1f} kHz -> {F_END/1000:.1f} kHz | Fs: {FS} Hz")
    print("  Resolucion fisica: ~0.7 cm por muestra de audio")
    print("=" * 80)
    
    # 1. Generar pulso de referencia (Plantilla coclear)
    chirp = generate_chirp(FS, CHIRP_DURATION, F_START, F_END)
    chirp_len = len(chirp)
    
    # Crear buffer de transmisión (chirp + silencio para escuchar ecos)
    total_samples = int(FS * RECORD_DURATION)
    tx_buffer = np.zeros(total_samples, dtype=np.float32)
    tx_buffer[:chirp_len] = chirp
    
    print("\n[*] Calibrando microfono y altavoces...")
    print("[*] COLOCA TU MANO O UN OBJETO FRENTE AL MICROFONO (a 30 cm - 1 metro)")
    print("[*] Presiona Ctrl+C para salir.\n")
    time.sleep(1.0)
    
    print(f"{'Tiempo':<8} | {'Distancia Estimada':<20} | {'Retardo':<10} | {'Radar Grafico (0 cm -> 200 cm)':<40}")
    print("-" * 88)
    
    step = 0
    history_distances = []
    
    try:
        while True:
            step += 1
            # 2. Emitir pulso y grabar respuesta simultaneamente (Full-Duplex I/O)
            rx_data = sd.playrec(tx_buffer, samplerate=FS, channels=1, dtype='float32', blocking=True)
            rx_signal = rx_data.flatten()
            
            # 3. Filtro Paso-Banda para aislar la banda del chirp y rechazar ruido ambiental
            sos = scipy.signal.butter(4, [F_START * 0.9, min(F_END * 1.1, FS/2 - 500)], btype='bandpass', fs=FS, output='sos')
            rx_filtered = scipy.signal.sosfilt(sos, rx_signal)
            
            # 4. Correlacion Cruzada (Matched Filter - Simulador de Línea de Retardo Axonal)
            correlation = scipy.signal.correlate(rx_filtered, chirp, mode='full')
            # Transformada de Hilbert para obtener la envolvente analitica instantánea
            analytic_envelope = np.abs(scipy.signal.hilbert(correlation))
            
            # 5. Deteccion del Camino Directo (Direct Path t0: Altavoz -> Microfono)
            # El pico maximo inicial en los primeros 10 ms corresponde a la emision directa
            direct_search_window = int(FS * 0.030) # 30 ms
            t0_idx = np.argmax(analytic_envelope[:direct_search_window])
            
            # 6. Deteccion del Eco de Retorno (Pared / Mano)
            # Buscar picos despues del camino directo (evitando la zona ciega inicial)
            blind_samples = int((MIN_DISTANCE_M * 2.0 / SPEED_OF_SOUND) * FS)
            max_samples = int((MAX_DISTANCE_M * 2.0 / SPEED_OF_SOUND) * FS)
            
            search_start = t0_idx + blind_samples
            search_end = min(t0_idx + max_samples, len(analytic_envelope))
            
            if search_end > search_start:
                echo_region = analytic_envelope[search_start:search_end]
                # Umbral adaptativo: 3x el ruido medio de fondo
                noise_floor = np.median(echo_region)
                peak_threshold = max(noise_floor * 2.5, np.max(echo_region) * 0.35)
                
                peaks, properties = scipy.signal.find_peaks(echo_region, height=peak_threshold, distance=int(FS * 0.001))
                
                if len(peaks) > 0:
                    # Seleccionar el eco mas prominente (o el primer eco significativo)
                    strongest_peak = peaks[np.argmax(properties['peak_heights'])]
                    echo_idx = search_start + strongest_peak
                    
                    delay_samples = echo_idx - t0_idx
                    delay_sec = delay_samples / FS
                    # Distancia de ida y vuelta dividida entre 2
                    distance_m = (delay_sec * SPEED_OF_SOUND) / 2.0
                    distance_cm = distance_m * 100.0
                    
                    history_distances.append(distance_cm)
                    
                    # Barra visual ASCII de distancia (0 cm a 200 cm)
                    bar_len = 35
                    bar_pos = int(min(distance_cm / 200.0, 1.0) * bar_len)
                    radar_bar = "[" + " " * bar_pos + "🎯" + " " * (bar_len - bar_pos) + "]"
                    
                    status = f"✅ {distance_cm:>6.1f} cm ({distance_m:.2f} m)"
                    delay_str = f"{delay_sec*1000:>5.2f} ms"
                else:
                    radar_bar = "[" + " " * 35 + "]"
                    status = "🔍 Buscando eco..."
                    delay_str = "-- ms"
            else:
                radar_bar = "[" + " " * 35 + "]"
                status = "⚠️ Fuera de rango"
                delay_str = "-- ms"
            
            t_now = step * RECORD_DURATION
            print(f"{t_now:>6.1f}s | {status:<20} | {delay_str:<10} | {radar_bar:<40}")
            sys.stdout.flush()
            
            # Pausa breve entre pulsos
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n[+] Bio-Sonar detenido por el usuario.")
        if history_distances:
            print(f"[+] Distancia promedio detectada: {np.mean(history_distances):.1f} cm")
            print(f"[+] Rango observado: {np.min(history_distances):.1f} cm - {np.max(history_distances):.1f} cm")
        print("[+] Prueba completada exitosamente.")

if __name__ == "__main__":
    main()
