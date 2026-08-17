// ==============================================================================
// BLOODHOUND TACTICAL 3D BIO-SONAR SCANNER (Three.js WebGL Engine)
// ==============================================================================

let scene, camera, renderer, controls;
let sensorMesh, pulseWaveMesh, scanRingRipples = [];
let obstacleObjectGroup, wallPlanesGroup;
let targetDiamondMarker, targetLaserBeam;
let pointCloud, pointGeometry;

const MAX_POINTS = 500;
const pointPositions = new Float32Array(MAX_POINTS * 3);
const pointColors = new Float32Array(MAX_POINTS * 3);

// Canvas 2D
const rirCanvas = document.getElementById('canvas-rir');
const rirCtx = rirCanvas ? rirCanvas.getContext('2d') : null;

// Elementos DOM
const elDistance = document.getElementById('val-distance');
const elVelocity = document.getElementById('val-velocity');
const elSnr = document.getElementById('val-snr');
const elTargetStatus = document.getElementById('target-status');
const elPeakCount = document.getElementById('peak-count');
const elSeqCounter = document.getElementById('seq-counter');
const elEchoList = document.getElementById('echo-list');

// Variables de animación de onda Bloodhound
let pulseRadius = 0.0;
const MAX_SCAN_RANGE_CM = 250.0;
const PULSE_SPEED = 220.0; // cm/s en simulación visual

function initThree() {
    const container = document.getElementById('canvas-3d-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06060a);
    scene.fog = new THREE.FogExp2(0x06060a, 0.0035);

    camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    camera.position.set(0, 160, 240);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.target.set(0, 0, 75);

    // Iluminación Táctica
    const ambientLight = new THREE.AmbientLight(0xffaa00, 0.4);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xff7700, 2.5, 350);
    pointLight.position.set(0, 40, 0);
    scene.add(pointLight);

    // Rejilla Táctica de Piso Estilo Radar
    const gridHelper = new THREE.GridHelper(400, 40, 0xff7700, 0x1f1510);
    gridHelper.position.y = -10;
    scene.add(gridHelper);

    // Nodo del Sensor (Bocina / Micrófono) en (0, 0, 0)
    const sensorGeo = new THREE.OctahedronGeometry(6, 0);
    const sensorMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff, wireframe: true });
    sensorMesh = new THREE.Mesh(sensorGeo, sensorMat);
    scene.add(sensorMesh);

    // 1. Onda Expansiva Táctica Bloodhound (Volumetric Sonar Dome)
    const pulseGeo = new THREE.SphereGeometry(1, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    const pulseMat = new THREE.MeshBasicMaterial({
        color: 0xff7700,
        wireframe: true,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide
    });
    pulseWaveMesh = new THREE.Mesh(pulseGeo, pulseMat);
    scene.add(pulseWaveMesh);

    // Anillos de Radar de Distancia Estilo Bloodhound
    const radarRanges = [25, 50, 100, 150, 200, 250];
    radarRanges.forEach(r => {
        const ringGeo = new THREE.BufferGeometry();
        const pts = [];
        const fov = Math.PI * 0.75;
        for (let i = 0; i <= 60; i++) {
            const a = -fov / 2 + (fov * i) / 60;
            pts.push(new THREE.Vector3(r * Math.sin(a), 0, r * Math.cos(a)));
        }
        ringGeo.setFromPoints(pts);
        const ringMat = new THREE.LineBasicMaterial({ color: 0x3d2818, transparent: true, opacity: 0.7 });
        const ring = new THREE.Line(ringGeo, ringMat);
        scene.add(ring);
    });

    // 2. Grupo de Objeto 3D Volumétrico (Silueta Holográfica de Mano/Obstáculo)
    obstacleObjectGroup = new THREE.Group();
    
    // Silueta faceted wireframe
    const obstacleGeo = new THREE.DodecahedronGeometry(12, 1);
    const obstacleMat = new THREE.MeshBasicMaterial({
        color: 0xffaa00,
        wireframe: true,
        transparent: true,
        opacity: 0.85
    });
    const obstacleMesh = new THREE.Mesh(obstacleGeo, obstacleMat);
    obstacleObjectGroup.add(obstacleMesh);

    // Núcleo brillante interior
    const coreGeo = new THREE.IcosahedronGeometry(7, 0);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xff3300 });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    obstacleObjectGroup.add(coreMesh);

    // Marcador Táctico Flotante (Rombo Bloodhound)
    const markerGeo = new THREE.OctahedronGeometry(4, 0);
    const markerMat = new THREE.MeshBasicMaterial({ color: 0xffd000, wireframe: true });
    targetDiamondMarker = new THREE.Mesh(markerGeo, markerMat);
    targetDiamondMarker.position.y = 20;
    obstacleObjectGroup.add(targetDiamondMarker);

    obstacleObjectGroup.visible = false;
    scene.add(obstacleObjectGroup);

    // Rayo Láser de Vector de Distancia
    const laserGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, 50)
    ]);
    const laserMat = new THREE.LineBasicMaterial({ color: 0xff7700, transparent: true, opacity: 0.6 });
    targetLaserBeam = new THREE.Line(laserGeo, laserMat);
    targetLaserBeam.visible = false;
    scene.add(targetLaserBeam);

    // 3. Grupo de Paredes / Estructuras de la Sala (Mallas Holográficas)
    wallPlanesGroup = new THREE.Group();
    const wallMat = new THREE.MeshBasicMaterial({
        color: 0x1e3a8a,
        wireframe: true,
        transparent: true,
        opacity: 0.4
    });

    // Pared de fondo
    const backWall = new THREE.Mesh(new THREE.PlaneGeometry(240, 80, 12, 6), wallMat);
    backWall.position.set(0, 30, 140);
    wallPlanesGroup.add(backWall);

    scene.add(wallPlanesGroup);

    // 4. Nube de Partículas de Ecos Secundarios
    pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute('position', new THREE.BufferAttribute(pointPositions, 3));
    pointGeometry.setAttribute('color', new THREE.BufferAttribute(pointColors, 3));

    const particleMat = new THREE.PointsMaterial({
        size: 7.0,
        vertexColors: true,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });
    pointCloud = new THREE.Points(pointGeometry, particleMat);
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

