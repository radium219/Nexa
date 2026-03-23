"""
NEXA GUI v1.10.4 - pywebview tabanlı modern arayüz
Dönen daire animasyonu (standart mod) + ses dalgası (ses modu)
"""

import webview
import threading
import json
from datetime import datetime
from pathlib import Path

VERSION = "v1.10.4"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nexa</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #030b18;
    --bg2: #060f20;
    --accent: #1a6fff;
    --accent2: #0af;
    --accent3: #00eaff;
    --text: #c8e0ff;
    --text-dim: #4a7ab5;
    --green: #00ff88;
    --blue: #1a6fff;
    --gray: #2a3a55;
    --glow: 0 0 20px rgba(26,111,255,0.5);
    --glow2: 0 0 40px rgba(0,234,255,0.3);
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    user-select: none;
  }

  /* ── HEADER ── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 24px;
    border-bottom: 1px solid rgba(26,111,255,0.3);
    background: rgba(6,15,32,0.9);
    backdrop-filter: blur(10px);
    flex-shrink: 0;
  }

  .header-version {
    font-size: 11px;
    color: var(--text-dim);
    letter-spacing: 2px;
  }

  .header-title {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    font-weight: 700;
    color: var(--accent2);
    letter-spacing: 4px;
    text-shadow: var(--glow);
  }

  .header-clock {
    font-size: 11px;
    color: var(--text-dim);
    letter-spacing: 2px;
    min-width: 80px;
    text-align: right;
  }

  /* ── MAIN ── */
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    overflow: hidden;
    padding: 20px 24px 16px;
    gap: 20px;
  }

  /* ── ANIMATION AREA ── */
  .anim-area {
    position: relative;
    width: 220px;
    height: 220px;
    flex-shrink: 0;
  }

  /* Three.js canvas */
  .rings-container {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  #nexaCanvas {
    position: absolute;
    inset: 0;
    width: 100% !important;
    height: 100% !important;
  }

  /* NEXA yazısı — dairelerin ortasında, üst katmanda */
  .nexa-logo {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .nexa-logo span {
    font-family: 'Orbitron', monospace;
    font-size: 28px;
    font-weight: 900;
    letter-spacing: 8px;
    color: var(--accent3);
    text-shadow: 0 0 20px rgba(0,234,255,0.8), 0 0 40px rgba(0,234,255,0.4);
    animation: pulse-text 3s ease-in-out infinite;
  }

  @keyframes pulse-text {
    0%, 100% { opacity: 1; text-shadow: 0 0 20px rgba(0,234,255,0.8), 0 0 40px rgba(0,234,255,0.4); }
    50% { opacity: 0.8; text-shadow: 0 0 30px rgba(0,234,255,1), 0 0 60px rgba(0,234,255,0.6); }
  }

  /* ── SES DALGASI (ses modunda görünür) ── */
  .wave-container {
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .wave-bar {
    width: 6px;
    border-radius: 3px;
    background: var(--accent2);
    box-shadow: 0 0 8px rgba(0,170,255,0.6);
    animation: none;
    height: 8px;
    transition: background 0.3s;
  }

  /* NEXA harfleri üst katmanda wave üzerinde */
  .wave-logo {
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .wave-logo span {
    font-family: 'Orbitron', monospace;
    font-size: 28px;
    font-weight: 900;
    letter-spacing: 8px;
    color: var(--accent3);
    text-shadow: 0 0 20px rgba(0,234,255,0.9), 0 0 40px rgba(0,234,255,0.5);
  }

  @keyframes wave-anim {
    0%, 100% { height: 8px; }
    50% { height: var(--h, 40px); }
  }

  /* ── STT STATUS GÖSTERGESI ── */
  .stt-status {
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-top: -8px;
  }

  .stt-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--gray);
    box-shadow: 0 0 10px var(--gray);
    transition: background 0.3s, box-shadow 0.3s;
    animation: dot-pulse 1.5s ease-in-out infinite;
  }

  .stt-dot.listening { background: var(--green); box-shadow: 0 0 15px var(--green); }
  .stt-dot.processing { background: var(--blue); box-shadow: 0 0 15px var(--blue); }
  .stt-dot.waiting { background: var(--gray); box-shadow: 0 0 8px var(--gray); animation: none; }

  @keyframes dot-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.8; }
  }

  .stt-label {
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  /* ── CHAT AREA ── */
  .chat-wrapper {
    flex: 1;
    width: 100%;
    max-width: 760px;
    border: 1px solid rgba(26,111,255,0.25);
    border-radius: 16px;
    background: rgba(6,15,32,0.7);
    backdrop-filter: blur(8px);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: inset 0 0 30px rgba(26,111,255,0.05), var(--glow2);
  }

  .chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    scrollbar-width: thin;
    scrollbar-color: rgba(26,111,255,0.3) transparent;
  }

  .chat-area::-webkit-scrollbar { width: 4px; }
  .chat-area::-webkit-scrollbar-track { background: transparent; }
  .chat-area::-webkit-scrollbar-thumb { background: rgba(26,111,255,0.4); border-radius: 2px; }

  .msg {
    display: flex;
    flex-direction: column;
    gap: 2px;
    animation: msg-in 0.3s ease;
  }

  @keyframes msg-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .msg-sender {
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--text-dim);
  }

  .msg.user .msg-sender { color: rgba(0,234,255,0.5); text-align: right; }
  .msg.user { align-items: flex-end; }

  .msg-text {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text);
    background: rgba(26,111,255,0.08);
    border: 1px solid rgba(26,111,255,0.15);
    border-radius: 10px;
    padding: 8px 14px;
    max-width: 85%;
  }

  .msg.user .msg-text {
    background: rgba(0,170,255,0.1);
    border-color: rgba(0,170,255,0.2);
    color: rgba(200,230,255,0.9);
  }

  .msg.nexa .msg-text {
    border-left: 2px solid var(--accent);
  }

  /* ── INPUT AREA ── */
  .input-area {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-top: 1px solid rgba(26,111,255,0.15);
    background: rgba(3,11,24,0.8);
  }

  .text-input {
    flex: 1;
    background: rgba(26,111,255,0.06);
    border: 1px solid rgba(26,111,255,0.2);
    border-radius: 8px;
    color: var(--text);
    font-family: 'Share Tech Mono', monospace;
    font-size: 13px;
    padding: 8px 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .text-input:focus {
    border-color: rgba(26,111,255,0.6);
    box-shadow: 0 0 12px rgba(26,111,255,0.2);
  }

  .text-input::placeholder { color: var(--text-dim); }

  .btn {
    background: rgba(26,111,255,0.15);
    border: 1px solid rgba(26,111,255,0.4);
    border-radius: 8px;
    color: var(--accent2);
    font-family: 'Share Tech Mono', monospace;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 8px 16px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn:hover {
    background: rgba(26,111,255,0.3);
    box-shadow: var(--glow);
  }

  .btn:active { transform: scale(0.97); }

  .btn-mic {
    border-color: rgba(0,234,255,0.4);
    color: var(--accent3);
    padding: 8px 12px;
  }

  .btn-mic.active {
    background: rgba(0,234,255,0.15);
    box-shadow: 0 0 15px rgba(0,234,255,0.3);
    animation: btn-pulse 1s ease-in-out infinite;
  }

  @keyframes btn-pulse {
    0%, 100% { box-shadow: 0 0 15px rgba(0,234,255,0.3); }
    50% { box-shadow: 0 0 25px rgba(0,234,255,0.6); }
  }

  /* ── MODLAR ── */
  body.voice-mode .rings-container { display: none; }
  body.voice-mode .nexa-logo { display: none; }
  body.voice-mode .wave-container { display: flex; }
  body.voice-mode .wave-logo { display: flex; }
  body.voice-mode .stt-status { display: flex; }

  body:not(.voice-mode) .stt-status { display: none; }

  /* Scan line efekti */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0,0,0,0.03) 2px,
      rgba(0,0,0,0.03) 4px
    );
    pointer-events: none;
    z-index: 999;
  }
