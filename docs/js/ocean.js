// SeaSwarm 3D scroll story. Three.js from primitives only; no external models.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const mobile = matchMedia('(max-width: 760px)').matches;
const canvas = document.getElementById('scene');
let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: !mobile, powerPreference: 'high-performance' }); }
catch (e) { document.body.classList.add('fallback'); throw e; }
renderer.setPixelRatio(Math.min(devicePixelRatio, mobile ? 1.25 : 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.55;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x2a3550, 0.0042);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.5, 4000);

// Dusk sky + sun
const sky = new Sky(); sky.scale.setScalar(10000); scene.add(sky);
const su = sky.material.uniforms;
su.turbidity.value = 8; su.rayleigh.value = 2.2; su.mieCoefficient.value = 0.006; su.mieDirectionalG.value = 0.85;
const sun = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(86), THREE.MathUtils.degToRad(200));
su.sunPosition.value.copy(sun);
const sunLight = new THREE.DirectionalLight(0xffc89a, 2.2); sunLight.position.copy(sun).multiplyScalar(100); scene.add(sunLight);
scene.add(new THREE.HemisphereLight(0x9fc8ff, 0x0b1d3a, 0.6));

// Gerstner waves (shared by GPU and CPU so boats ride the same surface)
const WAVES = [
  [1.0, 0.25, 0.18, 60], [0.6, 0.8, 0.14, 31], [-0.4, 1.0, 0.10, 18], [0.9, -0.5, 0.08, 11],
];
function gerstner(x, z, t) {
  let px = x, py = 0, pz = z;
  for (const [dx, dz, s, L] of WAVES) {
    const l = Math.hypot(dx, dz), ux = dx / l, uz = dz / l, k = 2 * Math.PI / L, c = Math.sqrt(9.8 / k), a = s / k;
    const f = k * (ux * x + uz * z - c * t);
    px += ux * a * Math.cos(f); pz += uz * a * Math.cos(f); py += a * Math.sin(f);
  }
  return [px, py, pz];
}
const waveGLSL = WAVES.map(w => `vec4(${w.map(v => v.toFixed(3)).join(',')})`).join(',');

const uniforms = {
  uTime: { value: 0 }, uSun: { value: sun }, uFog: { value: scene.fog.color }, uFogD: { value: scene.fog.density },
  uSector: { value: 0 }, uCleared: { value: new THREE.Vector3() }, uDup: { value: 0 }, uHead: { value: THREE.MathUtils.degToRad(250 - 90) },
};
const oceanMat = new THREE.ShaderMaterial({
  uniforms,
  vertexShader: `
  uniform float uTime; varying vec3 vW; varying vec3 vN; varying vec2 vXZ;
  const vec4 W[4] = vec4[4](${waveGLSL});
  void main(){
    vec3 p = position.xzy; p.z = -p.z; vec3 g = p; vec3 T = vec3(1,0,0), B = vec3(0,0,1);
    for(int i=0;i<4;i++){
      vec2 d = normalize(W[i].xy); float k = 6.28318/W[i].w; float c = sqrt(9.8/k); float a = W[i].z/k;
      float f = k*(dot(d,p.xz)-c*uTime);
      g += vec3(d.x*a*cos(f), a*sin(f), d.y*a*cos(f));
      T += vec3(-d.x*d.x*W[i].z*sin(f), d.x*W[i].z*cos(f), -d.x*d.y*W[i].z*sin(f));
      B += vec3(-d.x*d.y*W[i].z*sin(f), d.y*W[i].z*cos(f), -d.y*d.y*W[i].z*sin(f));
    }
    vN = normalize(cross(B,T)); vXZ = p.xz;
    vec4 w = modelMatrix*vec4(g,1.0); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w;
  }`,
  fragmentShader: `
  uniform vec3 uSun; uniform vec3 uFog; uniform float uFogD; uniform float uTime;
  uniform float uSector; uniform vec3 uCleared; uniform float uDup; uniform float uHead;
  varying vec3 vW; varying vec3 vN; varying vec2 vXZ;
  float sectorMask(vec2 q, float rot, out float idx, out float edge){
    float r = length(q); float a = atan(q.y,q.x) - uHead - rot; a = atan(sin(a),cos(a));
    float half_ = 0.42; idx = -1.0; edge = 0.0;
    if(r<14.0||r>130.0||abs(a)>half_) return 0.0;
    float s = (a+half_)/(2.0*half_)*3.0; idx = floor(s);
    float fr = fract(s); float ed = min(fr,1.0-fr)*r*0.7;
    edge = smoothstep(1.2,0.0,ed) + smoothstep(1.5,0.0,abs(r-14.0)) + smoothstep(1.5,0.0,abs(r-130.0));
    return 1.0;
  }
  void main(){
    vec3 V = normalize(cameraPosition - vW); vec3 N = normalize(vN);
    float fres = pow(1.0 - max(dot(N,V),0.0), 4.0);
    vec3 deep = vec3(0.01,0.06,0.13), shallow = vec3(0.04,0.22,0.32), skyc = vec3(0.55,0.45,0.55);
    vec3 col = mix(deep, shallow, clamp(vW.y*0.4+0.4,0.0,1.0));
    col = mix(col, skyc, fres*0.8);
    vec3 H = normalize(uSun + V); col += vec3(1.0,0.72,0.45)*pow(max(dot(N,H),0.0), 260.0)*3.0;
    col += vec3(0.9,0.95,1.0)*smoothstep(0.9,1.6,vW.y)*0.25; // crest foam
    if(uSector>0.001){
      float idx, edge; float m = sectorMask(vXZ, 0.0, idx, edge);
      if(m>0.0){
        float cl = idx<0.5?uCleared.x:(idx<1.5?uCleared.y:uCleared.z);
        vec3 base = mix(vec3(1.0,0.75,0.2), vec3(0.3,1.0,0.5), cl);
        float grid = smoothstep(0.08,0.0,abs(fract(length(vXZ)/10.0)-0.5)-0.45);
        float pulse = 0.6+0.4*sin(uTime*2.0 - length(vXZ)*0.08);
        col += base*uSector*(0.10 + edge*0.9*pulse + grid*0.25 + cl*0.15);
      }
      if(uDup>0.001){
        float j = step(0.5, fract(uTime*7.0)) * 0.06;
        float i2, e2; float m2 = sectorMask(vXZ + vec2(9.0,-6.0), 0.12+j, i2, e2);
        if(m2>0.0) col += vec3(1.0,0.1,0.25)*uDup*(0.08+e2*0.9);
      }
    }
    float d = length(cameraPosition - vW); float fg = 1.0 - exp(-pow(uFogD*d,2.0));
    gl_FragColor = vec4(mix(col, uFog, fg), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`,
});
const seg = mobile ? 160 : 300;
const ocean = new THREE.Mesh(new THREE.PlaneGeometry(1400, 1400, seg, seg), oceanMat);
ocean.frustumCulled = false; scene.add(ocean);

