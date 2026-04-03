// 1. Scene & Setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 5000);
camera.position.set(0, 150, 400);

const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// 2. Starfield
const starVertices = [];
for (let i = 0; i < 9000; i++) {
    starVertices.push((Math.random() - 0.5) * 4000, (Math.random() - 0.5) * 4000, (Math.random() - 0.5) * 4000);
}
const starGeo = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(starVertices, 3));
scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.8, transparent: true, opacity: 0.9 })));

// 3. Lighting & Sun
const sunLight = new THREE.PointLight(0xffffff, 8, 2000); 
scene.add(sunLight);
scene.add(new THREE.AmbientLight(0x222222)); 

function createSunTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512; canvas.height = 512;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ff4500'; ctx.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 25000; i++) {
        ctx.fillStyle = `rgba(255, 255, 100, ${Math.random() * 0.6})`;
        ctx.fillRect(Math.random() * 512, Math.random() * 512, 2, 2);
    }
    return new THREE.CanvasTexture(canvas);
}

const sun = new THREE.Mesh(
    new THREE.SphereGeometry(10, 64, 64),
    new THREE.MeshStandardMaterial({ map: createSunTexture(), emissive: 0xffaa00, emissiveIntensity: 2.0 })
);
scene.add(sun);

// 4. Global Groups & State
const planetObjects = [];
const labelGroup = new THREE.Group();
scene.add(labelGroup);
let time = 0, playing = false;

// 5. Dynamic Asteroid Belt
const asteroidCount = 4000;
const asteroidData = []; 
const asteroidVertices = new Float32Array(asteroidCount * 3);

for (let i = 0; i < asteroidCount; i++) {
    const rho = 53 + Math.random() * 12; 
    const theta = Math.random() * Math.PI * 2;
    const period = (rho * rho * 0.04) * (0.9 + Math.random() * 0.2); 
    const phi = (Math.random() - 0.5) * 0.1; 
    
    asteroidData.push({ rho, theta, period, phi });
    asteroidVertices[i * 3] = rho * Math.cos(theta);
    asteroidVertices[i * 3 + 1] = rho * Math.sin(phi);
    asteroidVertices[i * 3 + 2] = rho * Math.sin(theta);
}

const asteroidGeo = new THREE.BufferGeometry();
asteroidGeo.setAttribute('position', new THREE.BufferAttribute(asteroidVertices, 3));
const asteroidBelt = new THREE.Points(asteroidGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.5, transparent: true, opacity: 0.7 }));
scene.add(asteroidBelt);

// 6. Helpers
function createMoon(parentGroup, planetRadius, orbitDist, sizeRatio, period, color) {
    const moonMesh = new THREE.Mesh(
        new THREE.SphereGeometry(planetRadius * sizeRatio, 16, 16), 
        new THREE.MeshStandardMaterial({ color: color, roughness: 0.9 })
    );
    const moonOrbitContainer = new THREE.Group();
    parentGroup.add(moonOrbitContainer); 
    moonOrbitContainer.add(moonMesh);
    moonMesh.position.set(planetRadius + orbitDist, 0, 0);
    return { moonOrbitContainer, period, moonMesh };
}

function createLabel(text) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 256; canvas.height = 128;
    ctx.font = 'Bold 42px Arial'; ctx.fillStyle = '#00d4ff'; ctx.textAlign = 'center';
    ctx.fillText(text, 128, 64);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false }));
    sprite.scale.set(14, 7, 1);
    return sprite;
}