</style>
</head>
<body>

<header>
  <div class="header-version" id="version">v1.10.4</div>
  <div class="header-title">NEXA — ASSISTANT FROM THE FUTURE</div>
  <div class="header-clock" id="clock">00:00:00</div>
</header>

<main>
  <!-- ANİMASYON ALANI -->
  <div class="anim-area">

    <!-- Three.js Torus Halkaları -->
    <div class="rings-container">
      <canvas id="nexaCanvas"></canvas>
    </div>
    <div class="nexa-logo"><span>NEXA</span></div>

    <!-- Ses dalgası (ses modu) -->
    <div class="wave-container" id="waveBars"></div>
    <div class="wave-logo"><span>NEXA</span></div>

  </div>

  <!-- STT STATUS (sadece ses modunda) -->
  <div class="stt-status">
    <div class="stt-dot waiting" id="sttDot"></div>
    <div class="stt-label" id="sttLabel">BEKLIYOR</div>
  </div>

  <!-- SOHBET -->
  <div class="chat-wrapper">
    <div class="chat-area" id="chatArea"></div>
    <div class="input-area">
      <input class="text-input" id="textInput" type="text" placeholder="Komut girin..." />
      <button class="btn" id="sendBtn" onclick="sendText()">GÖNDER</button>
      <button class="btn btn-mic" id="micBtn" onclick="toggleMic()">🎤</button>
    </div>
  </div>
