// ==============================================================================
// BIO-SONAR 3D WEB APPLICATION (Three.js WebGL Engine)
// ==============================================================================

let scene, camera, renderer, controls;
let pointCloud, pointGeometry, pointMaterial;
let sensorMesh, radarRings = [];
const MAX_POINTS = 600;
const pointPositions = new Float32Array(MAX_POINTS * 3);
const pointColors = new Float32Array(MAX_POINTS * 3);
const pointSizes = new Float32Array(MAX_POINTS);

// Canvas RIR
const rirCanvas = document.getElementById('canvas-rir');
const rirCtx = rirCanvas ? rirCanvas.getContext('2d') : null;

// Elementos DOM
const elDistance = document.getElementById('val-distance');
const elVelocity = document.getElementById('val-velocity');
const elSnr = document.getElementById('val-snr');
const elFps = document.getElementById('val-fps');
const elPeakCount = document.getElementById('peak-count');
const elSeqCounter = document.getElementById('seq-counter');
const elEchoList = document.getElementById('echo-list');

let lastFetchTime = performance.now();
let frameCount = 0;
let fpsTimer = performance.now();

// Inicializar Three.js
function initThree() {
    const container = document.getElementById('canvas-3d-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06060c);
    scene.fog = new THREE.FogExp2(0x06060c, 0.003);

    camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    camera.position.set(0, 140, 220);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 + 0.1;
    controls.target.set(0, 0, 70);

    // Iluminación
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x00f3ff, 2, 300);
    pointLight.position.set(0, 50, 0);
    scene.add(pointLight);

    // Grid de piso
    const gridHelper = new THREE.GridHelper(400, 40, 0x18182e, 0x10101e);
    gridHelper.position.y = -10;
    scene.add(gridHelper);

    // Nodo del Sensor (Micrófono / Altavoz) en (0, 0, 0)
    const sensorGeo = new THREE.ConeGeometry(4, 8, 16);
    sensorGeo.rotateX(Math.PI / 2);
    const sensorMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff, wireframe: true });
    sensorMesh = new THREE.Mesh(sensorGeo, sensorMat);
    scene.add(sensorMesh);

    // Anillos de Radar de Distancia (25cm, 50cm, 100cm, 150cm, 200cm, 250cm)
    const ringRadii = [25, 50, 100, 150, 200, 250];
    ringRadii.forEach(radius => {
        const ringGeo = new THREE.BufferGeometry();
        const pts = [];
        const fovRad = Math.PI * 0.7; // Sector frontal de 126 grados
        for (let i = 0; i <= 60; i++) {
            const angle = -fovRad / 2 + (fovRad * i) / 60;
            pts.push(new THREE.Vector3(radius * Math.sin(angle), 0, radius * Math.cos(angle)));
        }
        ringGeo.setFromPoints(pts);
        const ringMat = new THREE.LineBasicMaterial({ color: 0x1f293d, transparent: true, opacity: 0.6 });
        const ringLine = new THREE.Line(ringGeo, ringMat);
        scene.add(ringLine);
        radarRings.push(ringLine);
    });

    // Nube de Puntos 3D Dinámica
    pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute('position', new THREE.BufferAttribute(pointPositions, 3));
    pointGeometry.setAttribute('color', new THREE.BufferAttribute(pointColors, 3));

    // Crear textura circular para partículas suaves
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.3, 'rgba(0, 243, 255, 0.8)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 32, 32);
    const particleTex = new THREE.CanvasTexture(canvas);

    pointMaterial = new THREE.PointsMaterial({
        size: 8.0,
        vertexColors: true,
        map: particleTex,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    pointCloud = new THREE.Points(pointGeometry, pointMaterial);
    scene.add(pointCloud);

    window.addEventListener('resize', onWindowResize);
    animate();
}

function onWindowResize() {
    const container = document.getElementById('canvas-3d-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

function animate() {
    requestAnimationFrame(animate);

    // Animación suave de pulsación del sensor
    const t = performance.now() * 0.003;
    sensorMesh.rotation.y = Math.sin(t) * 0.2;

    controls.update();
    renderer.render(scene, camera);

    // Calcular FPS
    frameCount++;
    if (performance.now() - fpsTimer >= 1000) {
        if (elFps) elFps.textContent = frameCount;
        frameCount = 0;
        fpsTimer = performance.now();
    }
}

// Histórico de ecos para estela 3D
const echoHistory = [];
const MAX_HISTORY_FRAMES = 20;

function updatePointCloud(peaks) {
    // Desvanecer histórico
    echoHistory.push(peaks || []);
    if (echoHistory.length > MAX_HISTORY_FRAMES) {
        echoHistory.shift();
    }

    let pIdx = 0;
    const totalHistory = echoHistory.length;

    for (let h = 0; h < totalHistory; h++) {
        const framePeaks = echoHistory[h];
        const ageNorm = (h + 1) / totalHistory; // 1.0 = más reciente

        framePeaks.forEach(peak => {
            if (pIdx >= MAX_POINTS - 20) return;

            const r = peak.distance_cm;
            const amp = peak.amplitude || 1.0;
            const numPoints = Math.max(3, Math.min(12, Math.floor(amp * 12)));

            for (let i = 0; i < numPoints; i++) {
                const angleX = -0.3 + (0.6 * i) / (numPoints - 1 || 1) + (Math.random() - 0.5) * 0.05;
                const angleZ = (Math.random() - 0.5) * 0.15;

                const x = r * Math.sin(angleX);
                const z = r * Math.cos(angleX) * Math.cos(angleZ);
                const y = r * Math.sin(angleZ);

                pointPositions[pIdx * 3] = x;
                pointPositions[pIdx * 3 + 1] = y;
                pointPositions[pIdx * 3 + 2] = z;

                // Color según distancia y desvanecimiento
                if (r < 70) {
                    // Eco cercano (Mano / Objeto): Neón Magenta / Oro
                    pointColors[pIdx * 3] = 1.0 * ageNorm;
                    pointColors[pIdx * 3 + 1] = 0.1 * ageNorm;
                    pointColors[pIdx * 3 + 2] = 0.5 * ageNorm;
                } else {
                    // Eco lejano (Pared / Fondo): Neón Cian
                    pointColors[pIdx * 3] = 0.0 * ageNorm;
                    pointColors[pIdx * 3 + 1] = 0.95 * ageNorm;
                    pointColors[pIdx * 3 + 2] = 1.0 * ageNorm;
                }

                pIdx++;
            }
        });
    }

    // Limpiar puntos sobrantes
    for (let i = pIdx; i < MAX_POINTS; i++) {
        pointPositions[i * 3] = 0;
        pointPositions[i * 3 + 1] = -1000; // fuera de la vista
        pointPositions[i * 3 + 2] = 0;
    }

    pointGeometry.attributes.position.needsUpdate = true;
    pointGeometry.attributes.color.needsUpdate = true;
}

// Dibujar envolvente analítica RIR en Canvas 2D
function drawRir(envelope, peaks) {
    if (!rirCtx || !envelope || envelope.length === 0) return;

    const w = rirCanvas.width;
    const h = rirCanvas.height;

    rirCtx.fillStyle = '#0c0c14';
    rirCtx.fillRect(0, 0, w, h);

    // Rejilla
    rirCtx.strokeStyle = '#1a1a2e';
    rirCtx.lineWidth = 1;
    for (let x = 0; x <= w; x += w / 4) {
        rirCtx.beginPath();
        rirCtx.moveTo(x, 0);
        rirCtx.lineTo(x, h);
        rirCtx.stroke();
    }

    // Curva de envolvente de eco
    rirCtx.strokeStyle = '#00f3ff';
    rirCtx.lineWidth = 2;
    rirCtx.beginPath();

    const len = envelope.length;
    for (let i = 0; i < len; i++) {
        const x = (i / (len - 1)) * w;
        const val = envelope[i]; // 0.0 a 1.0
        const y = h - val * (h - 20) - 10;
        if (i === 0) rirCtx.moveTo(x, y);
        else rirCtx.lineTo(x, y);
    }
    rirCtx.stroke();

    // Relleno degradado bajo la curva
    rirCtx.lineTo(w, h);
    rirCtx.lineTo(0, h);
    const fillGrad = rirCtx.createLinearGradient(0, 0, 0, h);
    fillGrad.addColorStop(0, 'rgba(0, 243, 255, 0.25)');
    fillGrad.addColorStop(1, 'rgba(0, 243, 255, 0.0)');
    rirCtx.fillStyle = fillGrad;
    rirCtx.fill();

    // Marcar picos detectados
    if (peaks && peaks.length > 0) {
        peaks.forEach(peak => {
            const distRatio = peak.distance_cm / 200.0;
            if (distRatio >= 0 && distRatio <= 1.0) {
                const px = distRatio * w;
                const py = h - peak.amplitude * (h - 20) - 10;

                rirCtx.fillStyle = '#ff0077';
                rirCtx.beginPath();
                rirCtx.arc(px, py, 5, 0, Math.PI * 2);
                rirCtx.fill();

                rirCtx.fillStyle = '#ffffff';
                rirCtx.font = '10px "Fira Code", monospace';
                rirCtx.fillText(`${Math.round(peak.distance_cm)}cm`, px - 12, py - 8);
            }
        });
    }
}

// Bucle de sondeo de alta velocidad (30 - 60 FPS)
async function fetchSonarData() {
    try {
        const res = await fetch('/api/sonar_frame');
        if (res.ok) {
            const data = await res.json();

            // 1. Actualizar métricas del header
            if (elDistance) {
                elDistance.textContent = data.primary_distance_cm > 0 ? data.primary_distance_cm.toFixed(1) : '--.-';
            }
            if (elVelocity) {
                elVelocity.textContent = (data.velocity_mps || 0).toFixed(2);
            }
            if (elSnr) {
                elSnr.textContent = (data.snr_db || 0).toFixed(1);
            }
            if (elSeqCounter) {
                elSeqCounter.textContent = `Seq #${data.seq || 0}`;
            }

            const peaks = data.peaks || [];
            if (elPeakCount) {
                elPeakCount.textContent = `${peaks.length} Ecos`;
            }

            // 2. Actualizar lista de ecos
            if (elEchoList) {
                if (peaks.length === 0) {
                    elEchoList.innerHTML = '<div class="echo-log-item empty">Buscando ecos acústicos...</div>';
                } else {
                    elEchoList.innerHTML = peaks.map((p, idx) => `
                        <div class="echo-log-item">
                            <span>#${idx + 1} ${idx === 0 ? '🎯 PRINCIPAL' : 'REBOTE'}</span>
                            <span class="echo-dist">${p.distance_cm.toFixed(1)} cm</span>
                            <span class="echo-amp">${(p.amplitude * 100).toFixed(0)}%</span>
                        </div>
                    `).join('');
                }
            }

            // 3. Actualizar 3D y 2D
            updatePointCloud(peaks);
            drawRir(data.envelope || [], peaks);
        }
    } catch (e) {
        // En caso de desconexión momentánea
    }

    // Siguiente cuadro
    setTimeout(fetchSonarData, 30);
}

// Iniciar aplicación
window.addEventListener('DOMContentLoaded', () => {
    initThree();
    fetchSonarData();
});
