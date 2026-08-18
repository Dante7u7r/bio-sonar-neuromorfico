# 🦇 Bio-Sonar Neuromórfico: Ecolocalización Acústica en Tiempo Real (C++17 / Python)

[![C++17](https://img.shields.io/badge/Language-C%2B%2B17-blue.svg)](https://en.wikipedia.org/wiki/C%2B%2B17)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Zero GPU](https://img.shields.io/badge/Hardware-CPU%20Only%20%28Zero%20GPU%29-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

Un sistema biomimético de **ecolocalización activa y procesamiento espacial en tiempo real**, inspirado en la fisiología auditiva de los murciélagos (*Chiroptera*) y potenciado por un motor bio-computacional multirreino (**SNN + Physarum + Micelio**).

Utiliza los **altavoces y micrófonos estándar** de cualquier computadora o microcontrolador para emitir micro-pulsos de frecuencia modulada (chirps inaudibles de $8\text{ kHz} - 18\text{ kHz}$) y procesar los ecos de retorno mediante **líneas de retardo axonal y plasticidad sináptica STDP**, logrando detección milimétrica de obstáculos sin cámaras, sin LiDAR y sin GPU.

---

## 🔬 Arquitectura del Bio-Sonar

```
     [ Altavoz / Bocina ]                    [ Micrófono Estándar ]
              │                                        │
              ▼                                        ▼
      (Chirp 8 - 18 kHz) ───> [ Sala / Obstáculo ] ──> (Ecos Físicos)
                                                       │
                                                       ▼
                                       [ Backend Acústico Python ]
                                       • Filtro Casado (Matched Filter) @ 48 kHz
                                       • Envolvente Analítica de Hilbert
                                       • 128 Canales de Distancia (0 - 2.56 m)
                                                       │
                                                       ▼ (Streaming UDP:9099)
                                    [ AudioSonarAdapter (C++17) ]
                                    • Inyección de Corrientes Sinápticas
                                    • Gradientes Espaciales de Distancia
                                                       │
                                                       ▼
                                    [ 🧠 Motor Bio-Híbrido SNN ]
                                    • 274 Neuronas LIF Multicompartimentales
                                    • Cerebelo (Cancelación de Auto-Vocalización)
                                    • Physarum (Enrutamiento Libre de Obstáculos)
                                    • Radar de Navegación en Consola
```

---

## ⚡ Fundamento Físico: ¿Por qué Sonido y no Radio/Wi-Fi?

| Parámetro | Ondas de Radio / Wi-Fi | Ondas Sonoras (Bio-Sonar) |
|---|:---:|:---:|
| **Velocidad de Propagación ($c$)** | $300,000,000\text{ m/s}$ (Luz) | **$343\text{ m/s}$ (Sonido)** |
| **Tiempo de vuelo para 1 metro** | $3.3\text{ nanosegundos}$ (imperceptible para microcontroladores) | **$2.9\text{ milisegundos}$ (fácilmente medible)** |
| **Resolución por muestra @ 48 kHz** | $7.5\text{ metros}$ (borroso en Wi-Fi 20 MHz) | **$\sim 0.71\text{ centímetros}$ (precisión milimétrica)** |
| **Rebote en Superficies** | Difuso (atraviesa paredes y muebles) | **Especular (rebote limpio en yeso, madera, vidrio)** |

---

## 🚀 Inicio Rápido

### 1. Requisitos:
* Python 3.10+ con `numpy`, `scipy` y `sounddevice`:
  ```bash
  pip install numpy scipy sounddevice matplotlib
  ```
* Compilador **C++17** (MSVC en Windows o GCC/Clang en Linux/macOS).

---

### 2. Compilación del Motor C++

#### En Windows (MSVC):
```powershell
.\build.ps1
```

#### En Linux / macOS (CMake):
```bash
mkdir build && cd build
cmake ..
make -j4
```

---

### 3. Ejecución del Sistema en Tiempo Real

Abre dos terminales:

#### Terminal 1 (Motor Neuromórfico C++):
```powershell
# En Windows
.\bio_sonar.exe --sonar 9099

# En Linux
./build/bio_sonar --sonar 9099
```

#### Terminal 2 (Transmisor y Receptor de Audio):
```bash
python bio_sonar_backend.py
```

---

## 📁 Estructura del Repositorio

```
bio-sonar-neuromorfico/
├── PROYECTO_BATDRIVE.md           # Dossier técnico y comercial para Evaluación de Proyectos
├── audio_sonar_adapter.hpp        # Adaptador C++ para ingesta de paquetes UDP Bio-Sonar
├── audio_sonar_adapter.cpp
├── bio_sonar_backend.py           # Backend de audio en tiempo real (Matched Filter @ 48 kHz)
├── test_bio_sonar.py              # Script interactivo de prueba en terminal
├── plot_bio_sonar.py              # Generador de gráficas de respuesta al impulso acústico (RIR)
├── visor_sonar_3d.py              # Visualizador 3D de campo acústico y rutas
├── sensor_adapter.hpp             # Interfaz abstracta universal ISensorAdapter
├── cerebro.hpp                    # Núcleo SNN 274 Neuronas LIF + Plasticidad STDP
├── cerebro.cpp
├── physarum_optimizer.hpp         # Módulo de navegación morfogénica (Physarum)
├── cerebellar_model.hpp           # Cancelador cerebeloso de auto-sonido (Efference Copy)
├── basal_ganglia.hpp              # Vías de decisión motora Go/No-Go
├── mycelium_substrate.hpp         # Sustrato memristivo fúngico anti-drift
├── bio_hybrid_plant_fungi.hpp     # Modelos electrofisiológicos vegetales
├── main.cpp                       # Punto de entrada principal con Radar en Consola
├── build.ps1                      # Script de compilación para Windows
└── CMakeLists.txt                 # Archivo de construcción multiplataforma
```

---

## 📄 Documentación del Proyecto Académico y Comercial

Para consultar el estudio de mercado, fundamentación física acústica vs RF, comparativa con *Robat* (Tel Aviv University, 2018) y modelo de negocio para la materia de **Evaluación de Proyectos**, consulta:
👉 **[`PROYECTO_BATDRIVE.md`](PROYECTO_BATDRIVE.md)**

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Libre para fines educativos, de investigación y desarrollo comercial.