// Boats from primitives
function makeBoat(hullColor, scale = 1) {
  const g = new THREE.Group();
  const m = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, metalness: 0.1 });
  const hull = new THREE.Mesh(new THREE.BoxGeometry(2.2, 1.0, 7), m(hullColor)); hull.position.y = 0.3; g.add(hull);
  const bow = new THREE.Mesh(new THREE.ConeGeometry(1.1, 2.6, 4), m(hullColor)); bow.rotation.set(Math.PI / 2, Math.PI / 4, 0); bow.scale.set(1, 1, 0.45); bow.position.set(0, 0.3, 4.6); g.add(bow);
  const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.3, 2), m(0xf2efe6)); cabin.position.set(0, 1.4, -1.2); g.add(cabin);
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 4.5), m(0xdddddd)); mast.position.set(0, 3, 0.8); g.add(mast);
  const flag = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.5), new THREE.MeshStandardMaterial({ color: 0xff7043, side: THREE.DoubleSide })); flag.position.set(0.45, 5, 0.8); g.add(flag);
  g.scale.setScalar(scale); return g;
}
const sagar = makeBoat(0x1565c0, 1.2); scene.add(sagar);
const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 16), new THREE.MeshBasicMaterial({ color: 0xff3b3b }));
beacon.position.set(0, 5.8, 0.8); sagar.add(beacon);
const beaconLight = new THREE.PointLight(0xff3b3b, 30, 40); beacon.add(beaconLight);
const rings = [0, 1, 2].map(i => {
  const r = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.1, 48), new THREE.MeshBasicMaterial({ color: 0xff5252, transparent: true, side: THREE.DoubleSide, depthWrite: false }));
  r.rotation.x = -Math.PI / 2; r.userData.o = i / 3; scene.add(r); return r;
});

// Search boats: Meerabai, Chandra-2, Harnai-Queen (from room template) head to the three sectors
const head = uniforms.uHead.value;
const sectorCenter = i => { const a = head + (-0.42 + 0.28 * (i + 0.5)); return new THREE.Vector2(Math.cos(a) * 75, Math.sin(a) * 75); };
const searchers = [0xffb300, 0x26a69a, 0xab47bc].map((c, i) => {
  const b = makeBoat(c, 0.9); b.userData = { from: new THREE.Vector2(-40 + i * 25, 40), to: sectorCenter(i), p: 0 }; scene.add(b); return b;
});

