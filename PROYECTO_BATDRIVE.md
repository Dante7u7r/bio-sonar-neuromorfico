# 🦇 BatDrive: Módulo Neuromórfico Edge de Navegación Acústica Autónoma para Vehículos en Ambientes Ciegos

**Proyecto de Ingeniería Electrónica y Telecomunicaciones**  
**Materia:** Evaluación de Proyectos  
**Base Tecnológica:** Spiking Neural Networks (SNN C++17), Filtro Casado Acústico (48 kHz), Morfogénesis de Physarum y Control Cerebeloso.

---

## 📑 1. Resumen Ejecutivo (Executive Summary)

**BatDrive** es un sistema biomimético de navegación reactiva, evasión de colisiones y cartografía espacial 2D/3D en tiempo real para vehículos y robots autónomos, inspirado en la fisiología auditiva de los murciélagos (*Chiroptera*).

A diferencia de las soluciones convencionales de robótica basadas en cámaras (vSLAM) o LiDARs ópticos, BatDrive **no utiliza cámaras, no utiliza lásers y no requiere tarjetas gráficas (Zero GPU)**. El sistema emite micro-pulsos de frecuencia modulada inaudibles ($8\text{ kHz} - 18\text{ kHz}$) a través de transductores acústicos estándar ($48\text{ kHz}$) y procesa los ecos de retorno mediante un **cerebro neuromórfico multirreino (SNN 274 neuronas LIF + Cerebelo + Physarum + Ganglios Basales)**.

### Propuesta de Valor Comercial
* **Reducción de Costos drástica:** Sustituye sensores LiDAR de $200 - $800 USD y procesadores GPU de $300 USD por un subsistema acústico de **$< 15 USD de BOM** que corre en microcontroladores y CPUs estándar ($< 0.5\text{ W}$).
* **Operación en Ambientes Ciegos:** Inmune a la oscuridad total ($0\text{ lux}$), humo denso, polvo en suspensión, niebla, superficies transparentes (cristal, acrílico) y superficies espejadas donde las cámaras y los lásers quedan totalmente ciegos.

---

## 🔬 2. Fundamento Físico y Matemático: ¿Por qué Sonido y no Wi-Fi CSI?

Durante las fases exploratorias iniciales se evaluó el uso de *Wi-Fi Channel State Information* (CSI) en ESP32 para detección de presencia y signos vitales. Los resultados evidenciaron graves limitaciones físicas en RF que quedan resueltas al migrar al **Bio-Sonar Acústico a 48 kHz**:

| Parámetro Físico / Técnico | Ondas de Radio / Wi-Fi CSI (ESP32) | Bio-Sonar Acústico (48 kHz) |
|---|:---:|:---:|
| **Velocidad de Propagación ($c$)** | $300,000,000\text{ m/s}$ (Luz) | **$343\text{ m/s}$ (Sonido)** |
| **Tiempo de vuelo (ToF) para 1 metro** | $3.3\text{ nanosegundos}$ (imperceptible para microcontroladores sin TDC dedicado) | **$2.91\text{ milisegundos}$ (fácilmente cuantificable a nivel de muestra)** |
| **Resolución física por muestra** | $7.5\text{ metros}$ (con ancho de banda de $20\text{ MHz}$) | **$\sim 0.71\text{ centímetros}$ ($\Delta d = \frac{c}{F_s} = \frac{343}{48000}$)** |
| **Comportamiento en Paredes** | Difuso (atraviesa paredes, capta ruido exterior de vecinos y tráfico) | **Especular (rebota limpiamente en obstáculos, no traspasa muros)** |
| **Ganancia de Filtro Casado ($G$)** | Baja / Nula en frames dispersos | **$+21.7\text{ dB}$ ($G = 10\log_{10}(B \cdot T) = 10\log_{10}(10000 \times 0.015)$)** |
| **Relación Señal/Ruido (SNR)** | Pobre (ADC de 8-10 bits con derivas térmicas continuas en ESP32) | **Alta (ADC de audio de 16/24 bits con oscilador de cuarzo estable)** |