</main>

<script>
// ── THREE.JS TORUS HALKALARI ──
(function() {
  const script = document.createElement('script');
  script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  script.onload = function() {
    const canvas = document.getElementById('nexaCanvas');
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(220, 220);
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.z = 4.5;

    // 4 torus — farklı boyut, farklı koyu mavi tonları, ince tube
    const torusData = [
      { r: 1.6,  tube: 0.025, color: 0x1a6fff, emissive: 0x0a2fff, rx: 0,    ry: 0,    rz: 0,    vx: 0.004, vy: 0.007, vz: 0.002 },
      { r: 1.2,  tube: 0.025, color: 0x0d3fa6, emissive: 0x071f6e, rx: 1.2,  ry: 0.5,  rz: 0,    vx:-0.006, vy: 0.004, vz: 0.007 },
      { r: 0.85, tube: 0.025, color: 0x0a2d85, emissive: 0x051a52, rx: 0.5,  ry: 1.4,  rz: 0.8,  vx: 0.005, vy:-0.007, vz: 0.005 },
      { r: 0.5,  tube: 0.025, color: 0x061d5c, emissive: 0x030e33, rx: 0.3,  ry: 0.8,  rz: 1.5,  vx:-0.007, vy: 0.006, vz:-0.004 },
    ];

    const toruses = torusData.map(d => {
      const geo = new THREE.TorusGeometry(d.r, d.tube, 16, 128);
      const m = new THREE.MeshPhongMaterial({
        color: d.color,
        emissive: d.emissive,
        emissiveIntensity: 0.6,
        shininess: 180,
        transparent: true,
        opacity: 0.95,
      });
      const mesh = new THREE.Mesh(geo, m);
      mesh.rotation.set(d.rx, d.ry, d.rz);
      mesh.userData = d;
      scene.add(mesh);
      return mesh;
    });

    // Işıklar
    const ambient = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambient);
    const point1 = new THREE.PointLight(0x4488ff, 3, 10);
    point1.position.set(3, 3, 3);
    scene.add(point1);
    const point2 = new THREE.PointLight(0x0044ff, 2, 10);
    point2.position.set(-3, -2, 2);
    scene.add(point2);

    function animate() {
      requestAnimationFrame(animate);
      toruses.forEach(mesh => {
        const d = mesh.userData;
        mesh.rotation.x += d.vx;
        mesh.rotation.y += d.vy;
        mesh.rotation.z += d.vz;
      });
      renderer.render(scene, camera);
    }
    animate();
  };
  document.head.appendChild(script);
})();

// ── SAAT ──
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toTimeString().slice(0,8);
}
setInterval(updateClock, 1000);
updateClock();

// ── SES DALGASI BARLARI OLUŞTUR ──
const waveBars = document.getElementById('waveBars');
const BAR_COUNT = 28;
const bars = [];
for (let i = 0; i < BAR_COUNT; i++) {
  const bar = document.createElement('div');
  bar.className = 'wave-bar';
  const maxH = 20 + Math.random() * 60;
  bar.style.setProperty('--h', maxH + 'px');
  waveBars.appendChild(bar);
  bars.push({ el: bar, maxH, phase: Math.random() * Math.PI * 2, speed: 0.03 + Math.random() * 0.04 });
}