// 7. Planet Initialization (Requires PLANETS array from planets.js)
if (typeof PLANETS !== 'undefined') {
    PLANETS.forEach(p => {
        const group = new THREE.Group();
        scene.add(group);

        const mesh = new THREE.Mesh(
            new THREE.SphereGeometry(p.radius, 32, 32), 
            new THREE.MeshStandardMaterial({ color: p.color, roughness: 0.7, metalness: 0.2, emissive: p.color, emissiveIntensity: 0.2 })
        );
        group.add(mesh);

        let moons = [];
        if (p.name === "Earth") moons.push(createMoon(group, p.radius, 5, 0.27, 27.3, 0xaaaaaa));
        if (p.name === "Jupiter") {
            moons.push(createMoon(group, p.radius, 4, 0.08, 0.5, 0xaaaaaa)); 
            moons.push(createMoon(group, p.radius, 8, 0.15, 1.7, 0xffd700)); 
            moons.push(createMoon(group, p.radius, 12, 0.13, 3.5, 0xffffff));
            moons.push(createMoon(group, p.radius, 17, 0.22, 7.1, 0x964B00));
        }
        if (p.name === "Saturn") {
            moons.push(createMoon(group, p.radius, 18, 0.35, 15.9, 0xffa500)); 
            const ring = new THREE.Mesh(new THREE.TorusGeometry(p.radius * 2.3, 0.2, 2, 64), new THREE.MeshStandardMaterial({ color: 0xceb8b0, transparent: true, opacity: 0.7, side: THREE.DoubleSide }));
            ring.rotation.x = Math.PI / 2.2;
            group.add(ring); 
        }

        const pts = [];
        for (let i = 0; i <= 360; i++) {
            const a = (i / 360) * Math.PI * 2;
            pts.push(new THREE.Vector3(Math.cos(a) * p.distance, 0, Math.sin(a) * p.distance));
        }
        const orbitLine = new THREE.LineLoop(
            new THREE.BufferGeometry().setFromPoints(pts), 
            new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 })
        );
        scene.add(orbitLine);

        const label = createLabel(p.name);
        labelGroup.add(label);
        planetObjects.push({ group, mesh, data: p, label, moons });
    });
}

// 8. Animation & Update Logic
const playBtn = document.getElementById("playBtn");
const speedMenu = document.getElementById("speedMenu");
const timeDisplay = document.getElementById("timeValue");

function updatePositions() {
    const showSats = document.getElementById("satelliteToggle") ? document.getElementById("satelliteToggle").checked : true;
    planetObjects.forEach(p => {
        const a = (p.data.phase * Math.PI / 180) + (time / p.data.period) * Math.PI * 2;
        p.group.position.set(Math.cos(a) * p.data.distance, 0, Math.sin(a) * p.data.distance);
        p.label.position.set(p.group.position.x, p.data.radius + 8, p.group.position.z);
        if (p.moons) {
            p.moons.forEach(m => {
                m.moonOrbitContainer.rotation.y = (time / m.period) * Math.PI * 2;
                m.moonMesh.visible = showSats;
            });
        }
    });

    const positions = asteroidBelt.geometry.attributes.position.array;
    for (let i = 0; i < asteroidCount; i++) {
        const data = asteroidData[i];
        const currentTheta = data.theta + (time / data.period) * Math.PI * 2;
        positions[i * 3] = data.rho * Math.cos(currentTheta);
        positions[i * 3 + 2] = data.rho * Math.sin(currentTheta);
    }
    asteroidBelt.geometry.attributes.position.needsUpdate = true;
}

if(playBtn) playBtn.onclick = () => { playing = !playing; playBtn.innerText = playing ? "⏸ Pause" : "▶ Play"; };
if(document.getElementById("resetBtn")) document.getElementById("resetBtn").onclick = () => { time = 0; playing = false; updatePositions(); if(timeDisplay) timeDisplay.innerText = "Day 0"; if(playBtn) playBtn.innerText = "▶ Play"; };
if(document.getElementById("labelToggle")) document.getElementById("labelToggle").onchange = (e) => { labelGroup.visible = e.target.checked; };

function animate() {
    requestAnimationFrame(animate);
    if (playing) { 
        time += Number(speedMenu.value) / 60; 
        if(timeDisplay) timeDisplay.innerText = `Day ${Math.floor(time)}`; 
        updatePositions(); 
        planetObjects.forEach(p => { p.mesh.rotation.y += 0.01; });
        sun.rotation.y += 0.002;
    }
    controls.update(); 
    renderer.render(scene, camera);
}

updatePositions();
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