let lastTime = performance.now();

function animate() {
    requestAnimationFrame(animate);

    const now = performance.now();
    const dt = (now - lastTime) / 1000.0;
    lastTime = now;

    // 1. Animación de la Onda de Escaneo Expansiva (Bloodhound Sonar Pulse)
    pulseRadius += PULSE_SPEED * dt;
    if (pulseRadius > MAX_SCAN_RANGE_CM) {
        pulseRadius = 0.0;
    }
    pulseWaveMesh.scale.set(pulseRadius, pulseRadius * 0.4, pulseRadius);
    const waveOpacity = Math.max(0, 0.45 * (1.0 - pulseRadius / MAX_SCAN_RANGE_CM));
    pulseWaveMesh.material.opacity = waveOpacity;

    // 2. Rotación continua del sensor y marcador
    sensorMesh.rotation.y += 0.015;
    if (targetDiamondMarker) {
        targetDiamondMarker.rotation.y += 0.04;
        targetDiamondMarker.rotation.x += 0.02;
    }

    if (obstacleObjectGroup && obstacleObjectGroup.visible) {
        obstacleObjectGroup.children[0].rotation.y += 0.01;
        obstacleObjectGroup.children[0].rotation.z = Math.sin(now * 0.003) * 0.15;
    }

    controls.update();
    renderer.render(scene, camera);
}

// Actualizar posición del objeto 3D detectado
function updateTacticalTarget(primaryDistCm, peaks) {
    if (primaryDistCm > 15.0 && primaryDistCm <= 200.0) {
        obstacleObjectGroup.visible = true;
        targetLaserBeam.visible = true;

        // Posicionar el objeto 3D en el espacio
        const targetZ = primaryDistCm;
        const targetX = (Math.sin(performance.now() * 0.001) * 5.0); // ligera oscilación natural
        const targetY = 10.0;

        obstacleObjectGroup.position.set(targetX, targetY, targetZ);

        // Escalar la silueta según la cercanía
        const scale = Math.max(0.6, Math.min(1.5, primaryDistCm / 60.0));
        obstacleObjectGroup.scale.set(scale, scale, scale);

        // Actualizar láser de vector
        const laserPts = [
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(targetX, targetY, targetZ)
        ];
        targetLaserBeam.geometry.setFromPoints(laserPts);

        if (elTargetStatus) {
            elTargetStatus.textContent = `OBJETIVO FIJADO @ ${primaryDistCm.toFixed(1)} CM`;
            elTargetStatus.style.color = '#ffd000';
        }
    } else {
        obstacleObjectGroup.visible = false;
        targetLaserBeam.visible = false;
        if (elTargetStatus) {
            elTargetStatus.textContent = "ESCANEANDO HABITACIÓN...";
            elTargetStatus.style.color = '#ff7700';
        }
    }

    // Actualizar paredes de fondo si hay ecos lejanos (> 100 cm)
    let hasWallEcho = false;
    let wallDist = 140;
    (peaks || []).forEach(p => {
        if (p.distance_cm > 100) {
            hasWallEcho = true;
            wallDist = p.distance_cm;
        }
    });

    if (hasWallEcho && wallPlanesGroup.children.length > 0) {
        wallPlanesGroup.children[0].position.z = wallDist;
        wallPlanesGroup.children[0].visible = true;
    }
}