let waveActive = false;
let waveLevel = 0; // 0-1 arası ses seviyesi
let animFrame;

function animateWave(t) {
  bars.forEach((b, i) => {
    const targetH = waveActive
      ? Math.max(4, Math.abs(Math.sin(t * b.speed * 60 + b.phase + i * 0.3)) * b.maxH * (0.3 + waveLevel * 0.7))
      : 8;
    b.el.style.height = targetH + 'px';
  });
  animFrame = requestAnimationFrame(animateWave);
}
animFrame = requestAnimationFrame(animateWave);

// ── STT DURUM GÜNCELLEMESİ ──
function setSTTStatus(state) {
  // state: 'listening' | 'processing' | 'waiting'
  const dot = document.getElementById('sttDot');
  const label = document.getElementById('sttLabel');
  dot.className = 'stt-dot ' + state;
  const labels = { listening: 'DİNLİYOR', processing: 'İŞLİYOR', waiting: 'BEKLİYOR' };
  label.textContent = labels[state] || 'BEKLİYOR';
}

// ── SES MODU AÇ/KAPAT ──
let voiceMode = false;
function setVoiceMode(active) {
  voiceMode = active;
  document.body.classList.toggle('voice-mode', active);
  const micBtn = document.getElementById('micBtn');
  micBtn.classList.toggle('active', active);
  waveActive = active;
  if (!active) setSTTStatus('waiting');
}

// ── MİKROFON TOGGLE ──
function toggleMic() {
  if (!voiceMode) {
    setVoiceMode(true);
    setSTTStatus('listening');
    if (window.pywebview) {
      window.pywebview.api.start_listening();
    }
  } else {
    setVoiceMode(false);
    if (window.pywebview) {
      window.pywebview.api.stop_listening();
    }
  }
}

// ── MESaj EKLE ──
function addMessage(sender, text) {
  const area = document.getElementById('chatArea');
  const div = document.createElement('div');
  div.className = 'msg ' + (sender === 'You' ? 'user' : 'nexa');
  div.innerHTML = `
    <div class="msg-sender">${sender === 'You' ? 'SEN' : 'NEXA'}</div>
    <div class="msg-text">${text}</div>
  `;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

// ── TEXT GÖNDER ──
function sendText() {
  const input = document.getElementById('textInput');
  const text = input.value.trim();
  if (!text) return;
  addMessage('You', text);
  input.value = '';
  if (window.pywebview) {
    window.pywebview.api.send_text(text);
  }
}

document.getElementById('textInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendText();
});

// ── PYTHON'DAN ÇAĞRILACAK FONKSİYONLAR ──
function receiveMessage(sender, text) {
  addMessage(sender, text);
}

function updateSTT(state) {
  setSTTStatus(state);
  if (state === 'listening') {
    waveLevel = 0.3;
    waveActive = true;
  } else if (state === 'processing') {
    waveLevel = 0.15;
    waveActive = true;
  } else {
    waveLevel = 0;
    waveActive = false;
  }
}

function updateWaveLevel(level) {
  waveLevel = Math.min(1, Math.max(0, level));
}

function setVersion(v) {
  document.getElementById('version').textContent = v;
}

