// main.js — PredictMaint Pro v2

// ── CHART DEFAULTS ────────────────────────────────────────────────────────────
function applyChartTheme() {
  const isLight = document.body.classList.contains('light');
  Chart.defaults.color       = isLight ? '#4a6070' : '#6688aa';
  Chart.defaults.borderColor = isLight ? 'rgba(0,100,150,0.12)' : 'rgba(0,212,255,0.09)';
  Chart.defaults.font.family = "'Exo 2', sans-serif";
}
applyChartTheme();

function pmDS(label, color, data) {
  return {
    label, data,
    borderColor: color,
    backgroundColor: color.replace('rgb(','rgba(').replace(')',',0.07)'),
    fill: true, tension: 0.4,
    pointRadius: 3, borderWidth: 2,
    pointBackgroundColor: color,
  };
}

function getAX() {
  const isLight = document.body.classList.contains('light');
  return { grid: { color: isLight ? 'rgba(0,100,150,0.1)' : 'rgba(0,212,255,0.07)' } };
}
const AX = getAX();

// ── ALARM (Web Audio API) ─────────────────────────────────────────────────────
let _alarmActive = false;
function playAlarm() {
  if (_alarmActive) return;
  _alarmActive = true;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [[880,.0],[660,.25],[880,.5],[660,.75],[880,1.0],[660,1.25]].forEach(([f,t]) => {
      const osc = ctx.createOscillator(), g = ctx.createGain();
      osc.connect(g); g.connect(ctx.destination);
      osc.type = 'square'; osc.frequency.value = f;
      g.gain.setValueAtTime(.18, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + t + .2);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + .22);
    });
  } catch(e) {}
  setTimeout(() => _alarmActive = false, 3500);
}

// ── GAUGE ─────────────────────────────────────────────────────────────────────
function drawGauge(id, value, label) {
  const c = document.getElementById(id);
  if (!c) return;
  const ctx = c.getContext('2d'), w = c.width, h = c.height;
  ctx.clearRect(0,0,w,h);
  const cx = w/2, cy = h-8, r = Math.min(w, h*2) * 0.42;
  ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,0);
  ctx.lineWidth=14; ctx.strokeStyle='rgba(255,255,255,0.06)';
  ctx.lineCap='round'; ctx.stroke();
  const pct   = Math.min(100,Math.max(0,value)) / 100;
  const color = value>60 ? '#00ff88' : value>30 ? '#ffaa00' : '#ff3355';
  ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,Math.PI + pct*Math.PI);
  ctx.lineWidth=14; ctx.strokeStyle=color; ctx.lineCap='round'; ctx.stroke();
  ctx.fillStyle='#fff';
  ctx.font=`bold ${Math.floor(r*.44)}px 'Rajdhani',sans-serif`;
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(Math.round(value), cx, cy-8);
  ctx.fillStyle='#6688aa';
  ctx.font=`${Math.floor(r*.21)}px 'Exo 2',sans-serif`;
  ctx.fillText(label, cx, cy+14);
}

// ── LIVE SIMULATION ───────────────────────────────────────────────────────────
let _simTimer = null;

function startSimulation(machineId, cb) {
  if (_simTimer) return;
  _simTimer = setInterval(async () => {
    try {
      const r = await fetch(`/api/live-data?machine_id=${machineId}`);
      cb(await r.json());
    } catch(e) {}
  }, 2000);
}

function stopSimulation() {
  if (_simTimer) { clearInterval(_simTimer); _simTimer = null; }
}

// ── POINT COLORS ─────────────────────────────────────────────────────────────
function ptColors(data, thresh, normal, alert) {
  return data.map(v => v >= thresh ? alert : normal);
}