// Dibujar la firma RIR estilo Bloodhound Amber en Canvas
function drawTacticalRir(envelope, peaks) {
    if (!rirCtx || !envelope || envelope.length === 0) return;

    const w = rirCanvas.width;
    const h = rirCanvas.height;

    rirCtx.fillStyle = '#07070d';
    rirCtx.fillRect(0, 0, w, h);

    // Rejilla táctica
    rirCtx.strokeStyle = '#181828';
    rirCtx.lineWidth = 1;
    for (let x = 0; x <= w; x += w / 4) {
        rirCtx.beginPath();
        rirCtx.moveTo(x, 0);
        rirCtx.lineTo(x, h);
        rirCtx.stroke();
    }

    // Curva de eco ámbar
    rirCtx.strokeStyle = '#ff7700';
    rirCtx.lineWidth = 2;
    rirCtx.beginPath();

    const len = envelope.length;
    for (let i = 0; i < len; i++) {
        const x = (i / (len - 1)) * w;
        const val = envelope[i];
        const y = h - val * (h - 20) - 10;
        if (i === 0) rirCtx.moveTo(x, y);
        else rirCtx.lineTo(x, y);
    }
    rirCtx.stroke();

    // Relleno ámbar resplandeciente
    rirCtx.lineTo(w, h);
    rirCtx.lineTo(0, h);
    const grad = rirCtx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(255, 119, 0, 0.3)');
    grad.addColorStop(1, 'rgba(255, 119, 0, 0.0)');
    rirCtx.fillStyle = grad;
    rirCtx.fill();

    // Puntos de fijación táctica
    if (peaks && peaks.length > 0) {
        peaks.forEach(peak => {
            const distRatio = peak.distance_cm / 200.0;
            if (distRatio >= 0 && distRatio <= 1.0) {
                const px = distRatio * w;
                const py = h - peak.amplitude * (h - 20) - 10;

                // Diamante HUD
                rirCtx.fillStyle = '#ffd000';
                rirCtx.beginPath();
                rirCtx.moveTo(px, py - 6);
                rirCtx.lineTo(px + 6, py);
                rirCtx.lineTo(px, py + 6);
                rirCtx.lineTo(px - 6, py);
                rirCtx.closePath();
                rirCtx.fill();

                rirCtx.fillStyle = '#ffffff';
                rirCtx.font = '10px "Fira Code", monospace';
                rirCtx.fillText(`${Math.round(peak.distance_cm)}cm`, px - 12, py - 10);
            }
        });
    }
}

// Bucle de lectura de datos
async function fetchSonarData() {
    try {
        const res = await fetch('/api/sonar_frame');
        if (res.ok) {
            const data = await res.json();

            const primaryDist = data.primary_distance_cm || 0.0;
            if (elDistance) {
                elDistance.textContent = primaryDist > 0 ? primaryDist.toFixed(1) : '--.-';
            }
            if (elVelocity) {
                elVelocity.textContent = (data.velocity_mps || 0).toFixed(2);
            }
            if (elSnr) {
                elSnr.textContent = (data.snr_db || 0).toFixed(1);
            }
            if (elSeqCounter) {
                elSeqCounter.textContent = `SCAN #${data.seq || 0}`;
            }

            const peaks = data.peaks || [];
            if (elPeakCount) {
                elPeakCount.textContent = `${peaks.length} ECOS`;
            }

            // Lista de objetivos
            if (elEchoList) {
                if (peaks.length === 0) {
                    elEchoList.innerHTML = '<div class="target-row empty">Emitiendo pulsos de ecolocalización...</div>';
                } else {
                    elEchoList.innerHTML = peaks.map((p, idx) => `
                        <div class="target-row">
                            <span class="target-tag">◈ ${idx === 0 ? 'SILUETA PRINCIPAL' : 'REVERBERACIÓN'}</span>
                            <span class="target-dist">${p.distance_cm.toFixed(1)} CM</span>
                        </div>
                    `).join('');
                }
            }

            // Actualizar el modelo 3D del objeto y las paredes
            updateTacticalTarget(primaryDist, peaks);
            drawTacticalRir(data.envelope || [], peaks);
        }
    } catch (e) {
        // En caso de reconexión
    }

    setTimeout(fetchSonarData, 30);
}

window.addEventListener('DOMContentLoaded', () => {
    initThree();
    fetchSonarData();
});