// Başlangıç — pywebview hazır olana kadar retry
window.addEventListener('load', () => {
  let attempts = 0;
  const tryReady = () => {
    attempts++;
    console.log(`[Nexa] pywebview check attempt ${attempts}, api: ${!!(window.pywebview && window.pywebview.api)}`);
    if (window.pywebview && window.pywebview.api) {
      console.log('[Nexa] Bridge ready, calling on_ready...');
      window.pywebview.api.gui_ready();
    } else if (attempts < 60) {
      setTimeout(tryReady, 500);
    } else {
      console.error('[Nexa] pywebview bridge never became ready!');
      document.getElementById('chatArea').innerHTML = '<div style="color:red;padding:20px">Bridge error: pywebview API not available after 30s</div>';
    }
  };
  setTimeout(tryReady, 1000);
});
</script>
</body>
</html>
"""

class NexaAPI:
    """Python tarafı — pywebview JS bridge"""

    def __init__(self):
        self.window = None
        self._listening = False
        self._core_thread = None
        self._core = None
        self._core_ready = threading.Event()

    def set_window(self, window):
        self.window = window

    def gui_ready(self):
        """GUI hazır olduğunda çağrılır"""
        print("✅ on_ready çağrıldı!")
        print("✅ gui_ready çağrıldı!")
        self.window.evaluate_js(f"setVersion('{VERSION}')") 
        self._start_core()

    def _start_core(self):
        """nexa_core'u ayrı thread'de başlatır"""
        def run():
            print("🚀 Core yükleniyor...")
            try:
                import importlib.util, sys
                core_path = Path(__file__).parent / "core" / "nexa_core.py"
                if not core_path.exists():
                    core_path = Path(__file__).parent / "nexa_core.py"

                print(f"📂 Core path: {core_path} | Var mı: {core_path.exists()}")
                spec = importlib.util.spec_from_file_location("nexa_core", core_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                # Greet
                from datetime import datetime
                import random
                hour = datetime.now().hour
                if 5 <= hour < 12: bas = "Good morning, sir."
                elif 12 <= hour < 18: bas = "Good afternoon, sir."
                elif 18 <= hour < 22: bas = "Good evening, sir."
                else: bas = "Good night, sir."
                sonlar = ["How can I help?", "How may I assist?", "Ready for your orders."]
                greeting = f"{bas} {random.choice(sonlar)}"

                self._add_message("Nexa", greeting)
                threading.Thread(target=mod.speak, args=(greeting,), daemon=True).start()

                # core modülünü sakla
                self._core = mod
                self._core_ready.set()

            except Exception as e:
                import traceback
                self._core_ready.set()
                self._add_message("Nexa", f"Core yüklenemedi: {e}\n{traceback.format_exc()}")

        self._core_thread = threading.Thread(target=run, daemon=True)
        self._core_thread.start()

    def send_text(self, text: str):
        """Kullanıcı text gönderdi"""
        def process():
            try:
                self._core_ready.wait(timeout=120)
                if not self._core:
                    self._add_message("Nexa", "Core henüz hazır değil, lütfen bekleyin.")
                    return
                reply, _ = self._core.ask_nexa(text, [])
                self._add_message("Nexa", reply)
                threading.Thread(target=self._core.speak, args=(reply,), daemon=True).start()
            except Exception as e:
                self._add_message("Nexa", f"Hata: {e}")
        threading.Thread(target=process, daemon=True).start()

    def start_listening(self):
        """Mikrofon dinlemeye başla"""
        def listen():
            try:
                self._core_ready.wait(timeout=120)
                if not self._core:
                    self._add_message("Nexa", "Core henüz hazır değil.")
                    return
                self._listening = True
                self._update_stt("listening")

                text = self._core.listen_until_silence(
                    status_callback=lambda s: self._update_stt(
                        "listening" if "Dinliyorum" in s or "Kaydediyorum" in s else "processing"
                    )
                )

                if text:
                    self._add_message("You", text)
                    self._update_stt("processing")
                    reply, _ = self._core.ask_nexa(text, [])
                    self._add_message("Nexa", reply)
                    threading.Thread(target=self._core.speak, args=(reply,), daemon=True).start()

            except Exception as e:
                self._add_message("Nexa", f"Dinleme hatası: {e}")
            finally:
                self._listening = False
                self._update_stt("waiting")
                self.window.evaluate_js("setVoiceMode(false)")

        threading.Thread(target=listen, daemon=True).start()

    def stop_listening(self):
        self._listening = False

    def _add_message(self, sender: str, text: str):
        safe = text.replace("'", "\\'").replace("\n", "<br>")
        self.window.evaluate_js(f"receiveMessage('{sender}', '{safe}')")

    def _update_stt(self, state: str):
        self.window.evaluate_js(f"updateSTT('{state}')")


def main():
    import os
    os.environ["PYWEBVIEW_GUI"] = "edgechromium"
    api = NexaAPI()
    window = webview.create_window(
        title="Nexa",
        html=HTML,
        js_api=api,
        width=900,
        height=700,
        min_size=(700, 550),
        background_color="#030b18",
        frameless=False,
    )
    api.set_window(window)
    webview.start(debug=False, private_mode=False)


if __name__ == "__main__":
    main()