// Camera keyframes per story step
const K = [
  { p: [0, 9, 34], t: [0, 3, 0], sec: 0 },          // hero
  { p: [22, 6, 18], t: [0, 2, 0], sec: 0 },         // problem: close on Sagar-4
  { p: [-60, 90, 70], t: [-10, 0, -40], sec: 1 },   // agents: drift cone from above
  { p: [14, 7, 22], t: [0, 4, 0], sec: 1 },         // gate
  { p: [-30, 120, 30], t: [-20, 0, -50], sec: 1, dup: 1 }, // kill switch
  { p: [-90, 60, -10], t: [-20, 0, -60], sec: 1, clear: 1 }, // audit: sectors cleared
  { p: [0, 30, 90], t: [0, 0, -30], sec: 1, clear: 1 },     // CTA
];
const state = { px: 0, py: 9, pz: 34, tx: 0, ty: 3, tz: 0, sec: 0, dup: 0, clear: 0, go: 0 };
const look = new THREE.Vector3();
function applyStep(i) {
  const k = K[i], to = { px: k.p[0], py: k.p[1], pz: k.p[2], tx: k.t[0], ty: k.t[1], tz: k.t[2], sec: k.sec, dup: k.dup || 0, clear: k.clear || 0, go: i >= 2 ? 1 : 0 };
  if (window.gsap && !reduce) gsap.to(state, { ...to, duration: 1.8, ease: 'power3.inOut', overwrite: true });
  else Object.assign(state, to);
  if (i === 3) document.getElementById('stamp')?.classList.add('on');
  if (i === 5) document.querySelectorAll('#log li').forEach((li, n) => setTimeout(() => li.classList.add('in'), reduce ? 0 : n * 180));
}
function wireScroll() {
  const panels = [...document.querySelectorAll('[data-step]')];
  if (window.ScrollTrigger) {
    gsap.registerPlugin(ScrollTrigger);
    panels.forEach(el => ScrollTrigger.create({ trigger: el, start: 'top 55%', end: 'bottom 45%', onToggle: s => s.isActive && applyStep(+el.dataset.step) }));
    panels.forEach(el => gsap.from(el.querySelector('.glass'), { opacity: 0, y: 60, duration: 1, scrollTrigger: { trigger: el, start: 'top 80%' } }));
  } else {
    const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && applyStep(+e.target.dataset.step)), { threshold: 0.5 });
    panels.forEach(p => io.observe(p));
  }
}
addEventListener('load', wireScroll);

const clock = new THREE.Clock();
const cleared = uniforms.uCleared.value;
function place(obj, x, z, t, yaw) {
  const [, y] = gerstner(x, z, t); const [, yx] = gerstner(x + 2, z, t); const [, yz] = gerstner(x, z + 2, t);
  obj.position.set(x, y, z); obj.rotation.set((yz - y) * -0.4, yaw, (yx - y) * 0.4);
}
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05), t = reduce ? 0 : clock.elapsedTime;
  uniforms.uTime.value = t;
  uniforms.uSector.value += (state.sec - uniforms.uSector.value) * 0.05;
  uniforms.uDup.value += (state.dup - uniforms.uDup.value) * 0.08;
  place(sagar, 0, 0, t, 0.6);
  rings.forEach(r => { const p = (t * 0.5 + r.userData.o) % 1; r.position.set(0, 0.6, 0); r.scale.setScalar(1 + p * 18); r.material.opacity = (1 - p) * 0.8; });
  beaconLight.intensity = 20 + Math.sin(t * 6) * 15;
  searchers.forEach((b, i) => {
    const u = b.userData; u.p = THREE.MathUtils.clamp(u.p + (state.go ? dt * 0.08 : -dt * 0.2), 0, 1);
    const e = u.p * u.p * (3 - 2 * u.p); const x = THREE.MathUtils.lerp(u.from.x, u.to.x, e), z = THREE.MathUtils.lerp(u.from.y, u.to.y, e);
    place(b, x, z, t, Math.atan2(u.to.x - u.from.x, u.to.y - u.from.y));
    const target = state.clear ? (u.p > 0.95 ? 1 : 0) : 0;
    cleared.setComponent(i, cleared.getComponent(i) + (target - cleared.getComponent(i)) * dt * (0.6 + i * 0.3));
  });
  camera.position.set(state.px, state.py, state.pz); look.set(state.tx, state.ty, state.tz); camera.lookAt(look);
  renderer.render(scene, camera);
  if (!reduce) requestAnimationFrame(frame);
}
if (reduce) { applyStep(0); addEventListener('scroll', () => requestAnimationFrame(frame), { passive: true }); }
frame();
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