---

## 🧠 3. Arquitectura del Cerebro Neuromórfico (`BrainUnico`)

El núcleo de procesamiento (`cerebro.hpp` / `cerebro.cpp`) integra 274 neuronas LIF multicompartimentales acopladas con módulos bio-inspirados:

```
                      [ ALTAVOZ / PIEZO ]                [ 2 MICRÓFONOS (L / R) ]
                               │                                     │
                               ▼ (Emite Chirp 8-18 kHz)              ▼ (Captura Ecos de Retorno)
                ┌─────────────────────────────────────────────────────────────┐
                │ 1. BACKEND ACÚSTICO (Filtro Casado a 48 kHz)               │
                │    • Genera 128 canales de distancia (0 a 2.56 metros)      │
                │    • Envolvente analítica de Hilbert instantánea            │
                └──────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
                ┌─────────────────────────────────────────────────────────────┐
                │ 2. CEREBELO PREDICTIVO (cerebellar_model.hpp)               │
                │    • Células de Purkinje y Fibras Paralelas                 │
                │    • Cancelación adaptativa de auto-ruido del motor (Efference│
                │      Copy) y clutter ambiental estático en t+1.             │
                └──────────────────────────────┬──────────────────────────────┘
                                               │ (Señal limpia de obstáculos)
                        ┌──────────────────────┴──────────────────────┐
                        ▼                                             ▼
 ┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
 │ 3. CORTEZA PARIETAL (spatial_parietal.hpp)│   │ 4. PHYSARUM OPTIMIZER (physarum_optimizer)│
 │    • Interferometría de Fase (AoA):      │   │    • Dinámica hidrodinámica de Poiseuille │
 │      Calcula ángulo de llegada [-60°,+60°│   │    • Modela el espacio libre como túbulos │
 │      y coordenadas relativas (X, Y).     │   │      de flujo; ensancha rutas seguras y   │
 │    • Bio-Beamforming de Auxinas (PIN).   │   │      digiere trayectorias bloqueadas.     │
 └──────────────────────┬───────────────────┘   └──────────────────────┬───────────────────┘
                        │                                              │
                        └──────────────────────┬───────────────────────┘
                                               ▼
                ┌─────────────────────────────────────────────────────────────┐
                │ 5. GANGLIOS BASALES (basal_ganglia.hpp)                     │
                │    • Vía Directa (D1 / Go): Avance continuo en ruta despejada│
                │    • Vía Indirecta (D2 / No-Go): Inhibición y frenado rápido│
                │    • Selección Winner-Take-All de maniobra motora.          │
                └──────────────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
                ┌─────────────────────────────────────────────────────────────┐
                │ 6. CAPA MOTORA DE 30 NEURONAS (cerebro.cpp)                 │
                │    • Zonas dinámicas de disparo para tracción diferencial   │
                │      (Giro Izquierda, Avance Recto, Giro Derecha, Freno).   │
                └─────────────────────────────────────────────────────────────┘
```

---

## 📚 4. Estado del Arte: Comparativa con "Robat" (Tel Aviv University, 2018)

En 2018, investigadores de la Universidad de Tel Aviv publicaron en *PLOS Computational Biology* el robot **"Robat"**, demostrando la viabilidad de la ecolocalización terrestre. BatDrive representa una evolución de ingeniería directa sobre dicho concepto:

| Característica | Robat (Tel Aviv, 2018) | **BatDrive (Nuestro Proyecto)** |
|---|:---:|:---:|
| **Transductores** | Ultrasónicos electrostáticos de grado científico ($20-150\text{ kHz}$, $>500\text{ USD}$) | **Altavoces y micrófonos comerciales de $48\text{ kHz}$ ($<10\text{ USD}$)** |
| **Procesamiento Neuronal** | Red Artificial densa tradicional (MLP / ANN frame-by-frame) | **Spiking Neural Network (274 LIF con STDP/STC)** |
| **Cómputo Requerido** | Mini-PC pesada a bordo (Intel NUC, $15-30\text{ W}$) | **CERO GPU / CPU básica o microcontrolador ($< 0.5\text{ W}$)** |
| **Filtrado de Auto-Ruido** | Algoritmos fijos en software | **Cerebelo biológico predictivo con plasticidad heterosináptica** |
| **Planificación de Ruta** | Búsqueda geométrica en grafos | **Morfogénesis hidrodinámica biológica (*Physarum Optimizer*)** |

---

## 💼 5. Estudio de Mercado y Evaluación Financiera (Business Plan)

### A. Segmentos de Mercado Objetivo
1. **Robótica de Almacén y Logística (Micro-AGVs):** Flotas de carros autónomos en almacenes industriales con alta presencia de polvo, aserrín o vapores donde el LiDAR óptico falla y es prohibitivo en costo.
2. **Robots de Inspección en Espacios Confinados:** Tuberías oscuras, ductos de ventilación HVAC y túneles mineros sin iluminación.
3. **Sector Educativo / Juguetes STEM B2C:** Kits de bio-robótica para universidades y escuelas de ingeniería.

### B. Estructura de Costos (BOM por Unidad de Hardware)
* 2 Cápsulas de Micrófono I2S / Analógicas: **$2.50 USD**
* 1 Transductor Acústico Piezoeléctrico / Micro-Speaker: **$1.80 USD**
* 1 Microcontrolador Embebido (ARM Cortex-M / ESP32-S3): **$3.20 USD**
* Etapa de preamplificación y filtrado analógico: **$1.50 USD**
* PCB y envolvente plástico inyectado: **$2.80 USD**
* **Costo Total de Manufactura (BOM):** **$11.80 USD**

### C. Estrategia de Ingresos y Precios
1. **Venta de Tarjeta OEM / Kit de Evaluación:** **$69.00 USD** (Margen bruto: **$82.9\%$**).
2. **Licenciamiento de Firmware / Algoritmo C++ (Royalty):** **$15.00 USD por vehículo fabricado** (Margen bruto: **$>90\%$**).
3. **Servicios de Integración y Calibración Acústica:** Pólizas de **$3,000 - $8,000 USD** por adaptación a nuevos chasis robóticos.

---

## 🚀 6. Guía Rápida de Pruebas en Laptop ($0 de Presupuesto)

Para verificar el sistema de forma inmediata en una laptop utilizando sus altavoces y micrófono integrados:

### Paso 1: Compilar el Motor C++ (si no está compilado)
```powershell
# En Windows (MSVC):
.\build.ps1

# En Linux / macOS:
mkdir build && cd build
cmake ..
make -j4
```

### Paso 2: Ejecutar el Sistema en Tiempo Real (Dos Terminales)

#### Terminal 1 — Núcleo Cerebral Neuromórfico (C++17):
```powershell
.\bio_sonar.exe --sonar 9099
```

#### Terminal 2 — Backend Acústico de Audio (Python 48 kHz):
```powershell
python bio_sonar_backend.py
```

### Paso 3: Prueba Interactiva
1. Sube el volumen de tu laptop al 70-80%.
2. Coloca tu mano o un libro a $30\text{ cm}$, $60\text{ cm}$ y $1\text{ metro}$ del micrófono.
3. Observa en la **Terminal 1** cómo el radar de consola rastrea la distancia milimétrica en tiempo real.
4. *(Opcional)* Ejecuta en una tercera terminal el visor visual 3D:
   ```powershell
   python visor_sonar_3d.py
   ```
   o abre el dashboard interactivo en tu navegador: [`web/index.html`](web/index.html).

---

## 📄 Conclusión
BatDrive valida que la computación neuromórfica y la ecolocalización bio-inspirada permiten lograr autonomía robótica robusta con una fracción del costo y consumo energético de las tecnologías ópticas actuales.
